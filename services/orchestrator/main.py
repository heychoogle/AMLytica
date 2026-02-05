from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import httpx
from services.orchestrator.config import INGEST_URL, CL_URL, EXTRACTION_URL, ANALYSIS_URL

app = FastAPI()


@app.post("/upload")
async def run_pipeline(
    file: UploadFile = File(...),
    customer_id: str = Form(...)
):
    async with httpx.AsyncClient(timeout=60) as client:

        # customer_lookup service
        customer_resp = await client.get(
            f"{CL_URL}/exists/{customer_id}"
        )
        if customer_resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Invalid customer_id"
            )

        # ingest service
        ingest_resp = await client.post(
            f"{INGEST_URL}/upload",
            files={"file": (file.filename, await file.read(), file.content_type)},
            data={"customer_id": customer_id},
        )
        if ingest_resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="File ingest failed"
            )

        ingest_data = ingest_resp.json()

        # extract service
        extract_resp = await client.post(
            f"{EXTRACTION_URL}/extract",
            json={
                "file_path": ingest_data["saved_at"],
                "customer_id": customer_id,
                "filename": ingest_data["filename"],
            },
        )
        if extract_resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Extraction failed"
            )

        extraction_data = extract_resp.json()
        print(extract_resp.json())

        # customer_lookup service
        customer_resp = await client.get(
            f"{CL_URL}/get/{customer_id}"
        )
        if customer_resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Invalid customer_id"
            )

        customer_data = customer_resp.json()

        # analysis service
        analysis_resp = await client.post(
            f"{ANALYSIS_URL}/analyse",
            json={
                "document": extraction_data["document"],
                "customer": customer_data
            },
        )
        if analysis_resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Analysis failed"
            )

        analysis_data = analysis_resp.json()

        # # 5. Generate report
        # report_resp = await client.post(
        #     f"{REPORT_URL}/generate",
        #     json={
        #         "document": extraction_data["document"],
        #         "analysis": analysis_data,
        #     },
        # )
        # if report_resp.status_code != 200:
        #     raise HTTPException(
        #         status_code=500,
        #         detail="Report generation failed"
        #     )

        return {
            "status": "complete",
            "report": analysis_data,
        }
