"""
Medical Vault Tool — Upload, store, and OCR-extract medical records.
Supports lab results, imaging reports, discharge summaries, and other documents.
"""
import json
import os
import sys
import time
import uuid
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import io

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import log_tool_call


# ── Configuration ─────────────────────────────────────────────────────────────
UPLOADS_DIR = os.path.join(config.BASE_DIR, "uploads")
MEDICAL_RECORDS_FILE = os.path.join(config.DATA_DIR, "medical_records.json")

# Create upload directories
for subdir in ["lab_results", "imaging", "discharge_summaries", "other"]:
    os.makedirs(os.path.join(UPLOADS_DIR, subdir), exist_ok=True)

RECORD_TYPES = {
    "lab_result": "lab_results",
    "imaging": "imaging",
    "discharge_summary": "discharge_summaries",
    "other": "other"
}


# ── Helper Functions ──────────────────────────────────────────────────────────
def _load_records() -> List[Dict[str, Any]]:
    """Load medical records from JSON file."""
    if not os.path.exists(MEDICAL_RECORDS_FILE):
        return []
    with open(MEDICAL_RECORDS_FILE) as f:
        return json.load(f)


def _save_records(records: List[Dict[str, Any]]) -> None:
    """Save medical records to JSON file."""
    with open(MEDICAL_RECORDS_FILE, "w") as f:
        json.dump(records, f, indent=2)


def _extract_text_from_image(image_path: str) -> Optional[str]:
    """
    Extract text from an image using OCR (Tesseract).
    Returns extracted text or None if OCR is unavailable.
    """
    if not OCR_AVAILABLE:
        return None
    
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        return None


def _extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extract text from a PDF file.
    Returns extracted text or None if PDF extraction is unavailable.
    """
    if not PDF_AVAILABLE:
        return None
    
    try:
        text_parts = []
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return None


def _get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return Path(filename).suffix.lower()


def _is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}
    return _get_file_extension(filename) in image_extensions


def _is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF."""
    return _get_file_extension(filename) == '.pdf'


# ── Public API Functions ──────────────────────────────────────────────────────
def upload_medical_record(
    patient_id: str,
    record_type: str,
    title: str,
    file_data: Any,
    filename: str,
    description: Optional[str] = None,
    date_str: Optional[str] = None,
    doctor_name: Optional[str] = None,
    extract_text: bool = True
) -> Dict[str, Any]:
    """
    Upload a medical record file to the vault.
    
    Args:
        patient_id: Patient identifier
        record_type: Type of record (lab_result, imaging, discharge_summary, other)
        title: Title/name of the record
        file_data: File data (bytes or file-like object)
        filename: Original filename
        description: Optional description
        date_str: Record date (defaults to today)
        doctor_name: Doctor who ordered/created the record
        extract_text: Whether to attempt OCR/text extraction
    
    Returns:
        Dict with success status, record_id, and extracted text if available
    """
    start = time.time()
    
    try:
        # Validate record type
        if record_type not in RECORD_TYPES:
            raise ValueError(f"Invalid record_type. Must be one of: {list(RECORD_TYPES.keys())}")
        
        # Generate unique record ID
        record_id = str(uuid.uuid4())
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_date = date_str or datetime.now().strftime("%Y-%m-%d")
        
        # Determine file path
        subdir = RECORD_TYPES[record_type]
        file_ext = _get_file_extension(filename)
        safe_filename = f"{record_id}_{filename.replace(' ', '_')}"
        file_path = os.path.join(UPLOADS_DIR, subdir, safe_filename)
        
        # Save file
        if isinstance(file_data, bytes):
            with open(file_path, 'wb') as f:
                f.write(file_data)
        else:
            # Assume file-like object
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
        
        # Attempt text extraction
        extracted_text = None
        extraction_method = None
        
        if extract_text:
            if _is_image_file(filename):
                extracted_text = _extract_text_from_image(file_path)
                extraction_method = "OCR (Tesseract)" if extracted_text else None
            elif _is_pdf_file(filename):
                extracted_text = _extract_text_from_pdf(file_path)
                extraction_method = "PDF Text Extraction" if extracted_text else None
        
        # Create record metadata
        record = {
            "record_id": record_id,
            "patient_id": patient_id,
            "record_type": record_type,
            "title": title,
            "description": description or "",
            "filename": filename,
            "file_path": file_path,
            "file_size_bytes": os.path.getsize(file_path),
            "file_extension": file_ext,
            "upload_date": upload_date,
            "record_date": record_date,
            "doctor_name": doctor_name or "Not specified",
            "extracted_text": extracted_text,
            "extraction_method": extraction_method,
            "ocr_available": OCR_AVAILABLE,
            "pdf_extraction_available": PDF_AVAILABLE
        }
        
        # Save to records
        records = _load_records()
        records.append(record)
        _save_records(records)
        
        result = {
            "success": True,
            "message": f"Medical record '{title}' uploaded successfully.",
            "record_id": record_id,
            "file_path": file_path,
            "extracted_text": extracted_text,
            "extraction_method": extraction_method,
            "record": record
        }
        
        log_tool_call("upload_medical_record", patient_id, "uploaded", True,
                      duration_ms=(time.time() - start) * 1000,
                      patient_id=patient_id, record_id=record_id,
                      record_type=record_type)
        
        return result
        
    except Exception as e:
        log_tool_call("upload_medical_record", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}


def get_patient_records(
    patient_id: str,
    record_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve all medical records for a patient, optionally filtered by type.
    
    Args:
        patient_id: Patient identifier
        record_type: Optional filter by record type
    
    Returns:
        Dict with success status and list of records
    """
    start = time.time()
    
    try:
        records = _load_records()
        
        # Filter by patient
        patient_records = [r for r in records if r["patient_id"] == patient_id]
        
        # Filter by type if specified
        if record_type:
            if record_type not in RECORD_TYPES:
                raise ValueError(f"Invalid record_type: {record_type}")
            patient_records = [r for r in patient_records if r["record_type"] == record_type]
        
        # Sort by upload date (most recent first)
        patient_records.sort(key=lambda x: x["upload_date"], reverse=True)
        
        result = {
            "success": True,
            "patient_id": patient_id,
            "record_type_filter": record_type,
            "total_records": len(patient_records),
            "records": patient_records
        }
        
        log_tool_call("get_patient_records", patient_id, f"found {len(patient_records)} records",
                      True, duration_ms=(time.time() - start) * 1000,
                      patient_id=patient_id, record_count=len(patient_records))
        
        return result
        
    except Exception as e:
        log_tool_call("get_patient_records", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}


def get_record_by_id(record_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific medical record by ID.
    
    Args:
        record_id: Record identifier
    
    Returns:
        Dict with success status and record details
    """
    start = time.time()
    
    try:
        records = _load_records()
        record = next((r for r in records if r["record_id"] == record_id), None)
        
        if not record:
            raise ValueError(f"Record {record_id} not found.")
        
        result = {
            "success": True,
            "record": record
        }
        
        log_tool_call("get_record_by_id", record_id, "found", True,
                      duration_ms=(time.time() - start) * 1000,
                      record_id=record_id)
        
        return result
        
    except Exception as e:
        log_tool_call("get_record_by_id", record_id, str(e), False,
                      error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}


def delete_record(record_id: str) -> Dict[str, Any]:
    """
    Delete a medical record and its associated file.
    
    Args:
        record_id: Record identifier
    
    Returns:
        Dict with success status and deletion confirmation
    """
    start = time.time()
    
    try:
        records = _load_records()
        record = next((r for r in records if r["record_id"] == record_id), None)
        
        if not record:
            raise ValueError(f"Record {record_id} not found.")
        
        # Delete file if it exists
        if os.path.exists(record["file_path"]):
            os.remove(record["file_path"])
        
        # Remove from records
        records = [r for r in records if r["record_id"] != record_id]
        _save_records(records)
        
        result = {
            "success": True,
            "message": f"Record '{record['title']}' deleted successfully.",
            "deleted_record": record
        }
        
        log_tool_call("delete_record", record_id, "deleted", True,
                      duration_ms=(time.time() - start) * 1000,
                      record_id=record_id)
        
        return result
        
    except Exception as e:
        log_tool_call("delete_record", record_id, str(e), False,
                      error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}


def search_records(
    query: str,
    patient_id: Optional[str] = None,
    record_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search medical records by text (title, description, extracted text).
    
    Args:
        query: Search query string
        patient_id: Optional filter by patient
        record_type: Optional filter by record type
    
    Returns:
        Dict with success status and matching records
    """
    start = time.time()
    
    try:
        records = _load_records()
        query_lower = query.lower()
        
        # Filter records
        matches = []
        for record in records:
            # Apply filters
            if patient_id and record["patient_id"] != patient_id:
                continue
            if record_type and record["record_type"] != record_type:
                continue
            
            # Search in text fields
            searchable_text = " ".join([
                record.get("title", ""),
                record.get("description", ""),
                record.get("extracted_text", "") or "",
                record.get("doctor_name", "")
            ]).lower()
            
            if query_lower in searchable_text:
                matches.append(record)
        
        # Sort by upload date (most recent first)
        matches.sort(key=lambda x: x["upload_date"], reverse=True)
        
        result = {
            "success": True,
            "query": query,
            "patient_id_filter": patient_id,
            "record_type_filter": record_type,
            "total_matches": len(matches),
            "records": matches
        }
        
        log_tool_call("search_records", query, f"found {len(matches)} matches",
                      True, duration_ms=(time.time() - start) * 1000,
                      query=query, match_count=len(matches))
        
        return result
        
    except Exception as e:
        log_tool_call("search_records", query, str(e), False,
                      error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}


def get_vault_statistics(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics about medical records in the vault.
    
    Args:
        patient_id: Optional filter by patient
    
    Returns:
        Dict with vault statistics
    """
    start = time.time()
    
    try:
        records = _load_records()
        
        # Filter by patient if specified
        if patient_id:
            records = [r for r in records if r["patient_id"] == patient_id]
        
        # Calculate statistics
        stats = {
            "total_records": len(records),
            "by_type": {
                "lab_results": len([r for r in records if r["record_type"] == "lab_result"]),
                "imaging": len([r for r in records if r["record_type"] == "imaging"]),
                "discharge_summaries": len([r for r in records if r["record_type"] == "discharge_summary"]),
                "other": len([r for r in records if r["record_type"] == "other"])
            },
            "total_size_mb": sum(r.get("file_size_bytes", 0) for r in records) / (1024 * 1024),
            "records_with_ocr": len([r for r in records if r.get("extracted_text")]),
            "ocr_success_rate": 0.0
        }
        
        if stats["total_records"] > 0:
            stats["ocr_success_rate"] = (stats["records_with_ocr"] / stats["total_records"]) * 100
        
        result = {
            "success": True,
            "patient_id_filter": patient_id,
            "statistics": stats
        }
        
        log_tool_call("get_vault_statistics", patient_id or "all", "calculated",
                      True, duration_ms=(time.time() - start) * 1000)
        
        return result
        
    except Exception as e:
        log_tool_call("get_vault_statistics", patient_id or "all", str(e),
                      False, error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}


def reprocess_ocr(record_id: str) -> Dict[str, Any]:
    """
    Re-run OCR extraction on an existing record.
    
    Args:
        record_id: Record identifier
    
    Returns:
        Dict with success status and new extracted text
    """
    start = time.time()
    
    try:
        records = _load_records()
        record_idx = next((i for i, r in enumerate(records) if r["record_id"] == record_id), None)
        
        if record_idx is None:
            raise ValueError(f"Record {record_id} not found.")
        
        record = records[record_idx]
        file_path = record["file_path"]
        
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        # Attempt text extraction
        extracted_text = None
        extraction_method = None
        
        if _is_image_file(record["filename"]):
            extracted_text = _extract_text_from_image(file_path)
            extraction_method = "OCR (Tesseract)" if extracted_text else None
        elif _is_pdf_file(record["filename"]):
            extracted_text = _extract_text_from_pdf(file_path)
            extraction_method = "PDF Text Extraction" if extracted_text else None
        
        # Update record
        record["extracted_text"] = extracted_text
        record["extraction_method"] = extraction_method
        record["last_ocr_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        records[record_idx] = record
        _save_records(records)
        
        result = {
            "success": True,
            "message": f"OCR reprocessed for record '{record['title']}'.",
            "record_id": record_id,
            "extracted_text": extracted_text,
            "extraction_method": extraction_method
        }
        
        log_tool_call("reprocess_ocr", record_id, "reprocessed", True,
                      duration_ms=(time.time() - start) * 1000,
                      record_id=record_id)
        
        return result
        
    except Exception as e:
        log_tool_call("reprocess_ocr", record_id, str(e), False,
                      error=str(e), duration_ms=(time.time() - start) * 1000)
        return {"success": False, "error": str(e)}
