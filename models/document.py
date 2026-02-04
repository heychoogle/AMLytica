from pydantic import BaseModel

class Transaction(BaseModel):
    transaction_id: str
    date: str
    vendor: str
    amount: float
    balance: float

class Document(BaseModel):
    customer_id: str
    filename: str
    customer_address: str
    transactions: list[Transaction]