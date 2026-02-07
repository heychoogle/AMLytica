import json
import uuid
import aio_pika
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from sqlalchemy import null
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db import engine, Base, get_db
from shared.models import Job, JobEvent
from services.ingest.utils import save_uploaded_file
from services.ingest.config import UPLOAD_DIR, DEBUG, MAX_FILE_SIZE, ALLOWED_TYPES, RABBITMQ_URL

app = FastAPI()

# Automatically create database tables on startup
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/upload")
async def upload_single_file(
    file: UploadFile = File(...), 
    customer_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # validate uploaded file
    mime_type = file.content_type.split(";")[0].lower()
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {mime_type}")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # generate identity and save to disk (this should work with S3)
    job_id = str(uuid.uuid4())
    saved_path = save_uploaded_file(UPLOAD_DIR, file.filename, content)

    # database try/except
    try:
        # job record
        new_job = Job(
            job_id=job_id, 
            customer_id=customer_id, 
            filename=file.filename
        )

        # create jobs_event row
        initial_event = JobEvent(
            job_id=job_id, 
            status="UPLOADED", 
            message=saved_path
        )

        db.add(new_job)
        db.add(initial_event)
        await db.commit()
        
    except Exception as e:
        if DEBUG: print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Database persistence failed")

    # rabbitmq try/except
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue("raw_extraction_queue", durable=True)
            
            payload = {
                "job_id": job_id,
                "file_path": saved_path,
                "customer_id": customer_id,
                "filename": file.filename
            }

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    correlation_id=job_id
                ),
                routing_key="raw_extraction_queue",
            )

    except Exception as e:
        if DEBUG: print(f"RabbitMQ Error: {e}")
        
        # update job as failed since it never made the queue
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    # update main job to Failed
                    await session.execute(
                        update(Job)
                        .where(Job.job_id == job_id)
                        .values(current_status="QUEUE_FAILED")
                    )
                    
                    # create job event 
                    event = JobEvent(
                        job_id=job_id, 
                        status="QUEUE_FAILED", 
                        message="MQ unreachable",
                        # no worker name, ingest doesn't have workers
                    )
                    session.add(event)
        except Exception as db_e:
            # db failure error
            if DEBUG: print(f"Critical DB failure while logging RabbitMQ error: {db_e}")

        raise HTTPException(
            status_code=503,
            detail="Job queue is currently unavailable. Please try again shortly."
        )

    return {
        "status": "queued",
        "job_id": job_id,
        "filename": file.filename
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ingest"}