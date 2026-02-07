import asyncio
import aio_pika
import json
import os
import statistics
from decimal import Decimal
from sqlalchemy import update
from shared.db import AsyncSessionLocal
from shared.models import Job, JobEvent
from models.models import AnalysisResponse, Document, Customer
from services.analysis.config import DEBUG, SOFT_FLAG_EPSILON, RABBITMQ_URL, INPUT_QUEUE, OUTPUT_QUEUE

WORKER_NAME = os.getenv('HOSTNAME', 'analysis_worker_local')

async def update_job_status(job_id: str, status: str, message: str = None):

    async with AsyncSessionLocal() as session:
        async with session.begin():

            await session.execute(
                update(Job).where(Job.job_id == job_id).values(current_status=status)
            )

            event = JobEvent(
                job_id=job_id, 
                status=status, 
                message=message,
                worker_name=WORKER_NAME
            )
            session.add(event)

async def perform_analysis(data: dict) -> dict:
    customer = Customer(**data['customer'])
    doc = Document(**data['document'])
    transactions = doc.transactions

    hard_flags = []
    
    total_inflow = sum(t.amount for t in transactions if t.amount > 0)
    total_outflow = sum(t.amount for t in transactions if t.amount < 0)
    net_change = total_inflow + total_outflow
    avg_daily_balance = sum(t.balance for t in transactions) / Decimal(len(transactions)) if transactions else Decimal(0)

    # hard flags
    
    # name mismatch
    if customer.name != doc.customer_name:
        hard_flags.append({
            "type": "name_mismatch",
            "customer_profile_name": customer.name,
            "document_name": doc.customer_name,
        })

    # address mismatch
    if customer.address != doc.customer_address:
        hard_flags.append({
            "type": "address_mismatch",
            "customer_profile_address": customer.address,
            "document_address": doc.customer_address,
        })

    # balance mismatch
    transactions_sorted = sorted(transactions, key=lambda t: t.date)
    for i, t in enumerate(transactions):
        if i == 0: continue
        prev = transactions_sorted[i-1]

        expected_balance = prev.balance + t.amount
        if expected_balance != t.balance:
            hard_flags.append({
                "type": "balance_mismatch",
                "date": t.date.isoformat(),
                "vendor": t.vendor,
                "transaction_id": t.transaction_id,
                "expected_balance": expected_balance,
                "actual_balance": t.balance,
            })

    # soft flags
    amounts = [t.amount for t in transactions]
    if len(amounts) > 1:
        mean_amt = statistics.mean(amounts)
        std_amt = statistics.stdev(amounts)
    else:
        mean_amt = amounts[0] if amounts else 0
        std_amt = 0

    soft_flags = [
        {
            "type": "std_dev_outlier",
            "transaction_id": t.transaction_id,
            "amount": t.amount,
            "date": t.date,
            "vendor": t.vendor,
            "std_dev_deviation": deviation,
            "std_dev_threshold": SOFT_FLAG_EPSILON
        }
        for i, t in enumerate(transactions, start=1)
        if std_amt > 0
        and (deviation := round(abs(t.amount - mean_amt) / std_amt, 2)) > Decimal(SOFT_FLAG_EPSILON)
    ]

    response_data = AnalysisResponse(
        customer=customer,
        filename=doc.filename,
        summary={
            "total_inflow": total_inflow,
            "total_outflow": total_outflow,
            "net_change": net_change,
            "avg_daily_balance": avg_daily_balance,
        },
        alerts={
            "soft_flags": soft_flags, 
            "hard_flags": hard_flags,
        }
    )

    return response_data.dict()

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        job_id = message.correlation_id
        body = json.loads(message.body.decode())
        
        print(f"[*] [{WORKER_NAME}] Analyzing: {body['customer']['name']}")
        await update_job_status(job_id, "ANALYSIS_STARTED")
        
        try:
            results = await perform_analysis(body)
            
            print(f"[+] [{WORKER_NAME}] [{job_id}] Analysis finished.")
            await update_job_status(job_id, "ANALYSIS_SUCCESS", json.dumps(results, default=str))

            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue(OUTPUT_QUEUE, durable=True)
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(results, default=str).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        correlation_id=job_id
                    ),
                    routing_key=OUTPUT_QUEUE
                )

        except Exception as e:
            print(f"[!] [{WORKER_NAME}] [{job_id}] Analysis error: {e}")
            await update_job_status(job_id, "ANALYSIS_FAILED", str(e))

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(INPUT_QUEUE, durable=True)
        
        print(f" [*] [{WORKER_NAME}] Analysis Worker active. Listening on {INPUT_QUEUE}...")
        await queue.consume(process_message)
        
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())