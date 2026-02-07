import asyncio
import aio_pika
import json
import os
import httpx  
from sqlalchemy import update
from shared.db import AsyncSessionLocal
from shared.models import Job, JobEvent
from services.extraction.utils import extract_text_from_pdf
from services.extraction.parser import parse_document
from services.extraction.config import RABBITMQ_URL, INPUT_QUEUE, OUTPUT_QUEUE, CL_URL

WORKER_NAME = os.getenv('HOSTNAME', 'extraction_worker_local')

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

async def fetch_customer_metadata(customer_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{CL_URL}/get/{customer_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[!] [{WORKER_NAME}] Customer lookup error: {e}")
            return None

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        job_id = message.correlation_id
        data = json.loads(message.body.decode())
        customer_id = data.get('customer_id')
        
        print(f"[*] [{WORKER_NAME}] processing job {job_id}: {data.get('filename')}")
        await update_job_status(job_id, "EXTRACTION_STARTED")

        try:
            customer_data = await fetch_customer_metadata(customer_id)
            if not customer_data:
                raise Exception(f"Validation failed: Customer {customer_id} not found in database.")

            raw_text, confidence, method = extract_text_from_pdf(data['file_path'])
            document = parse_document(
                raw_text=raw_text,
                customer_id=customer_id,
                filename=data.get("filename")
            )

            analysis_payload = {
                "customer": customer_data, 
                "document": document.dict()
            }

            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue(OUTPUT_QUEUE, durable=True)
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(analysis_payload, default=str).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        correlation_id=job_id 
                    ),
                    routing_key=OUTPUT_QUEUE,
                )
            
            print(f"[+] [{WORKER_NAME}] [{job_id}] Extraction complete.")
            await update_job_status(job_id, "EXTRACTION_SUCCESS", json.dumps(analysis_payload, default=str))

        except Exception as e:
            print(f"[!] [{WORKER_NAME}] [{job_id}] Extraction failed: {str(e)}")
            await update_job_status(job_id, "EXTRACTION_FAILED", str(e))

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(INPUT_QUEUE, durable=True)
        print(f" [*] [{WORKER_NAME}] Extraction Worker active. Listening on {INPUT_QUEUE}...")
        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())