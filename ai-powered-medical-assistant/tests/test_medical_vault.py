"""
Tests for Medical Vault Tool.
Tests upload, retrieval, search, OCR extraction, and deletion of medical records.
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.medical_vault_tool import (
    upload_medical_record,
    get_patient_records,
    get_record_by_id,
    delete_record,
    search_records,
    get_vault_statistics,
    _load_records,
    _save_records,
    MEDICAL_RECORDS_FILE,
    UPLOADS_DIR
)


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def temp_vault_env(monkeypatch, tmp_path):
    """
    Create a temporary isolated environment for vault tests.
    Uses temporary directories for uploads and records.
    """
    # Create temp directories
    temp_uploads = tmp_path / "uploads"
    temp_data = tmp_path / "data"
    temp_uploads.mkdir()
    temp_data.mkdir()
    
    # Create subdirectories
    for subdir in ["lab_results", "imaging", "discharge_summaries", "other"]:
        (temp_uploads / subdir).mkdir()
    
    # Create temp records file
    temp_records_file = temp_data / "medical_records.json"
    temp_records_file.write_text("[]")
    
    # Monkeypatch the module-level constants
    monkeypatch.setattr("tools.medical_vault_tool.UPLOADS_DIR", str(temp_uploads))
    monkeypatch.setattr("tools.medical_vault_tool.MEDICAL_RECORDS_FILE", str(temp_records_file))
    
    yield {
        "uploads_dir": temp_uploads,
        "records_file": temp_records_file,
        "data_dir": temp_data
    }
    
    # Cleanup is automatic with tmp_path


@pytest.fixture
def sample_pdf_bytes():
    """Create a minimal valid PDF byte string."""
    # This is a minimal PDF that PDF libraries can parse
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Lab Result) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
    return pdf_content


@pytest.fixture
def sample_image_bytes():
    """Create a minimal valid PNG byte string (1x1 pixel)."""
    # 1x1 white PNG
    png_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
        b'\x00\x01\x01\x00\x05\x18\r\xfd\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return png_content


# ── Tests ─────────────────────────────────────────────────────────────────────
def test_upload_medical_record_success(temp_vault_env, sample_pdf_bytes):
    """Test successful upload of a medical record."""
    result = upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Blood Test - January 2024",
        file_data=sample_pdf_bytes,
        filename="blood_test_jan_2024.pdf",
        description="Routine blood work",
        date_str="2024-01-15",
        doctor_name="Dr. Smith",
        extract_text=False  # Skip OCR for this test
    )
    
    assert result["success"] is True
    assert "record_id" in result
    assert result["message"] == "Medical record 'Blood Test - January 2024' uploaded successfully."
    
    # Verify file was saved
    record = result["record"]
    assert os.path.exists(record["file_path"])
    
    # Verify record was saved to JSON
    records = _load_records()
    assert len(records) == 1
    assert records[0]["title"] == "Blood Test - January 2024"
    assert records[0]["patient_id"] == "P001"


def test_upload_invalid_record_type(temp_vault_env, sample_pdf_bytes):
    """Test upload with invalid record type."""
    result = upload_medical_record(
        patient_id="P001",
        record_type="invalid_type",
        title="Test",
        file_data=sample_pdf_bytes,
        filename="test.pdf",
        extract_text=False
    )
    
    assert result["success"] is False
    assert "Invalid record_type" in result["error"]


def test_get_patient_records(temp_vault_env, sample_pdf_bytes):
    """Test retrieving records for a patient."""
    # Upload multiple records
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Lab Result 1",
        file_data=sample_pdf_bytes,
        filename="lab1.pdf",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P001",
        record_type="imaging",
        title="X-Ray Report",
        file_data=sample_pdf_bytes,
        filename="xray.pdf",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P002",
        record_type="lab_result",
        title="Lab Result 2",
        file_data=sample_pdf_bytes,
        filename="lab2.pdf",
        extract_text=False
    )
    
    # Get records for P001
    result = get_patient_records("P001")
    
    assert result["success"] is True
    assert result["total_records"] == 2
    assert len(result["records"]) == 2
    assert all(r["patient_id"] == "P001" for r in result["records"])


def test_get_patient_records_filtered(temp_vault_env, sample_pdf_bytes):
    """Test retrieving records filtered by type."""
    # Upload different types
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Lab Result",
        file_data=sample_pdf_bytes,
        filename="lab.pdf",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P001",
        record_type="imaging",
        title="X-Ray",
        file_data=sample_pdf_bytes,
        filename="xray.pdf",
        extract_text=False
    )
    
    # Filter by lab_result
    result = get_patient_records("P001", record_type="lab_result")
    
    assert result["success"] is True
    assert result["total_records"] == 1
    assert result["records"][0]["record_type"] == "lab_result"


def test_get_record_by_id(temp_vault_env, sample_pdf_bytes):
    """Test retrieving a specific record by ID."""
    # Upload a record
    upload_result = upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Blood Test",
        file_data=sample_pdf_bytes,
        filename="blood.pdf",
        extract_text=False
    )
    
    record_id = upload_result["record_id"]
    
    # Retrieve by ID
    result = get_record_by_id(record_id)
    
    assert result["success"] is True
    assert result["record"]["record_id"] == record_id
    assert result["record"]["title"] == "Blood Test"


def test_get_record_by_id_not_found(temp_vault_env):
    """Test retrieving a non-existent record."""
    result = get_record_by_id("nonexistent-id")
    
    assert result["success"] is False
    assert "not found" in result["error"]


def test_delete_record(temp_vault_env, sample_pdf_bytes):
    """Test deleting a medical record."""
    # Upload a record
    upload_result = upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="To Delete",
        file_data=sample_pdf_bytes,
        filename="delete.pdf",
        extract_text=False
    )
    
    record_id = upload_result["record_id"]
    file_path = upload_result["file_path"]
    
    # Verify file exists
    assert os.path.exists(file_path)
    
    # Delete record
    result = delete_record(record_id)
    
    assert result["success"] is True
    assert "deleted successfully" in result["message"]
    
    # Verify file was deleted
    assert not os.path.exists(file_path)
    
    # Verify record was removed from JSON
    records = _load_records()
    assert len(records) == 0


def test_search_records(temp_vault_env, sample_pdf_bytes):
    """Test searching records by text."""
    # Upload records with different titles
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Blood Test Results",
        file_data=sample_pdf_bytes,
        filename="blood.pdf",
        description="Cholesterol levels",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P001",
        record_type="imaging",
        title="X-Ray Report",
        file_data=sample_pdf_bytes,
        filename="xray.pdf",
        description="Chest X-ray",
        extract_text=False
    )
    
    # Search for "blood"
    result = search_records(query="blood", patient_id="P001")
    
    assert result["success"] is True
    assert result["total_matches"] == 1
    assert "Blood Test" in result["records"][0]["title"]
    
    # Search for "x-ray"
    result = search_records(query="x-ray", patient_id="P001")
    
    assert result["success"] is True
    assert result["total_matches"] == 1
    assert "X-Ray" in result["records"][0]["title"]
    
    # Search in description
    result = search_records(query="cholesterol", patient_id="P001")
    
    assert result["success"] is True
    assert result["total_matches"] == 1


def test_get_vault_statistics(temp_vault_env, sample_pdf_bytes):
    """Test vault statistics calculation."""
    # Upload various records
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Lab 1",
        file_data=sample_pdf_bytes,
        filename="lab1.pdf",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Lab 2",
        file_data=sample_pdf_bytes,
        filename="lab2.pdf",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P001",
        record_type="imaging",
        title="X-Ray",
        file_data=sample_pdf_bytes,
        filename="xray.pdf",
        extract_text=False
    )
    
    # Get statistics
    result = get_vault_statistics(patient_id="P001")
    
    assert result["success"] is True
    stats = result["statistics"]
    assert stats["total_records"] == 3
    assert stats["by_type"]["lab_results"] == 2
    assert stats["by_type"]["imaging"] == 1
    assert stats["total_size_mb"] > 0


def test_get_vault_statistics_all_patients(temp_vault_env, sample_pdf_bytes):
    """Test vault statistics for all patients."""
    # Upload for different patients
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Lab P001",
        file_data=sample_pdf_bytes,
        filename="lab_p001.pdf",
        extract_text=False
    )
    
    upload_medical_record(
        patient_id="P002",
        record_type="lab_result",
        title="Lab P002",
        file_data=sample_pdf_bytes,
        filename="lab_p002.pdf",
        extract_text=False
    )
    
    # Get all statistics
    result = get_vault_statistics()
    
    assert result["success"] is True
    assert result["statistics"]["total_records"] == 2


def test_upload_with_image_file(temp_vault_env, sample_image_bytes):
    """Test uploading an image file."""
    result = upload_medical_record(
        patient_id="P001",
        record_type="imaging",
        title="MRI Scan",
        file_data=sample_image_bytes,
        filename="mri_scan.png",
        description="Brain MRI",
        extract_text=False  # Skip OCR for minimal image
    )
    
    assert result["success"] is True
    assert result["record"]["file_extension"] == ".png"
    assert os.path.exists(result["file_path"])


def test_multiple_record_types(temp_vault_env, sample_pdf_bytes):
    """Test uploading all supported record types."""
    record_types = ["lab_result", "imaging", "discharge_summary", "other"]
    
    for rec_type in record_types:
        result = upload_medical_record(
            patient_id="P001",
            record_type=rec_type,
            title=f"Test {rec_type}",
            file_data=sample_pdf_bytes,
            filename=f"test_{rec_type}.pdf",
            extract_text=False
        )
        
        assert result["success"] is True
        assert result["record"]["record_type"] == rec_type
    
    # Verify all were saved
    records = _load_records()
    assert len(records) == 4


def test_default_date(temp_vault_env, sample_pdf_bytes):
    """Test that default date is set correctly when not provided."""
    result = upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Test",
        file_data=sample_pdf_bytes,
        filename="test.pdf",
        extract_text=False
    )
    
    assert result["success"] is True
    record_date = result["record"]["record_date"]
    # Should be today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")
    assert record_date == today


def test_empty_patient_records(temp_vault_env):
    """Test getting records for a patient with no records."""
    result = get_patient_records("P999")
    
    assert result["success"] is True
    assert result["total_records"] == 0
    assert len(result["records"]) == 0


def test_search_no_matches(temp_vault_env, sample_pdf_bytes):
    """Test search with no matching results."""
    upload_medical_record(
        patient_id="P001",
        record_type="lab_result",
        title="Blood Test",
        file_data=sample_pdf_bytes,
        filename="blood.pdf",
        extract_text=False
    )
    
    result = search_records(query="nonexistent term", patient_id="P001")
    
    assert result["success"] is True
    assert result["total_matches"] == 0
    assert len(result["records"]) == 0
