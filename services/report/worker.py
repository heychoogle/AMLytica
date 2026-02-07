import asyncio
import aio_pika
import json
import os
from datetime import datetime
from sqlalchemy import update
from shared.db import AsyncSessionLocal
from shared.models import Job, JobEvent
from services.report.config import RABBITMQ_URL, INPUT_QUEUE, REPORTS_DIR

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

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        job_id = message.correlation_id
        payload = json.loads(message.body.decode())
        
        print(f"[*] [{job_id}] Generating Report...")
        await update_job_status(job_id, "REPORTING_STARTED")

        try:
            payload["job_id"] = job_id
            payload["generated_at"] = datetime.now().isoformat()

            customer_name = payload.get("customer", {}).get("name", "unknown").replace(" ", "_")
            report_filename = f"report_{customer_name}_{job_id[:8]}.json"
            report_path = os.path.join(REPORTS_DIR, report_filename)

            os.makedirs(REPORTS_DIR, exist_ok=True)
            with open(report_path, "w") as f:
                json.dump(payload, f, indent=4)
            
            print(f"[✓] [{job_id}] Final Report saved: {report_path}")
            await update_job_status(job_id, "COMPLETED", str(payload))

        except Exception as e:
            print(f"[!] [{job_id}] Report error: {e}")
            await update_job_status(job_id, "REPORTING_FAILED", str(e))

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(INPUT_QUEUE, durable=True)
        
        print(f" [*] Report Worker active. Listening on {INPUT_QUEUE}...")
        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())