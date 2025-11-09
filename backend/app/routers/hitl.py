"""
Human-in-the-Loop (HITL) feedback router
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from app.models.schemas import HITLFeedback, ClassificationResult, ClassificationCategory
from app.services.hitl_learner import HITLLearner
from app.services.learning_database import learning_db

router = APIRouter()

RESULTS_DIR = Path("results")
FEEDBACK_DIR = Path("results/feedback")
FEEDBACK_DIR.mkdir(exist_ok=True, parents=True)

# Initialize HITL Learner
PROMPT_LIBRARY_PATH = Path("app/prompts/prompt_library.json")
hitl_learner = HITLLearner(FEEDBACK_DIR, PROMPT_LIBRARY_PATH)


@router.get("/queue")
async def get_review_queue():
    """
    Get all documents that require human review
    """
    review_queue = []

    for result_file in RESULTS_DIR.glob("*.json"):
        if result_file.parent.name == "feedback":
            continue

        try:
            with result_file.open('r') as f:
                result_data = json.load(f)

            if result_data.get("requires_review", False):
                review_queue.append({
                    "document_id": result_data["document_id"],
                    "filename": result_data["filename"],
                    "classification": result_data["classification"],
                    "confidence": result_data["confidence"],
                    "review_reason": result_data.get("review_reason"),
                    "safety_check": result_data.get("safety_check", {}),
                    "submitted_at": result_file.stat().st_ctime
                })

        except Exception as e:
            print(f"Error loading result {result_file}: {str(e)}")

    # Sort by confidence (lowest first) and safety concerns
    review_queue.sort(key=lambda x: (
        not x["safety_check"].get("is_safe", True),  # Unsafe first
        x["confidence"]  # Then by lowest confidence
    ))

    return {
        "queue": review_queue,
        "count": len(review_queue),
        "unsafe_count": sum(1 for item in review_queue if not item["safety_check"].get("is_safe", True))
    }


@router.post("/feedback")
async def submit_feedback(feedback: HITLFeedback):
    """
    Submit human feedback on a classification with enhanced context for learning
    """
    try:
        # Load original result
        result_path = RESULTS_DIR / f"{feedback.document_id}.json"

        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Classification result not found")

        with result_path.open('r') as f:
            result_data = json.load(f)

        # **NEW: Build enhanced context for learning**
        if not feedback.document_context:
            # Extract context from result data
            feedback.document_context = {
                "filename": result_data.get("filename"),
                "page_count": result_data.get("page_count"),
                "image_count": result_data.get("image_count"),
                "summary": result_data.get("summary"),
                "original_classification": result_data.get("classification"),
                "confidence": result_data.get("confidence"),
                "key_evidence": [
                    {
                        "quote": e.get("quote", "")[:200],
                        "reasoning": e.get("reasoning", "")
                    }
                    for e in result_data.get("evidence", [])[:3]
                ],
                "text_segments_summary": {
                    "total": len(result_data.get("text_segments", [])),
                    "classifications": {}
                },
                "keywords": result_data.get("all_keywords", [])[:20]
            }
            
            # Count segment classifications
            for seg in result_data.get("text_segments", []):
                seg_class = seg.get("classification", "Unknown")
                feedback.document_context["text_segments_summary"]["classifications"][seg_class] = \
                    feedback.document_context["text_segments_summary"]["classifications"].get(seg_class, 0) + 1
        
        # **NEW: Store original classification in feedback**
        if not feedback.original_classification:
            feedback.original_classification = result_data.get("classification")
        
        # **NEW: Generate learning instruction if not provided**
        if not feedback.learning_instruction and feedback.corrected_classification:
            feedback.learning_instruction = _generate_learning_instruction(
                feedback,
                result_data
            )
        
        # **NEW: Extract key indicators if not provided**
        if not feedback.key_indicators and feedback.corrected_classification:
            feedback.key_indicators = _extract_key_indicators(result_data)
        
        # Update result with feedback
        result_data["requires_review"] = False
        result_data["human_reviewed"] = True
        result_data["reviewed_by"] = feedback.reviewer_id
        result_data["reviewed_at"] = feedback.timestamp
        result_data["feedback_approved"] = feedback.approved

        if feedback.corrected_classification:
            result_data["original_classification"] = result_data["classification"]
            result_data["classification"] = feedback.corrected_classification
            result_data["human_corrected"] = True

        # Save updated result
        with result_path.open('w') as f:
            json.dump(result_data, f, indent=2, default=str)

        # **CRITICAL: Save to PERMANENT learning database (never deleted)**
        learning_db.add_learning_entry(feedback)
        
        # Save enhanced feedback for training data (archival copy)
        feedback_path = FEEDBACK_DIR / f"{feedback.document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with feedback_path.open('w') as f:
            json.dump(feedback.model_dump(mode='json'), f, indent=2, default=str)

        return {
            "message": "Feedback submitted successfully and saved to permanent learning database",
            "document_id": feedback.document_id,
            "approved": feedback.approved,
            "corrected": feedback.corrected_classification is not None,
            "learning_instruction": feedback.learning_instruction,
            "saved_to_permanent_db": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/feedback/{document_id}")
async def get_document_feedback(document_id: str):
    """
    Get all feedback for a specific document
    """
    feedback_list = []

    for feedback_file in FEEDBACK_DIR.glob(f"{document_id}_*.json"):
        try:
            with feedback_file.open('r') as f:
                feedback_data = json.load(f)
                feedback_list.append(feedback_data)
        except Exception as e:
            print(f"Error loading feedback {feedback_file}: {str(e)}")

    if not feedback_list:
        raise HTTPException(status_code=404, detail="No feedback found for this document")

    return {
        "document_id": document_id,
        "feedback": feedback_list,
        "count": len(feedback_list)
    }


@router.get("/feedback/all")
async def get_all_feedback():
    """
    Get all feedback for analytics and model improvement
    """
    all_feedback = []

    for feedback_file in FEEDBACK_DIR.glob("*.json"):
        try:
            with feedback_file.open('r') as f:
                feedback_data = json.load(f)
                all_feedback.append(feedback_data)
        except Exception as e:
            print(f"Error loading feedback {feedback_file}: {str(e)}")

    # Calculate statistics
    total = len(all_feedback)
    approved = sum(1 for f in all_feedback if f.get("approved", False))
    corrected = sum(1 for f in all_feedback if f.get("corrected_classification"))

    correction_stats = {}
    for f in all_feedback:
        if f.get("corrected_classification"):
            orig = f.get("original_classification", "Unknown")
            corr = f.get("corrected_classification")
            key = f"{orig} -> {corr}"
            correction_stats[key] = correction_stats.get(key, 0) + 1

    return {
        "feedback": all_feedback,
        "statistics": {
            "total_reviews": total,
            "approved": approved,
            "corrected": corrected,
            "approval_rate": approved / total if total > 0 else 0,
            "correction_rate": corrected / total if total > 0 else 0,
            "correction_patterns": correction_stats
        }
    }


@router.post("/approve/{document_id}")
async def quick_approve(document_id: str, reviewer_id: str = "system"):
    """
    Quick approve a document (no corrections needed)
    """
    feedback = HITLFeedback(
        document_id=document_id,
        reviewer_id=reviewer_id,
        approved=True,
        corrected_classification=None,
        feedback_notes="Quick approval - classification correct",
        timestamp=datetime.now().isoformat()
    )

    return await submit_feedback(feedback)


@router.post("/reject/{document_id}")
async def quick_reject(
    document_id: str,
    corrected_classification: ClassificationCategory,
    reviewer_id: str = "system",
    notes: str = ""
):
    """
    Quick reject and reclassify a document
    """
    feedback = HITLFeedback(
        document_id=document_id,
        reviewer_id=reviewer_id,
        approved=False,
        corrected_classification=corrected_classification,
        feedback_notes=notes or f"Reclassified to {corrected_classification}",
        timestamp=datetime.now().isoformat()
    )

    return await submit_feedback(feedback)


@router.get("/stats")
async def get_review_stats():
    """
    Get HITL review statistics
    """
    total_results = len(list(RESULTS_DIR.glob("*.json")))
    total_feedback = len(list(FEEDBACK_DIR.glob("*.json")))

    review_queue_count = 0
    for result_file in RESULTS_DIR.glob("*.json"):
        try:
            with result_file.open('r') as f:
                result_data = json.load(f)
                if result_data.get("requires_review", False):
                    review_queue_count += 1
        except:
            pass

    return {
        "total_classifications": total_results,
        "total_reviews": total_feedback,
        "pending_reviews": review_queue_count,
        "review_rate": total_feedback / total_results if total_results > 0 else 0,
        "pending_rate": review_queue_count / total_results if total_results > 0 else 0
    }


@router.get("/learning/stats")
async def get_learning_stats():
    """
    Get HITL learning system statistics - shows how the system learns from feedback
    """
    try:
        stats = hitl_learner.get_learning_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning stats: {str(e)}")


@router.get("/learning/patterns")
async def get_learned_patterns():
    """
    Get detailed learned patterns from human feedback
    """
    try:
        patterns = hitl_learner.analyze_corrections()
        return {
            "success": True,
            "patterns": patterns
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze patterns: {str(e)}")


@router.get("/learning/examples/{category}")
async def get_few_shot_examples(category: str):
    """
    Get few-shot learning examples for a specific category
    """
    try:
        examples = hitl_learner.get_few_shot_examples(category, limit=5)
        return {
            "success": True,
            "category": category,
            "examples": examples,
            "count": len(examples)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get examples: {str(e)}")


def _generate_learning_instruction(feedback: HITLFeedback, result_data: Dict[str, Any]) -> str:
    """
    Generate a clear learning instruction for the model based on the correction
    """
    orig = feedback.original_classification or result_data.get("classification", "Unknown")
    corrected = feedback.corrected_classification
    filename = result_data.get("filename", "document")
    
    # Extract key context
    has_aircraft_reg = any("N1234" in str(kw) or "N5678" in str(kw) for kw in result_data.get("all_keywords", []))
    has_company_info = any("company" in str(seg.get("text", "")).lower() for seg in result_data.get("text_segments", []))
    segment_counts = {}
    for seg in result_data.get("text_segments", []):
        seg_class = seg.get("classification", "Unknown")
        segment_counts[seg_class] = segment_counts.get(seg_class, 0) + 1
    
    instruction = f"""
LEARNING INSTRUCTION:
When you see documents similar to '{filename}':

ORIGINAL MISTAKE: Classified as '{orig}' but should be '{corrected}'

KEY LESSON: {feedback.feedback_notes}

WHAT TO LOOK FOR:
"""
    
    if has_aircraft_reg:
        instruction += "\n- Aircraft registration numbers (N-numbers) indicate internal aviation documents → Confidential"
    
    if has_company_info:
        instruction += "\n- Company/organization names in document headers → Likely Confidential internal docs"
    
    if segment_counts.get("Confidential", 0) >= 2:
        instruction += f"\n- Multiple segments classified as Confidential ({segment_counts.get('Confidential', 0)} found) → Overall doc is Confidential"
    
    if "manual" in filename.lower() or "operations" in filename.lower():
        instruction += "\n- Operations manuals, flight manuals, procedures → Usually Confidential unless public FAA docs"
    
    instruction += f"""

CORRECT CLASSIFICATION RULE:
Documents like this with {segment_counts.get('Confidential', 0)} confidential segments containing 
internal company information, procedures, or registration numbers should be classified as '{corrected}', 
not '{orig}'.

APPLY THIS: When you see similar patterns (company docs, N-numbers, internal procedures), 
classify as '{corrected}' with high confidence.
"""
    
    return instruction.strip()


def _extract_key_indicators(result_data: Dict[str, Any]) -> List[str]:
    """
    Extract key indicators that should trigger a specific classification
    """
    indicators = []
    
    # Get keywords
    keywords = result_data.get("all_keywords", [])[:15]
    indicators.extend(keywords)
    
    # Get confidential segment triggers
    for seg in result_data.get("text_segments", []):
        if seg.get("classification") == "Confidential":
            seg_keywords = seg.get("keywords", [])
            indicators.extend(seg_keywords)
    
    # Remove duplicates and limit
    indicators = list(set(indicators))[:20]
    
    return indicators


# **NEW ENDPOINTS: Permanent Learning Database Access**

@router.get("/learning/database")
async def get_learning_database():
    """
    Get all entries from the permanent learning database
    This database is NEVER cleared when classification cards are deleted
    """
    try:
        entries = learning_db.get_all_learning_entries()
        stats = learning_db.get_statistics()
        
        return {
            "learning_entries": entries,
            "statistics": stats,
            "total_count": len(entries),
            "message": "Permanent learning database - never deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load learning database: {str(e)}")


@router.get("/learning/statistics")
async def get_learning_statistics():
    """
    Get statistics about the permanent learning database
    """
    try:
        stats = learning_db.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/learning/recent/{limit}")
async def get_recent_learning(limit: int = 10):
    """
    Get the most recent learning entries
    """
    try:
        recent = learning_db.get_recent_learning(limit)
        return {
            "recent_learning": recent,
            "count": len(recent)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent learning: {str(e)}")


@router.get("/learning/classification/{classification}")
async def get_learning_by_classification(classification: str):
    """
    Get all learning entries for a specific classification
    """
    try:
        entries = learning_db.get_learning_by_classification(classification)
        return {
            "classification": classification,
            "learning_entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning by classification: {str(e)}")


@router.get("/learning/export")
async def export_learning_for_training():
    """
    Export learning data in format suitable for few-shot learning
    """
    try:
        training_data = learning_db.export_for_training()
        return {
            "training_examples": training_data,
            "count": len(training_data),
            "message": "Learning data exported for few-shot training"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export learning data: {str(e)}")
