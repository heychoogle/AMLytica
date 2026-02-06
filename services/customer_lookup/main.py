from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared.db import AsyncSessionLocal
from shared.models import Customer
import json
from pathlib import Path

app = FastAPI()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.get("/get/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "address": customer.address
    }

@app.post("/seed")
async def seed_customers(db: AsyncSession = Depends(get_db)):
    DATA_FILE = Path(__file__).parent.parent.parent / "data" / "customers.json"
    
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    
    for cid, info in data.items():
        customer = Customer(
            customer_id=cid,
            name=info["name"],
            address=info["address"]
        )
        await db.merge(customer)
    
    await db.commit()
    return {"message": f"Imported {len(data)} customers"}

@app.get("/")
def health_check():
    return {"status": "ok", "source": "database"}