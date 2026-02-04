import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from typing import Tuple
from services.extraction.config import OCR_CONFIDENCE_THRESHOLD, DEBUG


def extract_text_from_pdf(file_path: str) -> Tuple[str, float, str]:
    """
    Extract text from PDF using pdfplumber first, falling back to OCR if needed.
    
    Returns:
        Tuple of (extracted_text, confidence_score, method_used)
        - extracted_text: The full text content
        - confidence_score: 100.0 for pdfplumber, OCR confidence for pytesseract
        - method_used: "pdfplumber" or "ocr"
    """
    
    # Try pdfplumber first (for native PDFs)
    try:
        text = _extract_with_pdfplumber(file_path)
        
        # Check if we got meaningful content
        if _is_meaningful_text(text):
            if DEBUG:
                print(f"Successfully extracted text using pdfplumber: {len(text)} characters")
            return text, 100.0, "pdfplumber"
        else:
            if DEBUG:
                print("pdfplumber extraction yielded insufficient content, falling back to OCR")
    
    except Exception as e:
        if DEBUG:
            print(f"pdfplumber extraction failed: {e}, falling back to OCR")
    
    # Fall back to OCR (for scanned documents)
    try:
        text, confidence = _extract_with_ocr(file_path)
        
        if confidence < OCR_CONFIDENCE_THRESHOLD:
            if DEBUG:
                print(f"Warning: OCR confidence ({confidence:.1f}%) below threshold ({OCR_CONFIDENCE_THRESHOLD}%)")
        
        return text, confidence, "ocr"
    
    except Exception as e:
        raise Exception(f"Both pdfplumber and OCR extraction failed: {e}")


def _extract_with_pdfplumber(file_path: str) -> str:
    """Extract text using pdfplumber"""
    text_parts = []
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    
    return "\n".join(text_parts)


def _extract_with_ocr(file_path: str) -> Tuple[str, float]:
    """
    Extract text using OCR (pytesseract).
    
    Returns:
        Tuple of (extracted_text, average_confidence)
    """
    # Convert PDF to images
    images = convert_from_path(file_path)
    
    text_parts = []
    confidences = []
    
    for image in images:
        # Get OCR data with confidence scores
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Extract text and confidences
        page_text = []
        page_confidences = []
        
        for i, word in enumerate(ocr_data['text']):
            if word.strip():  # Skip empty strings
                page_text.append(word)
                conf = int(ocr_data['conf'][i])
                if conf > 0:  # pytesseract returns -1 for unrecognized
                    page_confidences.append(conf)
        
        text_parts.append(" ".join(page_text))
        confidences.extend(page_confidences)
    
    full_text = "\n".join(text_parts)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    return full_text, avg_confidence


def _is_meaningful_text(text: str) -> bool:
    """
    Check if extracted text is meaningful (contains enough content).
    
    For financial documents, we expect:
    - Reasonable length (>100 chars)
    - Contains numbers (amounts, balances)
    - Contains date-like patterns
    """
    if not text or len(text) < 100:
        return False
    
    # Check for numbers (financial documents should have many)
    digit_count = sum(c.isdigit() for c in text)
    if digit_count < 20:  # Arbitrary threshold
        return False
    
    # Check for common date separators
    has_dates = '/' in text or '-' in text
    
    return has_dates