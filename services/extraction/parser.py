import re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from models.models import Document, Transaction
from services.extraction.config import MIN_TRANSACTIONS, DEBUG


def parse_document(raw_text: str, customer_id: str, filename: str) -> Document:
    """
    Parse raw extracted text into a structured Document object.
    
    Args:
        raw_text: The full text extracted from the PDF
        customer_id: Customer ID from upstream
        filename: Original filename
    
    Returns:
        Document object with parsed transactions and metadata
    
    Raises:
        ValueError: If unable to parse required fields or insufficient transactions
    """
    
    # Extract customer address
    customer_address = _extract_address(raw_text)
    
    if not customer_address:
        raise ValueError("Could not extract customer address from document")
    
    # Extract transactions
    transactions = _extract_transactions(raw_text, customer_id, filename)
    
    if len(transactions) < MIN_TRANSACTIONS:
        raise ValueError(
            f"Insufficient transactions: found {len(transactions)}, "
            f"minimum required is {MIN_TRANSACTIONS}"
        )
    
    if DEBUG:
        print(f"Parsed document: {len(transactions)} transactions, address: {customer_address}")
    
    return Document(
        customer_id=customer_id,
        filename=filename,
        customer_address=customer_address,
        transactions=transactions
    )


def _extract_address(text: str) -> Optional[str]:
    """
    Extract customer address from document text.
    
    Looks for patterns like:
    - "Address: 123 Main St..."
    - Lines containing street numbers and postcodes
    """
    
    # Try explicit "Address:" label first
    address_match = re.search(r'Address:\s*(.+)', text, re.IGNORECASE)
    if address_match:
        address_line = address_match.group(1).strip()
        # Take up to the next newline or next labeled field
        address_line = re.split(r'\n|Account', address_line)[0].strip()
        if len(address_line) > 10:  # Sanity check
            return address_line
    
    # Fallback: Look for common address patterns (number + street + area/city)
    # This is a simple heuristic
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Look for lines with numbers and common address words
        if re.search(r'\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd)', line, re.IGNORECASE):
            # Potentially an address - take this line and maybe the next
            address_parts = [line.strip()]
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # If next line looks like city/postcode, include it
                if re.search(r'[A-Z][a-z]+|[A-Z0-9\s]+', next_line):
                    address_parts.append(next_line)
            return ', '.join(address_parts)
    
    return None


def _extract_transactions(raw_text: str, customer_id: str, filename: str) -> List[Transaction]:
    """
    Extract transaction table from raw text and parse into Transaction objects.
    
    Expected format:
    Date        Vendor              Amount (€)    Balance (€)
    01/01/2025  TESCO STORES        -45.23        1234.56
    """
    
    transactions = []
    lines = raw_text.split('\n')
    
    # Find the transaction table (look for header row)
    table_start = None
    for i, line in enumerate(lines):
        # Look for header containing date, amount, balance keywords
        if re.search(r'Date.*Amount.*Balance', line, re.IGNORECASE):
            table_start = i + 1  # Data starts after header
            break
    
    if table_start is None:
        if DEBUG:
            print("Warning: Could not find transaction table header")
        return transactions
    
    # Parse transaction rows
    txn_counter = 1
    for line in lines[table_start:]:
        line = line.strip()
        if not line:
            continue
        
        # Pattern: DD/MM/YYYY VENDOR_NAME +/-AMOUNT BALANCE
        # Use regex to extract components
        # Date: DD/MM/YYYY
        # Vendor: Everything between date and amount
        # Amount: +/- followed by digits and decimal
        # Balance: Final number
        
        match = re.match(
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-+]?\d+\.\d{2})\s+(\d+\.\d{2})$',
            line
        )
        
        if not match:
            continue
        
        date_str = match.group(1)
        vendor = match.group(2).strip()
        amount_str = match.group(3)
        balance_str = match.group(4)
        
        # Parse amount and balance
        try:
            amount = Decimal(amount_str)
            balance = Decimal(balance_str)
        except ValueError:
            if DEBUG:
                print(f"Failed to parse transaction: {line}")
            continue
        
        # Generate transaction ID
        filename_base = filename.replace('.pdf', '').replace('.', '_')
        txn_id = f"{customer_id}_{filename_base}_{txn_counter:03d}"
        
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")

        transactions.append(Transaction(
            transaction_id=txn_id,
            date=date_obj,
            vendor=vendor,
            amount=amount,
            balance=balance
        ))
        
        txn_counter += 1
    
    if DEBUG:
        print(f"Extracted {len(transactions)} transactions")
    
    return transactions