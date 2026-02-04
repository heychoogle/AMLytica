from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder

from services.analysis.main import app
from models.models import AnalysisRequest, Document, Transaction

client = TestClient(app)

def sample_transactions():
    """Return a list of sample transactions for testing"""
    return [
        Transaction(
            transaction_id=f"TXN{i:03d}",
            date=datetime(2025, 1, i+1),
            vendor=f"Vendor{i}",
            amount=Decimal("100.00"),
            balance=Decimal(f"{1000 + i*100}")
        )
        for i in range(5)
    ]

def create_analysis_request(transactions=None):
    """Create a standard AnalysisRequest with optional custom transactions"""
    transactions = transactions if transactions is not None else sample_transactions()
    doc = Document(
        customer_id="CUST001",
        filename="statement.pdf",
        customer_address="123 Main St, Dublin",
        transactions=transactions
    )
    return AnalysisRequest(document=doc)

def test_analysis_clean_no_flags():
    """Test analysis with normal transactions, expect no flags"""
    req = create_analysis_request()
    response = client.post("/analyse", json=jsonable_encoder(req))
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["alerts"]["hard_flags"] == []
    assert data["alerts"]["soft_flags"] == []

def test_analysis_balance_mismatch_hard_flag():
    """Inject a balance mismatch to trigger a hard flag"""
    transactions = sample_transactions()
    transactions[-1].balance += Decimal("100.00")  # break last transaction
    req = create_analysis_request(transactions)
    response = client.post("/analyse", json=jsonable_encoder(req))
    
    assert response.status_code == 200
    data = response.json()
    
    hard_flags = data["alerts"]["hard_flags"]
    assert any(f["type"] == "balance_mismatch" for f in hard_flags)
    mismatch_flag = next(f for f in hard_flags if f["type"] == "balance_mismatch")
    assert mismatch_flag["actual_balance"] != mismatch_flag["expected_balance"]

def test_analysis_date_mismatch_hard_flag():
    """Inject out-of-order date to trigger a date mismatch"""
    transactions = sample_transactions()
    # Swap first two to break ordering
    transactions[0], transactions[1] = transactions[1], transactions[0]
    req = create_analysis_request(transactions)
    response = client.post("/analyse", json=jsonable_encoder(req))
    
    assert response.status_code == 200
    data = response.json()
    
    hard_flags = data["alerts"]["hard_flags"]
    assert any(f["type"] == "date_mismatch" for f in hard_flags)
    date_flag = next(f for f in hard_flags if f["type"] == "date_mismatch")
    assert date_flag["actual_date"] != date_flag["expected_date"]

def test_analysis_soft_flag_outlier():
    """Inject an extreme transaction to trigger a soft flag"""
    transactions = sample_transactions()
    transactions.append(
        Transaction(
            transaction_id="TXN999",
            date=datetime(2025, 1, 10),
            vendor="BIG BONUS",
            amount=Decimal("5000.00"),
            balance=Decimal("9000.00")
        )
    )
    req = create_analysis_request(transactions)
    response = client.post("/analyse", json=jsonable_encoder(req))
    
    assert response.status_code == 200
    data = response.json()
    
    soft_flags = data["alerts"]["soft_flags"]
    assert any(f["type"] == "std_dev_outlier" for f in soft_flags)
    outlier_flag = next(f for f in soft_flags if f["type"] == "std_dev_outlier")
    assert outlier_flag["amount"] == Decimal("5000.00") or float(outlier_flag["amount"]) == 5000.0

def test_analysis_empty_transactions():
    """Analysis on document with no transactions should return zeros and no crashes"""
    doc = Document(
        customer_id="CUST001",
        filename="empty.pdf",
        customer_address="123 Main St, Dublin",
        transactions=[]
    )
    req = AnalysisRequest(document=doc)
    response = client.post("/analyse", json=jsonable_encoder(req))
    
    assert response.status_code == 200
    data = response.json()
    
    summary = data["summary"]
    # doing string checks here because JSON doesn't serialise Decimal 0 and this is the simplest way while still being accurate
    assert summary["total_inflow"] == "0"
    assert summary["total_outflow"] == "0"
    assert summary["net_change"] == "0"
    assert summary["avg_daily_balance"] == "0"
    assert data["alerts"]["hard_flags"] == []
    assert data["alerts"]["soft_flags"] == []
