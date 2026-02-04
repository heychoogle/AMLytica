import os
import time
import httpx
from fastapi import HTTPException
from services.ingest.config import CL_URL

async def validate_customer_id(customer_id: str) -> str:
    """
    Validate that customer exists by calling customer-lookup service.
    Returns customer_id if valid, raises HTTPException if not.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CL_URL}/exists/{customer_id}",
                timeout=5.0
            )
            response.raise_for_status()
            # Customer lookup returns just the customer_id on success
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Customer {customer_id} not found"
                )
            raise HTTPException(
                status_code=502,
                detail="Customer lookup service error"
            )
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Customer lookup service unavailable"
            )



def save_uploaded_file(upload_dir: str, filename: str, content: bytes) -> str:
    """
    Save uploaded file content to the given directory and return the path.
    Sanitizes filename to prevent path traversal attacks.
    """
    os.makedirs(upload_dir, exist_ok=True)
    
    # Sanitize filename - strip path components and keep only basename
    safe_filename = os.path.basename(filename)
    
    # filename sanity check, if somehow still empty or just "."
    if not safe_filename or safe_filename == ".":
        safe_filename = "uploaded_file" + time.time()
    
    file_location = os.path.join(upload_dir, safe_filename)
    
    with open(file_location, "wb") as f:
        f.write(content)
    
    return file_location