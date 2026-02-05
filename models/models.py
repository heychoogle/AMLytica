from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

class Transaction(BaseModel):
    transaction_id: str
    date: datetime
    vendor: str
    amount: Decimal
    balance: Decimal

class Document(BaseModel):
    customer_id: str
    filename: str
    customer_address: str
    transactions: list[Transaction]

class AnalysisRequest(BaseModel):
    document: Document
    address: str

class AnalysisResponse(BaseModel):
    customer_id: str
    customer_address: str
    filename: str
    summary: Dict[str, Decimal]
    alerts: Dict[str, List[Dict[str, Any]]]

class ExtractionRequest(BaseModel):
    file_path: str
    customer_id: str
    filename: str


class ExtractionResponse(BaseModel):
    document: Document
    extraction_method: str
    confidence: float