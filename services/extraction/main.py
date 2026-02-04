from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.extraction.utils import extract_text_from_pdf
from services.extraction.parser import parse_document
from services.extraction.config import DEBUG
from models.models import Document
import os

app = FastAPI()


class ExtractionRequest(BaseModel):
    """Request model for extraction endpoint"""
    file_path: str
    customer_id: str
    filename: str


class ExtractionResponse(BaseModel):
    """Response model for extraction endpoint"""
    document: Document
    extraction_method: str
    confidence: float


@app.post("/extract", response_model=ExtractionResponse)
async def extract_document(request: ExtractionRequest):
    """
    Extract structured data from a financial document.
    
    Process:
    1. Load PDF from file_path
    2. Extract text (pdfplumber with OCR fallback)
    3. Parse into structured Document with Transactions
    4. Return structured data
    """
    
    # Validate file exists
    if not os.path.exists(request.file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {request.file_path}"
        )
    
    # Validate file is a PDF
    if not request.file_path.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Extract text from PDF
        raw_text, confidence, method = extract_text_from_pdf(request.file_path)
        
        if DEBUG:
            print("=" * 50)
            print("EXTRACTED TEXT:")
            print(raw_text)  # First 1000 chars
            print("=" * 50)

            print(f"Extraction method: {method}, confidence: {confidence:.1f}%")
            print(f"Extracted text length: {len(raw_text)} characters")
        
        # Parse into structured document
        document = parse_document(
            raw_text=raw_text,
            customer_id=request.customer_id,
            filename=request.filename
        )
        
        return ExtractionResponse(
            document=document,
            extraction_method=method,
            confidence=confidence
        )
    
    except ValueError as e:
        # Parsing errors (e.g., insufficient transactions, missing address)
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse document: {str(e)}"
        )
    
    except Exception as e:
        # Unexpected errors
        if DEBUG:
            import traceback
            traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@app.get("/")
def read_root():
    return {"status": "ok", "service": "extraction"}