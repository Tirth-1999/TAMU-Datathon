"""
Classification router
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Optional, List, AsyncGenerator
from pathlib import Path
import json
import os
from datetime import datetime
import asyncio
import queue
import time

from app.models.schemas import ClassificationResult, BatchProcessRequest, BatchProcessStatus
from app.services.document_processor import DocumentProcessor
from app.services.classifier import DocumentClassifier
from pydantic import BaseModel

router = APIRouter()

UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
METADATA_DIR = Path("uploads/.metadata")

# Initialize services (API key from environment)
processor = DocumentProcessor()

# Global classifier instance (will be initialized when API key is available)
_classifier: Optional[DocumentClassifier] = None

# Progress tracking for real-time updates - using thread-safe Queue
progress_queues: Dict[str, queue.Queue] = {}


def get_classifier() -> DocumentClassifier:
    """Get or create classifier instance"""
    global _classifier
    if _classifier is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY not configured. Please set it in your environment."
            )
        _classifier = DocumentClassifier(api_key)
    return _classifier


class ClassifyRequest(BaseModel):
    """Request to classify a document"""
    document_id: str
    enable_dual_verification: bool = False


@router.get("/progress/{document_id}")
async def stream_classification_progress(document_id: str):
    """
    Server-Sent Events endpoint for real-time classification progress updates
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        # Create a queue for this document if it doesn't exist
        if document_id not in progress_queues:
            progress_queues[document_id] = queue.Queue()
            print(f"[SSE] Created queue for document: {document_id}")
        
        msg_queue = progress_queues[document_id]

        print(f"📡 SSE connected for document: {document_id}")
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"

        try:
            last_keepalive = time.time()

            while True:
                # Try to get message from queue (non-blocking with timeout)
                try:
                    message = msg_queue.get(timeout=0.1)

                    print(f"[SSE] Sending SSE message: {message[:50]}...")

                    # Send the progress update as SSE
                    if message == "DONE":
                        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                        print(f"[COMPLETE] Classification complete for {document_id}")
                        break
                    elif message == "ERROR":
                        yield f"data: {json.dumps({'type': 'error'})}\n\n"
                        print(f"[ERROR] Classification error for {document_id}")
                        break
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'message': message})}\n\n"
                        # Small delay to ensure messages are sent separately
                        await asyncio.sleep(0.05)

                except queue.Empty:
                    # Send keepalive every 15 seconds
                    if time.time() - last_keepalive > 15:
                        yield f": keepalive\n\n"
                        last_keepalive = time.time()

                    # Small sleep to prevent busy-waiting
                    await asyncio.sleep(0.1)

        finally:
            # Clean up the queue when client disconnects
            if document_id in progress_queues:
                del progress_queues[document_id]
            print(f"🔌 SSE disconnected for document: {document_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )


@router.post("/", response_model=ClassificationResult)
async def classify_document(request: ClassifyRequest):
    """
    Classify an uploaded document with enhanced granular analysis
    """
    try:
        classifier = get_classifier()

        # Create SYNCHRONOUS progress callback for real-time updates
        def progress_callback(message: str):
            """Send progress update to SSE stream (synchronous, thread-safe)"""
            if request.document_id in progress_queues:
                progress_queues[request.document_id].put(message)
                print(f"[PROGRESS] {message}")
            else:
                print(f"[PROGRESS-NO-QUEUE] {message}")

        # Use existing progress queue or create one if doesn't exist
        # (SSE endpoint should have already created it)
        if request.document_id not in progress_queues:
            progress_queues[request.document_id] = queue.Queue()
            print(f"[CLASSIFY] Created queue for {request.document_id} (SSE might not be connected yet)")

        print(f"[START] Starting classification for {request.document_id}")

        # Send initial progress
        progress_callback("Starting document classification...")

        # Find document file
        progress_callback("Locating document...")
        file_path = None
        for path in UPLOAD_DIR.glob(f"{request.document_id}.*"):
            file_path = path
            break

        if not file_path or not file_path.exists():
            progress_callback("ERROR")
            raise HTTPException(status_code=404, detail="Document not found")

        # Load original filename from metadata
        original_filename = file_path.name  # Default to file_path name
        metadata_path = METADATA_DIR / f"{request.document_id}.json"
        if metadata_path.exists():
            with metadata_path.open('r') as f:
                file_metadata = json.load(f)
                original_filename = file_metadata.get("original_filename", file_path.name)

        # Process document
        progress_callback("Processing document pages...")
        metadata, text_pages, images_base64 = processor.process_document(str(file_path))
        
        # Override filename with original filename
        metadata.filename = original_filename

        # Get full text
        progress_callback("Extracting document text...")
        full_text = processor.extract_document_info(text_pages)

        # Extract page images for UI
        progress_callback("Extracting page images...")
        page_images = processor.extract_page_images(str(file_path))

        # Prepare content for Claude
        progress_callback("Preparing content for AI analysis...")
        content_blocks = processor.prepare_claude_content(text_pages, images_base64)

        # Use enhanced classification with SYNCHRONOUS callback
        progress_callback("Starting AI classification...")
        result = classifier.classify_document_enhanced(
            content_blocks=content_blocks,
            metadata=metadata,
            document_id=request.document_id,
            full_text=full_text,
            page_images=page_images,
            enable_dual_verification=request.enable_dual_verification,
            progress_callback=progress_callback  # Pass synchronous callback directly
        )

        # Save result
        progress_callback("Saving classification results...")
        result_path = RESULTS_DIR / f"{request.document_id}.json"
        with result_path.open('w') as f:
            json.dump(result.model_dump(mode='json'), f, indent=2, default=str)

        # Send completion signal
        progress_callback("DONE")
        print(f"[COMPLETE] Classification complete for {request.document_id}")

        return result

    except HTTPException:
        if request.document_id in progress_queues:
            progress_queues[request.document_id].put("ERROR")
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in classify_document: {str(e)}")
        print(f"Traceback: {error_details}")
        if request.document_id in progress_queues:
            progress_queues[request.document_id].put("ERROR")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.get("/{document_id}", response_model=ClassificationResult)
async def get_classification_result(document_id: str):
    """
    Retrieve classification result for a document
    """
    result_path = RESULTS_DIR / f"{document_id}.json"

    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Classification result not found")

    with result_path.open('r') as f:
        result_data = json.load(f)

    return ClassificationResult(**result_data)


@router.post("/batch", response_model=BatchProcessStatus)
async def classify_batch(request: BatchProcessRequest):
    """
    Classify multiple documents in batch
    """
    try:
        classifier = get_classifier()

        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = []
        processed = 0
        failed = 0

        for document_id in request.document_ids:
            try:
                # Find document file
                file_path = None
                for path in UPLOAD_DIR.glob(f"{document_id}.*"):
                    file_path = path
                    break

                if not file_path or not file_path.exists():
                    failed += 1
                    continue

                # Process document
                metadata, text_pages, images_base64 = processor.process_document(str(file_path))

                # Prepare content for Claude
                content_blocks = processor.prepare_claude_content(text_pages, images_base64)

                # Classify
                result = classifier.classify_document(
                    content_blocks=content_blocks,
                    metadata=metadata,
                    document_id=document_id,
                    enable_dual_verification=request.enable_dual_verification
                )

                # Auto-approve if confidence is high enough
                if result.confidence >= request.auto_approve_threshold and result.safety_check.is_safe:
                    result.requires_review = False

                results.append(result)

                # Save result
                result_path = RESULTS_DIR / f"{document_id}.json"
                with result_path.open('w') as f:
                    json.dump(result.model_dump(mode='json'), f, indent=2, default=str)

                processed += 1

            except Exception as e:
                failed += 1
                print(f"Failed to classify {document_id}: {str(e)}")

        return BatchProcessStatus(
            batch_id=batch_id,
            total_documents=len(request.document_ids),
            processed=processed,
            in_progress=0,
            failed=failed,
            completed=True,
            results=results
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.get("/results/all")
async def get_all_results():
    """
    Get all classification results
    """
    results = []

    for result_file in RESULTS_DIR.glob("*.json"):
        try:
            with result_file.open('r') as f:
                result_data = json.load(f)
                results.append(result_data)
        except Exception as e:
            print(f"Error loading result {result_file}: {str(e)}")

    return {
        "results": results,
        "count": len(results)
    }


@router.delete("/results/{document_id}")
async def delete_result(document_id: str):
    """
    Delete classification result and associated uploaded file
    **IMPORTANT: Human learning feedback is NEVER deleted - it's stored in permanent learning database**
    """
    result_path = RESULTS_DIR / f"{document_id}.json"
    
    # Delete result file
    result_deleted = False
    if result_path.exists():
        result_path.unlink()
        result_deleted = True

    # Delete uploaded file
    file_deleted = False
    for file_path in UPLOAD_DIR.glob(f"{document_id}.*"):
        file_path.unlink()
        file_deleted = True
    
    # **CRITICAL CHANGE: DO NOT DELETE FEEDBACK FILES**
    # Feedback is permanent learning data and should never be deleted
    # It's stored in the permanent learning database (results/learning_database.json)
    # The feedback files in results/feedback/ are archival copies that can stay for reference

    if not result_deleted and not file_deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "message": "Document and classification result deleted successfully. Human learning feedback preserved in permanent database.",
        "document_id": document_id,
        "result_deleted": result_deleted,
        "file_deleted": file_deleted,
        "learning_preserved": True
    }


@router.delete("/results/all/clear")
async def delete_all_results():
    """
    Delete all classification results and uploaded files
    **IMPORTANT: Human learning feedback is PRESERVED in permanent database and never deleted**
    """
    deleted_results = 0
    deleted_uploads = 0
    feedback_preserved = 0

    # Delete all result files
    for result_file in RESULTS_DIR.glob("*.json"):
        try:
            result_file.unlink()
            deleted_results += 1
        except Exception as e:
            print(f"Error deleting {result_file}: {str(e)}")

    # Delete all uploaded files
    for upload_file in UPLOAD_DIR.glob("*"):
        if upload_file.is_file():
            try:
                upload_file.unlink()
                deleted_uploads += 1
            except Exception as e:
                print(f"Error deleting {upload_file}: {str(e)}")

    # **CRITICAL: DO NOT DELETE FEEDBACK FILES OR LEARNING DATABASE**
    # Count feedback files (they are preserved as archival copies)
    feedback_dir = RESULTS_DIR / "feedback"
    if feedback_dir.exists():
        feedback_preserved = len(list(feedback_dir.glob("*.json")))

    return {
        "message": "All classification results and uploads cleared. Human learning feedback PRESERVED in permanent database.",
        "deleted_results": deleted_results,
        "deleted_uploads": deleted_uploads,
        "feedback_preserved": feedback_preserved,
        "learning_database_intact": True,
        "warning": "Classification results deleted but human learning is permanently preserved"
    }
