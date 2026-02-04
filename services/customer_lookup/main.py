import json
from fastapi import FastAPI, HTTPException
from pathlib import Path

app = FastAPI()

# Load customer data on startup
DATA_FILE = Path(__file__).parent / "data" / "customers.json"

with open(DATA_FILE, "r") as f:
    CUSTOMERS = json.load(f)

@app.get("/exists/{customer_id}")
def validate_customer_id(customer_id: str):
    """
    Look up customer by ID.
    Returns customer ID if found, else error
    """
    customer = CUSTOMERS.get(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {customer_id} not found"
        )
    
    return customer_id

@app.get("/")
def read_root():
    return {"status": "ok", "service": "customer-lookup"}