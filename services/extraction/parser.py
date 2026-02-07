import re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from models.models import Document, Transaction
from services.extraction.config import MIN_TRANSACTIONS, DEBUG


def parse_document(raw_text: str, customer_id: str, filename: str) -> Document:
    
    # Extract account holder
    account_holder_name = _extract_account_holder(raw_text)
    
    if not account_holder_name:
        raise ValueError("Could not extract account holder name from document")

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
        customer_name=account_holder_name,
        customer_address=customer_address,
        filename=filename,
        transactions=transactions
    )

def _extract_account_holder(text: str) -> Optional[str]:
    patterns = [
        r"(?i)Account\s*Holder\s*:\s*(.*)",
        r"(?i)Name\s*:\s*(.*)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Clean up the line
            raw_name = match.group(1).strip()
            # Stop if we hit another common label or a double newline
            clean_name = re.split(r'(?i)Address|Date|Statement|\n', raw_name)[0]
            # Remove artifacts like | or *
            clean_name = re.sub(r'[|*]', '', clean_name).strip()
            
            if len(clean_name) > 1:
                return clean_name
    
    return None

def _extract_address(text: str) -> Optional[str]:

    # explicit regex
    address_match = re.search(r"(?i)Address\s*:\s*(.*)", text)
    if address_match:
        raw_address = address_match.group(1).strip()

        clean_address = re.split(r'(?i)Account|Date|Statement|\n\n', raw_address)[0]
        clean_address = re.sub(r'[|*]', '', clean_address).strip()
        if len(clean_address) > 5:
            return clean_address

    # heuristic search, lines with City/Country/Postcode patterns
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for i, line in enumerate(lines):
        if re.search(r'\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Way|Lane|Ln|Drive|Dr)', line, re.IGNORECASE):
            full_addr = line
            if i + 1 < len(lines):
                full_addr += ", " + lines[i+1]
            return re.sub(r'[|*]', '', full_addr).strip()

    return None


def _extract_transactions(raw_text: str, customer_id: str, filename: str) -> List[Transaction]:
    transactions = []
    lines = raw_text.split('\n')
    
    table_start = None
    for i, line in enumerate(lines):
        if any(keyword in line.upper() for keyword in ["DATE", "VENDOR", "AMOUNT", "BALANCE"]):
            table_start = i + 1
            break
    
    if table_start is None:
        return []

    txn_counter = 1
    for line in lines[table_start:]:
        line = line.strip()
        if not line: continue

        # date extraction
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', line)
        if not date_match:
            continue
        
        date_str = date_match.group(1)
        remaining_text = line.replace(date_str, "").strip()

        # extract numbers
        amount_matches = re.findall(r'([-+]?\d{1,3}(?:,\d{3})*\.\d{2}|[-+]?\d+\.\d{2})', remaining_text)

        if len(amount_matches) < 2:
            continue

        try:
            # usual amount/balance order
            amount_str = amount_matches[-2]
            balance_str = amount_matches[-1]

            # extract vendor
            vendor = remaining_text.replace(amount_str, "").replace(balance_str, "").strip()
            vendor = re.sub(r'[|€$¥]', '', vendor).strip()

            # cleaning data to convert to Decimal
            amount = Decimal(amount_str.replace(',', ''))
            balance = Decimal(balance_str.replace(',', ''))
            
            # date normalisation
            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                date_obj = datetime.strptime(date_str, "%d/%m/%y")

            txn_id = f"{customer_id}_{filename.split('.')[0]}_{txn_counter:03d}"
            
            transactions.append(Transaction(
                transaction_id=txn_id,
                date=date_obj,
                vendor=vendor,
                amount=amount,
                balance=balance
            ))
            txn_counter += 1

        except Exception as e:
            if DEBUG: print(f"Row skip: {e} on line: {line}")
            continue
            
    return transactions