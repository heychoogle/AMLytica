from fastapi import FastAPI
from models.models import AnalysisRequest, AnalysisResponse
from decimal import Decimal
from services.analysis.config import DEBUG, SOFT_FLAG_EPSILON

app = FastAPI()

@app.post("/analyze", response_model=AnalysisResponse)
def analyze_document(req: AnalysisRequest):
    doc = req.document
    transactions = doc.transactions

    total_inflow = sum(t.amount for t in transactions if t.amount > 0)
    total_outflow = sum(t.amount for t in transactions if t.amount < 0)
    net_change = total_inflow + total_outflow
    avg_daily_balance = sum(t.balance for t in transactions) / Decimal(len(transactions))

    # Hard flags
    transactions_sorted = sorted(transactions, key=lambda t: t.date)

    hard_flags = []
    for i, t in enumerate(transactions):
        if i == 0:
            continue

        prev = transactions_sorted[i-1]

        if(t.date.isoformat != transactions_sorted[i].date.isoformat):
            if DEBUG:
                print(f"Hard flag raised: date_mismatch at Transaction {i}. Date misaligned with sorted transaction list.\nAre these transactions in sorted order?")
            hard_flags.append({
                "type": "date_mismatch",
                "transaction_id": t.transaction_id,
                "actual_date": t.date.isoformat(),
                "expected_date": transactions_sorted[i].date.isoformat(),
                "vendor": t.vendor,
                "balance": t.balance,
            })

        expected_balance = prev.balance + t.amount
        if expected_balance != t.balance:
            if DEBUG:
                expected_for_print = prev.balance + t.amount if t.amount >= 0 else prev.balance - abs(t.amount)
                print(
                    f"Hard flag raised: balance_mismatch between Transaction {i} and Transaction {i-1}.\n"
                    f"Actual balance {t.balance} should be {expected_for_print} "
                    f"(Previous balance {prev.balance} {'+' if t.amount >= 0 else '-'} transaction amount {abs(t.amount)})\n"
                )
            hard_flags.append({
                "type": "balance_mismatch",
                "date": t.date.isoformat(),
                "vendor": t.vendor,
                "transaction_id": t.transaction_id,
                "expected_balance": expected_balance,
                "actual_balance": t.balance,

            })



    # Soft flags
    import statistics
    amounts = [t.amount for t in transactions]
    if len(amounts) > 1:
        mean_amt = statistics.mean(amounts)
        std_amt = statistics.stdev(amounts)
    else:
        mean_amt = amounts[0] if amounts else 0
        std_amt = 0

    soft_flags = [
        {
            "type": "std_dev_outlier",
            "transaction_id": t.transaction_id,
            "amount": t.amount,
            "date": t.date,
            "vendor": t.vendor,
            "std_dev_deviation": deviation,
            "std_dev_threshold": SOFT_FLAG_EPSILON
        }
        for t in transactions
        if std_amt > 0
        and (deviation := round(abs(t.amount - mean_amt) / std_amt, 2)) > Decimal(SOFT_FLAG_EPSILON)
        and (print(
            f"Soft flag raised: std_dev_outlier at Transaction {t.transaction_id}.\n"
            f"Deviation {deviation} greater than Soft Flag epsilon value of {SOFT_FLAG_EPSILON}\n"
        ) or True)
    ]

    return AnalysisResponse(
        customer_id=doc.customer_id,
        filename=doc.filename,
        summary={
            "total_inflow": total_inflow,
            "total_outflow": total_outflow,
            "net_change": net_change,
            "avg_daily_balance": avg_daily_balance,
        },
        alerts={
            "soft_flags": soft_flags, 
            "hard_flags": hard_flags,
        }
    )
