import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Document, Business
from backend.app.schemas.schemas import DocumentOut, DocumentAnalysisRequest
from backend.app.auth.deps import get_current_business
from backend.app.services.document_processor import process_uploaded_document
from backend.app.services.workflow_engine import run_document_workflow
from backend.app.services.activity_service import log_activity
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("", response_model=List[DocumentOut])
def get_documents(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    docs = db.query(Document).filter(
        Document.business_id == business.id
    ).order_by(desc(Document.created_at)).all()
    return docs


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    auto_analyze: bool = Form(True),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    # Validate extension
    filename = file.filename or "uploaded_doc"
    ext = os.path.splitext(filename)[1].lower()
    allowed = [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".doc", ".txt"]
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Please upload a PDF, PNG, JPG, or DOCX document."
        )

    # Save to disk
    import time
    import uuid
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_prefix = f"{business.id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    saved_filename = f"{safe_prefix}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Error saving upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")

    # Process extraction
    proc_result = process_uploaded_document(file_path)

    doc = Document(
        business_id=business.id,
        file_name=filename,
        file_path=file_path,
        file_type=ext.lstrip("."),
        file_size=proc_result.get("file_size", 0),
        document_type="invoice",
        processing_status="processing" if auto_analyze else "pending",
        ocr_text=proc_result.get("raw_text", "")
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Document Uploaded",
        description=f"Uploaded file '{filename}' ({doc.file_size} bytes).",
        metadata={"document_id": doc.id, "file_name": filename}
    )

    # Auto run AI workflow if requested
    if auto_analyze:
        try:
            workflow_res = run_document_workflow(db, business, doc)
            db.refresh(doc)
        except Exception as e:
            logger.error(f"AI Workflow error: {e}")
            doc.processing_status = "failed"
            db.commit()

    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.business_id == business.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/{document_id}/analyze")
def analyze_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.business_id == business.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = run_document_workflow(db, business, doc)
    return {
        "message": "Document analyzed and workflow actions generated successfully.",
        "data": result
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.business_id == business.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove local file if exists
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    return {"message": "Document removed successfully"}
