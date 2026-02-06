import asyncio
import aio_pika
import json
import statistics
from decimal import Decimal
from sqlalchemy import update
from shared.db import AsyncSessionLocal
from shared.models import Job, JobEvent
from models.models import AnalysisResponse, Document, Customer
from services.analysis.config import DEBUG, SOFT_FLAG_EPSILON, RABBITMQ_URL, INPUT_QUEUE, OUTPUT_QUEUE

async def update_job_status(job_id: str, status: str, message: str = None):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(Job).where(Job.job_id == job_id).values(current_status=status)
            )
            event = JobEvent(job_id=job_id, status=status, message=message)
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

    # Hard flags
    print("\n")

    ### name mismatch
    if(customer.name != doc.customer_name):
        if DEBUG:
            print(
                f"Hard flag raised: name_mismatch between Customer profile and provided document\n"
                f"Document name \"{doc.customer_name}\" should be customer profile name \"{customer.name}\"\n"
            )
        hard_flags.append({
            "type": "name_mismatch",
            "customer_profile_name": customer.name,
            "document_name": doc.customer_name,
        })

    ### address mismatch
    if(customer.address != doc.customer_address):
        if DEBUG:
            print(
                f"Hard flag raised: address_mismatch between Customer profile and provided document\n"
                f"Document address \"{doc.customer_address}\" should be customer profile address \"{customer.address}\"\n"
            )
        hard_flags.append({
            "type": "address_mismatch",
            "customer_profile_address": customer.address,
            "document_address": doc.customer_address,
        })


    ### date and balance mismatches
    transactions_sorted = sorted(transactions, key=lambda t: t.date)

    for i, t in enumerate(transactions):
        if i == 0:
            continue

        prev = transactions_sorted[i-1]

        if(t.date.isoformat != transactions_sorted[i].date.isoformat):
            if DEBUG:
                print(f"Hard flag raised: date_mismatch at Transaction {i}. Date misaligned with sorted transaction list.\nAre these transactions in sorted order?")
            hard_flags.append({
                "type": "date_mismatch",
                "transaction_id": t.transaction_id,
                "actual_date": t.date.isoformat(),
                "expected_date": transactions_sorted[i].date.isoformat(),
                "vendor": t.vendor,
                "balance": t.balance,
            })

        expected_balance = prev.balance + t.amount
        if expected_balance != t.balance:
            if DEBUG:
                expected_for_print = prev.balance + t.amount if t.amount >= 0 else prev.balance - abs(t.amount)
                print(
                    f"Hard flag raised: balance_mismatch between Transaction {i} and Transaction {i-1}.\n"
                    f"Actual balance {t.balance} should be {expected_for_print} "
                    f"(Previous balance {prev.balance} {'+' if t.amount >= 0 else '-'} transaction amount {abs(t.amount)})\n"
                )
            hard_flags.append({
                "type": "balance_mismatch",
                "date": t.date.isoformat(),
                "vendor": t.vendor,
                "transaction_id": t.transaction_id,
                "expected_balance": expected_balance,
                "actual_balance": t.balance,
            })

    # Soft flags
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
        and (print(
            f"Soft flag raised: std_dev_outlier at Transaction {i} (ID: {t.transaction_id}).\n"
            f"Deviation {deviation} greater than Soft Flag epsilon value of {SOFT_FLAG_EPSILON}\n"
        ) or True)
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
        
        print(f"[*] [{job_id}] Analyzing: {body['customer']['name']}")
        await update_job_status(job_id, "ANALYSIS_STARTED")
        
        try:
            results = await perform_analysis(body)
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
            
            print(f"[+] [{job_id}] Analysis finished.")
            await update_job_status(job_id, "ANALYSIS_SUCCESS", json.dumps(results, default=str))

        except Exception as e:
            print(f"[!] [{job_id}] Analysis error: {e}")
            await update_job_status(job_id, "ANALYSIS_FAILED", str(e))

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(INPUT_QUEUE, durable=True)
        print(f" [*] Analysis Worker active. Listening on {INPUT_QUEUE}...")
        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())