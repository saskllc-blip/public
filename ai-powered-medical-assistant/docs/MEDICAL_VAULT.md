# Medical Records Vault

The Medical Records Vault is a comprehensive document management system for healthcare records, featuring file upload, OCR text extraction, and secure storage capabilities.

## Features

### 📤 File Upload
- Support for multiple file formats:
  - **PDF**: Lab results, discharge summaries, reports
  - **Images**: PNG, JPG, JPEG, TIFF, BMP (imaging reports, scanned documents)
- Organized storage by record type:
  - 🧪 Lab Results
  - 🩻 Imaging Reports
  - 📋 Discharge Summaries
  - 📄 Other Documents

### 🔍 OCR Text Extraction
- Automatic text extraction from uploaded documents
- Uses **Tesseract OCR** for image files
- **PyPDF2** for PDF text extraction
- Extracted text is searchable and stored with the record
- Supports reprocessing if OCR fails initially

### 🗄️ Secure Storage
- Files stored in organized directory structure
- Unique record IDs (UUID) for each upload
- Metadata tracking:
  - Upload date/time
  - Record date
  - Doctor/lab name
  - File size and type
  - Extraction method used
- Patient-specific access control

### 📊 Vault Statistics
- Total records count
- Records by type breakdown
- Total storage usage (MB)
- OCR success rate
- Patient-specific or system-wide statistics

### 🔎 Search & Filter
- Full-text search across:
  - Record titles
  - Descriptions
  - Extracted text content
  - Doctor/lab names
- Filter by record type
- Filter by patient
- Sort by upload date (newest first)

## Usage

### Patient View Integration

The Medical Vault is integrated into the Patient View as a dedicated tab:

**Purdue_GenAI_Projects/Capstone/AI Powered Medical Assistant/pages/1_Patient_View.py**

Navigate to: **Patient View → Medical Vault** tab

### Uploading a Record

1. Select the patient from the dropdown
2. Go to the **Medical Vault** tab
3. Fill in the upload form:
   - **Record Type**: Choose from lab result, imaging, discharge summary, or other
   - **Title**: Descriptive name (e.g., "Blood Test - January 2024")
   - **Description**: Optional notes about the record
   - **Record Date**: Date the test/procedure was performed
   - **Doctor/Lab Name**: Who ordered or created the record
   - **File**: Upload PDF or image file
   - **Enable OCR**: Check to automatically extract text
4. Click **Upload to Vault**
5. View extraction results if OCR was successful

### Viewing Records

Records are organized in tabs by type:
- **All**: View all records
- **Lab Results**: Lab tests and pathology reports
- **Imaging**: X-rays, MRIs, CT scans, ultrasounds
- **Discharge Summaries**: Hospital discharge documents
- **Other**: Miscellaneous medical documents

Each record displays:
- Type icon and title
- Record date and upload date
- Doctor/lab name
- File information (name, size)
- Description (if provided)
- Extracted text (if available)

### Downloading Records

Click the **⬇️ Download** button next to any record to download the original file.

### Deleting Records

Click the **🗑️ Delete** button to permanently remove a record and its file.

### Searching Records

Use the search box in the Medical Vault tab to search across all record metadata and extracted text. Filter results by record type.

## API Reference

### `medical_vault_tool.py`

#### `upload_medical_record()`
```python
upload_medical_record(
    patient_id: str,
    record_type: str,
    title: str,
    file_data: Any,
    filename: str,
    description: Optional[str] = None,
    date_str: Optional[str] = None,
    doctor_name: Optional[str] = None,
    extract_text: bool = True
) -> Dict[str, Any]
```

Upload a new medical record with optional OCR extraction.

**Parameters:**
- `patient_id`: Patient identifier
- `record_type`: One of: `lab_result`, `imaging`, `discharge_summary`, `other`
- `title`: Record title/name
- `file_data`: File bytes or file-like object
- `filename`: Original filename with extension
- `description`: Optional description/notes
- `date_str`: Record date (defaults to today)
- `doctor_name`: Doctor or lab name
- `extract_text`: Whether to perform OCR/text extraction

**Returns:**
```python
{
    "success": True,
    "record_id": "uuid",
    "message": "Upload message",
    "file_path": "/path/to/file",
    "extracted_text": "...",
    "extraction_method": "OCR (Tesseract)" or "PDF Text Extraction",
    "record": {...}  # Full record metadata
}
```

#### `get_patient_records()`
```python
get_patient_records(
    patient_id: str,
    record_type: Optional[str] = None
) -> Dict[str, Any]
```

Retrieve all records for a patient, optionally filtered by type.

**Returns:**
```python
{
    "success": True,
    "patient_id": "P001",
    "total_records": 5,
    "records": [...]  # List of record objects
}
```

#### `get_record_by_id()`
```python
get_record_by_id(record_id: str) -> Dict[str, Any]
```

Retrieve a specific record by its UUID.

#### `delete_record()`
```python
delete_record(record_id: str) -> Dict[str, Any]
```

Delete a record and its associated file.

#### `search_records()`
```python
search_records(
    query: str,
    patient_id: Optional[str] = None,
    record_type: Optional[str] = None
) -> Dict[str, Any]
```

Search records by text across title, description, and extracted content.

#### `get_vault_statistics()`
```python
get_vault_statistics(patient_id: Optional[str] = None) -> Dict[str, Any]
```

Get statistics about vault usage.

**Returns:**
```python
{
    "success": True,
    "statistics": {
        "total_records": 10,
        "by_type": {
            "lab_results": 4,
            "imaging": 3,
            "discharge_summaries": 2,
            "other": 1
        },
        "total_size_mb": 15.4,
        "records_with_ocr": 8,
        "ocr_success_rate": 80.0
    }
}
```

#### `reprocess_ocr()`
```python
reprocess_ocr(record_id: str) -> Dict[str, Any]
```

Re-run OCR extraction on an existing record.

## Storage Structure

```
AI Powered Medical Assistant/
├── uploads/
│   ├── lab_results/
│   │   └── {uuid}_{filename}.pdf
│   ├── imaging/
│   │   └── {uuid}_{filename}.png
│   ├── discharge_summaries/
│   │   └── {uuid}_{filename}.pdf
│   └── other/
│       └── {uuid}_{filename}.pdf
└── data/
    └── medical_records.json
```

### Record Metadata Schema

```json
{
    "record_id": "uuid",
    "patient_id": "P001",
    "record_type": "lab_result",
    "title": "Blood Test - January 2024",
    "description": "Routine blood work",
    "filename": "blood_test.pdf",
    "file_path": "/path/to/uploads/lab_results/uuid_blood_test.pdf",
    "file_size_bytes": 102400,
    "file_extension": ".pdf",
    "upload_date": "2024-01-20 14:30:00",
    "record_date": "2024-01-15",
    "doctor_name": "Dr. Smith",
    "extracted_text": "Extracted content...",
    "extraction_method": "PDF Text Extraction",
    "ocr_available": true,
    "pdf_extraction_available": true
}
```

## Dependencies

### Required Python Packages

```txt
Pillow>=10.0.0          # Image processing
pytesseract>=0.3.10     # OCR engine wrapper
PyPDF2>=3.0.0           # PDF text extraction
```

### System Requirements

**Tesseract OCR** must be installed on the system:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

## Security Considerations

### Data Privacy
- Medical records contain sensitive patient information
- Files are stored locally in the `uploads/` directory
- The `uploads/` directory is excluded from git via `.gitignore`
- Access control is implemented at the patient selection level

### File Validation
- File types are validated by extension
- Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP
- Files are saved with UUID prefixes to prevent name collisions

### Storage Management
- Monitor disk space usage via vault statistics
- Implement retention policies as needed
- Regular backups of `uploads/` and `medical_records.json` recommended

## Testing

Run the test suite:

```bash
pytest tests/test_medical_vault.py -v
```

Tests cover:
- ✅ File upload (PDF and images)
- ✅ Record retrieval (all and filtered)
- ✅ Search functionality
- ✅ Deletion with file cleanup
- ✅ Statistics calculation
- ✅ Error handling
- ✅ Edge cases (empty results, invalid types)

## Future Enhancements

### Potential Features
- 🔒 Encryption at rest for sensitive files
- 🌐 Cloud storage integration (S3, Azure Blob)
- 📱 Mobile upload via QR code/camera
- 🤖 AI-powered document classification
- 📊 Advanced analytics (trend detection, anomaly alerts)
- 🔗 FHIR integration for interoperability
- 📧 Email integration for automated uploads
- 🔔 Notification system for new uploads
- 📝 Document versioning and history
- 👥 Multi-user access controls
- 🌍 Multi-language OCR support
- 📈 Visualization of lab trends over time

## Troubleshooting

### OCR Not Working

**Issue:** Uploaded images don't have extracted text

**Solutions:**
1. Verify Tesseract is installed:
   ```bash
   tesseract --version
   ```
2. Check image quality - OCR works best with:
   - High resolution (300+ DPI)
   - Clear, black text on white background
   - No rotation or skew
3. Try reprocessing with `reprocess_ocr(record_id)`

### PDF Text Extraction Fails

**Issue:** PDFs don't have extracted text

**Cause:** Some PDFs are image-based (scanned documents) and require OCR, not just text extraction.

**Solution:** Convert PDF pages to images and run OCR, or use a more advanced PDF library like `pdfplumber` or `pdf2image`.

### File Upload Errors

**Issue:** Upload fails with permission error

**Solution:** Ensure the `uploads/` directory has write permissions:
```bash
chmod -R 755 uploads/
```

### Large File Handling

**Issue:** Large files (>10MB) fail to upload

**Solution:** Configure Streamlit's file upload size limit:
```toml
# .streamlit/config.toml
[server]
maxUploadSize = 50  # MB
```

## Support

For issues, questions, or feature requests related to the Medical Vault:
- Check the test suite for usage examples
- Review the API reference for function signatures
- Consult the troubleshooting section for common issues

---

**Built with:** Python, Streamlit, Tesseract OCR, PyPDF2, Pillow
**License:** MIT (or as per project license)
**Version:** 1.0.0
