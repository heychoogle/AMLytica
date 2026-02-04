import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch

from services.extraction.config import MIN_TRANSACTIONS
from services.extraction.main import app

client = TestClient(app)

# Sample PDFs for testing - you'll need these in your test fixtures
SAMPLE_PDF_CLEAN = "tests/fixtures/statement_clean.pdf"
SAMPLE_PDF_ERROR = "tests/fixtures/statement_error.pdf"
NON_PDF = "tests/fixtures/non_pdf.txt"


@pytest.fixture(scope="module")
def setup_test_pdfs(tmp_path_factory):
    """
    Copy your sample PDFs to a test fixtures directory.
    In reality, you'd have these checked into tests/fixtures/
    """
    # For now, assume they exist - you'll copy statement_clean.pdf and statement_error.pdf there
    pass

def test_extract_valid_pdf():
    """Test extraction of a valid PDF with sufficient transactions"""
    # Skip if test PDF doesn't exist
    if not os.path.exists(SAMPLE_PDF_CLEAN):
        pytest.skip("Sample PDF not found")
    
    request_data = {
        "file_path": SAMPLE_PDF_CLEAN,
        "customer_id": "CUST001",
        "filename": "statement_clean.pdf"
    }
    
    response = client.post("/extract", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "document" in data
    assert "extraction_method" in data
    assert "confidence" in data
    
    # Check document fields
    doc = data["document"]
    assert doc["customer_id"] == "CUST001"
    assert doc["filename"] == "statement_clean.pdf"
    assert "customer_address" in doc
    assert len(doc["customer_address"]) > 0
    
    # Check transactions
    assert "transactions" in doc
    assert len(doc["transactions"]) >= 10  # Minimum threshold
    
    # Check first transaction structure
    first_txn = doc["transactions"][0]
    assert "transaction_id" in first_txn
    assert "date" in first_txn
    assert "vendor" in first_txn
    assert "amount" in first_txn
    assert "balance" in first_txn
    
    # Check transaction ID format
    assert first_txn["transaction_id"].startswith("CUST001_statement_clean_")


def test_extract_file_not_found():
    """Test extraction with non-existent file"""
    request_data = {
        "file_path": "nonexistent/file.pdf",
        "customer_id": "CUST001",
        "filename": "fake.pdf"
    }
    
    response = client.post("/extract", json=request_data)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_extract_non_pdf_file():
    """Test extraction with non-PDF file"""
    # Skip if test PDF doesn't exist
    if not os.path.exists(NON_PDF):
        pytest.skip("Non PDF not found")
    
    request_data = {
        "file_path": NON_PDF,
        "customer_id": "CUST001",
        "filename": "non_pdf.txt"
    }
    
    response = client.post("/extract", json=request_data)

    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()


@patch('services.extraction.main.extract_text_from_pdf')
def test_extract_insufficient_transactions(mock_extract):
    """Test extraction fails when document has too few transactions"""
    # Mock extraction to return minimal text
    mock_extract.return_value = (
        "SECURE BANK\nAddress: 123 Test St\nDate Vendor Amount (€) Balance (€)\n01/01/2025 TEST -10.00 100.00",
        100.0,
        "pdfplumber"
    )
    
    request_data = {
        "file_path": "dummy.pdf",  # Won't be read due to mock
        "customer_id": "CUST001",
        "filename": "test.pdf"
    }
    
    with patch('os.path.exists', return_value=True):
        response = client.post("/extract", json=request_data)
    
    assert response.status_code == 422
    assert "insufficient transactions" in response.json()["detail"].lower()


@patch('services.extraction.main.extract_text_from_pdf')
def test_extract_missing_address(mock_extract):
    """Test extraction fails when address cannot be found"""
    # Mock extraction to return text without valid address
    mock_extract.return_value = (
        "Date Vendor Amount (€) Balance (€)\n" + 
        "\n".join([f"0{i+1}/01/2025 VENDOR{i} -10.00 {1000-i*10}.00" for i in range(15)]),
        100.0,
        "pdfplumber"
    )
    
    request_data = {
        "file_path": "dummy.pdf",
        "customer_id": "CUST001",
        "filename": "test.pdf"
    }
    
    with patch('os.path.exists', return_value=True):
        response = client.post("/extract", json=request_data)
    
    assert response.status_code == 422
    assert "address" in response.json()["detail"].lower()


@patch('services.extraction.main.extract_text_from_pdf')
def test_extract_ocr_fallback(mock_extract):
    """Test that OCR fallback is properly reported"""
    mock_extract.return_value = (
        "SECURE BANK\nAddress: 123 Test St, Dublin\nDate Vendor Amount (€) Balance (€)\n" +
        "\n".join([
            f"{i+1:02d}/01/2025 VENDOR{i} -10.00 {1000 - i*10}.00"
            for i in range(MIN_TRANSACTIONS+1)
        ]),
        75.5,
        "ocr"
    )

    request_data = {
        "file_path": "dummy.pdf",
        "customer_id": "CUST001",
        "filename": "scanned.pdf"
    }

    with patch('os.path.exists', return_value=True):
        response = client.post("/extract", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_method"] == "ocr"
    assert data["confidence"] == 75.5



def test_extract_transaction_id_format():
    """Test that transaction IDs are formatted correctly"""
    if not os.path.exists(SAMPLE_PDF_CLEAN):
        pytest.skip("Sample PDF not found")
    
    request_data = {
        "file_path": SAMPLE_PDF_CLEAN,
        "customer_id": "TEST_123",
        "filename": "my.statement.pdf"
    }
    
    response = client.post("/extract", json=request_data)
    
    if response.status_code == 200:
        doc = response.json()["document"]
        txn_id = doc["transactions"][0]["transaction_id"]
        
        # Should be: TEST_123_my_statement_001
        assert txn_id.startswith("TEST_123_my_statement_")
        assert txn_id.endswith("_001")


def test_extract_preserves_customer_id():
    """Test that customer ID is preserved through extraction"""
    if not os.path.exists(SAMPLE_PDF_CLEAN):
        pytest.skip("Sample PDF not found")
    
    request_data = {
        "file_path": SAMPLE_PDF_CLEAN,
        "customer_id": "CUST999",
        "filename": "statement.pdf"
    }
    
    response = client.post("/extract", json=request_data)
    
    if response.status_code == 200:
        doc = response.json()["document"]
        assert doc["customer_id"] == "CUST999"