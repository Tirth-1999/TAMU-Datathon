"""
File upload router
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List
import uuid
import shutil
from pathlib import Path
import os
import json

from app.models.schemas import UploadResponse, DocumentMetadata
from app.services.document_processor import DocumentProcessor

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Metadata directory for tracking original filenames
METADATA_DIR = Path("uploads/.metadata")
METADATA_DIR.mkdir(exist_ok=True)

processor = DocumentProcessor()


@router.post("/", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a single document for classification
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in processor.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_ext}. Supported: {', '.join(processor.SUPPORTED_FORMATS)}"
            )

        # Generate unique document ID
        document_id = str(uuid.uuid4())

        # Save file
        file_path = UPLOAD_DIR / f"{document_id}{file_ext}"
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)
        
        # Save filename metadata mapping
        metadata_path = METADATA_DIR / f"{document_id}.json"
        with metadata_path.open("w") as f:
            json.dump({"original_filename": file.filename, "document_id": document_id}, f)

        # Pre-process to get metadata
        try:
            metadata, _, _ = processor.process_document(str(file_path))

            return UploadResponse(
                document_id=document_id,
                filename=file.filename,
                file_size=file_size,
                status="success",
                message="File uploaded and validated successfully",
                metadata=metadata
            )

        except ValueError as e:
            # Clean up file if processing fails
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/batch", response_model=List[UploadResponse])
async def upload_batch(files: List[UploadFile] = File(...)):
    """
    Upload multiple documents for batch processing
    """
    results = []

    for file in files:
        try:
            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in processor.SUPPORTED_FORMATS:
                results.append(UploadResponse(
                    document_id="",
                    filename=file.filename,
                    file_size=0,
                    status="error",
                    message=f"Unsupported file format: {file_ext}",
                    metadata=None
                ))
                continue

            # Generate unique document ID
            document_id = str(uuid.uuid4())

            # Save file
            file_path = UPLOAD_DIR / f"{document_id}{file_ext}"
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_size = os.path.getsize(file_path)
            
            # Save filename metadata mapping
            metadata_path = METADATA_DIR / f"{document_id}.json"
            with metadata_path.open("w") as f:
                json.dump({"original_filename": file.filename, "document_id": document_id}, f)

            # Pre-process to get metadata
            try:
                metadata, _, _ = processor.process_document(str(file_path))

                results.append(UploadResponse(
                    document_id=document_id,
                    filename=file.filename,
                    file_size=file_size,
                    status="success",
                    message="File uploaded successfully",
                    metadata=metadata
                ))

            except ValueError as e:
                # Clean up file if processing fails
                if file_path.exists():
                    file_path.unlink()

                results.append(UploadResponse(
                    document_id="",
                    filename=file.filename,
                    file_size=file_size,
                    status="error",
                    message=str(e),
                    metadata=None
                ))

        except Exception as e:
            results.append(UploadResponse(
                document_id="",
                filename=file.filename,
                file_size=0,
                status="error",
                message=f"Upload failed: {str(e)}",
                metadata=None
            ))

    return results


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete an uploaded document
    """
    # Find and delete file
    deleted = False
    for file_path in UPLOAD_DIR.glob(f"{document_id}.*"):
        file_path.unlink()
        deleted = True

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"message": "Document deleted successfully", "document_id": document_id}


@router.get("/list")
async def list_uploads():
    """
    List all uploaded documents
    """
    documents = []

    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            # Extract document ID from filename
            document_id = file_path.stem

            documents.append({
                "document_id": document_id,
                "filename": file_path.name,
                "file_size": os.path.getsize(file_path),
                "uploaded_at": os.path.getctime(file_path)
            })

    return {"documents": documents, "count": len(documents)}
