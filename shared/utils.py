from shared.db import AsyncSessionLocal
from shared.models import Job, JobEvent
from sqlalchemy import update

async def update_job_status(job_id: str, status: str, message: str = None):
    async with AsyncSessionLocal() as session:
        async with session.begin():

            await session.execute(
                update(Job)
                .where(Job.job_id == job_id)
                .values(current_status=status)
            )
            
            event = JobEvent(job_id=job_id, status=status, message=message)
            session.add(event)