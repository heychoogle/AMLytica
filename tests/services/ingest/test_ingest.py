import os
import shutil
import pytest
import time
from fastapi.testclient import TestClient

from services.ingest.main import app
from services.ingest.config import UPLOAD_DIR, MAX_FILE_SIZE

client = TestClient(app)

# override upload dir for tests
@pytest.fixture(autouse=True)
def temp_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("services.ingest.main.UPLOAD_DIR", tmp_path)
    return tmp_path


# upload a valid file
def test_upload_file_valid_success():
    # mock file contents
    file_content = b"test file content"
    file_name = "test.pdf"
    file_type = "application/pdf"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == file_name
    assert data["content_type"] == file_type
    
    # Check file was saved
    saved_path = data["saved_at"]
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as f:
        assert f.read() == file_content

# upload a file with additional file_type args
def test_upload_file_additional_file_type_args_sucess():
    # mock file contents
    file_content = b"test file content"
    file_name = "test.pdf"
    file_type = "application/pdf; charset=binary"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == file_name
    assert data["content_type"] == file_type
    
    # Check file was saved
    saved_path = data["saved_at"]
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as f:
        assert f.read() == file_content

# upload a file with a capitalised file_type
def test_upload_file_capitalised_file_type_success():
    # mock file contents
    file_content = b"test file content"
    file_name = "test.pdf"
    file_type = "APPLICATION/PDF"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == file_name
    assert data["content_type"] == file_type
    
    # Check file was saved
    saved_path = data["saved_at"]
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as f:
        assert f.read() == file_content

# upload a file with an invalid filetype
def test_upload_file_invalid_filetype_fail():
    # mock file contents
    file_content = b"test file content"
    file_name = "test.txt"
    file_type = "text/plain"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 400
    data = response.json()
    # validate error message exists with no additional fields
    assert set(data.keys()) == {"detail"}
    assert "Invalid file type" in data["detail"]

# upload a file with an invalid filetype
def test_upload_file_invalid_filepath_fail():
    # mock file contents
    file_content = b"test file content"
    file_name = "test.txt"
    file_type = "text/plain"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 400
    data = response.json()
    # validate error message exists with no additional fields
    assert set(data.keys()) == {"detail"}
    assert "Invalid file type" in data["detail"]

# upload a file with empty content
def test_upload_file_empty_content_fail():
    # mock file contents
    file_content = b""
    file_name = "empty.pdf"
    file_type = "application/pdf"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 400
    data = response.json()
    # validate error message exists with no additional fields
    assert set(data.keys()) == {"detail"}
    assert "File is empty" in data["detail"]

# upload a file on the size limit for content
def test_upload_file_on_size_limit_success():
    # mock file contents
    file_content = b"x" * (MAX_FILE_SIZE) 
    file_name = "big.pdf"
    file_type = "application/pdf"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == file_name
    assert data["content_type"] == file_type
    
    # Check file was saved
    saved_path = data["saved_at"]
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as f:
        assert f.read() == file_content

# upload a file with too much content
def test_upload_file_over_size_limit_fail():
    # mock file contents
    file_content = b"x" * (MAX_FILE_SIZE+1) 
    file_name = "big.pdf"
    file_type = "application/pdf"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, file_content, file_type)}
    )
    
    # Check response status
    assert response.status_code == 413
    data = response.json()
    # validate error message exists with no additional fields
    assert set(data.keys()) == {"detail"}
    assert "File too large" in data["detail"]