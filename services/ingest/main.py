import json
import uuid
import aio_pika
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Internal imports from our shared library and local config
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
    # 1. Validation Logic
    mime_type = file.content_type.split(";")[0].lower()
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {mime_type}")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # 2. Generate Identity & Save to Disk (S3-ready)
    job_id = str(uuid.uuid4())
    saved_path = save_uploaded_file(UPLOAD_DIR, file.filename, content)

    # 3. DATABASE INTEGRATION: Create Audit Trail
    try:
        # Create parent Job record
        new_job = Job(
            job_id=job_id, 
            customer_id=customer_id, 
            filename=file.filename
        )

        # Create first "UPLOADED" event with timestamp
        initial_event = JobEvent(
            job_id=job_id, 
            status="UPLOADED", 
            message=saved_path
        )

        db.add(new_job)
        db.add(initial_event)
        await db.commit() # Persistent tracking established
        
    except Exception as e:
        if DEBUG: print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Database persistence failed")

    # 4. Publish to RabbitMQ
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
        # Note: In a production system, you'd mark the Job as FAILED in the DB here
        raise HTTPException(status_code=500, detail="Messaging queue unavailable")

    return {
        "status": "queued",
        "job_id": job_id,
        "filename": file.filename
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ingest"}