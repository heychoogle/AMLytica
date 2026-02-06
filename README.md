# AMLytica Document Pipeline

This project is a financial document (bank statement) processing pipeline built with **FastAPI**. It consists of six services, each responsible for a specific stage of data handling and analysis.

## Services

1. **Orchestrator Service**  
   - Coordinates calls between all services.  
   - Validates inputs and acts as a single source of truth.  

2. **Customer Lookup Service**  
   - Verifies customer IDs (exist) for the orchestrator  
   - Provides full customer details (ID, name, address) to the analysis service to allow flagging inconsistencies between customer data 

3. **Ingest Service**  
   - Handles file uploads 
   - Performs file type validation and basic sanity checks (size, emptiness, allowed formats)  

4. **Extraction Service**  
   - Converts PDFs to text using **pdfplumber** for native PDFs.  
   - **OCR support (pytesseract) is planned for the future**  
     - **But OCR is annoying**  
     - Must handle multi-page documents in correct text order. (not too difficult) 
     - Scanned PDFs often produce inconsistent spacing, misaligned columns, or misread characters. (slightly harder but doable)   
     - Parsing transactions reliably from OCR output requires detecting and normalizing dates, amounts, and balances across pages. (annoying to create comprehensive normalisation) 
     - Proper debit/credit classification is required to avoid false balance mismatches. (hand in hand with the previous bullet)

    Due to these complexities, OCR support is deferred to a future release (But is definitely achieveable).

5. **Analysis Service**  
   - Receives structured data from extraction service.  
   - Applies rules and models to detect potential risks and inconsistencies:  
     - **Soft flags**: Standard deviation outliers (i.e. larger than normal transactions)
     - **Hard flags**: Impossible or mathematically inconsistent transactions (e.g., balance mismatches,).  
        - Also includes inconsistencies in customer name or address when compared to the document.  

6. **Report Service**  
   - Generates structured reports highlighting risks and flagged issues on a per document basis  

## Service Data Flow
![](https://github.com/heychoogle/AMLytica/blob/master/assets/data_flow.gif)

## Current vs Future Features

### Current Features
- PDF ingestion and validation.  
- Text extraction from native PDFs with pdfplumber.  
- Transaction parsing and structured document creation.  
- Analysis service producing soft and hard flags.  
- Report generation from analyzed data.

### Future / Planned
- OCR extraction from scanned PDFs using pytesseract.  
- Multi-page OCR handling with proper transaction ordering.  
- Automatic debit/credit classification in OCR output.  
- Improved parsing for messy OCR outputs (e.g., misaligned columns, missing signs).  
- Enhanced confidence scoring and error handling for OCR-extracted data.