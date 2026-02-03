import os
import shutil
import pytest
from fastapi.testclient import TestClient

from services.ingest.main import app
from services.ingest.config import UPLOAD_DIR

client = TestClient(app)

# cleanup
@pytest.fixture(autouse=True)
def cleanup_uploads():
    yield
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

# test
def test_upload_file():
    # mock file contents
    file_content = b"test file content"
    file_name = "test.txt"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, "text/plain")}
    )
    
    # Check response status
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == file_name
    assert data["content_type"] == "text/plain"
    
    # Check file was saved
    saved_path = data["saved_at"]
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as f:
        assert f.read() == file_content
