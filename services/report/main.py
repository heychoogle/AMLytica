from fastapi import FastAPI
from models.models import ReportRequest, ReportResponse

app = FastAPI()

@app.post("/generate")
def generate_report(req: ReportRequest):

    print(req.json())

    soft_flags = req.analysis.alerts["soft_flags"]
    hard_flags = req.analysis.alerts["hard_flags"]
    print(f"Soft flags: {len(soft_flags)}\nHard flags: {len(hard_flags)}")
    response_data = ReportResponse(
        flags=req.analysis.alerts
    )
    return response_data

@app.get("/")
def read_root():
    return {"status": "ok"}