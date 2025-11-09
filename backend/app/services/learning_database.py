"""
Permanent Learning Database
Stores all human feedback permanently, never deleted even when classification cards are removed
"""
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.schemas import HITLFeedback


class LearningDatabase:
    """
    Centralized, permanent storage for human learning feedback
    This database is NEVER cleared when classification results are deleted
    """
    
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Initialize database if it doesn't exist
        if not self.database_path.exists():
            self._initialize_database()
    
    def _initialize_database(self):
        """Create empty learning database"""
        initial_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_feedback_count": 0,
            "learning_entries": []
        }
        with self.database_path.open('w') as f:
            json.dump(initial_data, f, indent=2)
    
    def add_learning_entry(self, feedback: HITLFeedback) -> bool:
        """
        Add a new learning entry to the permanent database
        Returns True if added, False if duplicate
        """
        try:
            data = self._load_database()
            
            # Check for duplicate (same document_id)
            existing_ids = {entry.get("document_id") for entry in data["learning_entries"]}
            if feedback.document_id in existing_ids:
                # Update existing entry instead of adding duplicate
                for i, entry in enumerate(data["learning_entries"]):
                    if entry.get("document_id") == feedback.document_id:
                        data["learning_entries"][i] = self._feedback_to_dict(feedback)
                        break
            else:
                # Add new entry
                data["learning_entries"].append(self._feedback_to_dict(feedback))
                data["total_feedback_count"] = len(data["learning_entries"])
            
            data["last_updated"] = datetime.now().isoformat()
            
            self._save_database(data)
            return True
            
        except Exception as e:
            print(f"Error adding learning entry: {e}")
            return False
    
    def get_all_learning_entries(self) -> List[Dict[str, Any]]:
        """Get all learning entries from the database"""
        try:
            data = self._load_database()
            return data.get("learning_entries", [])
        except Exception as e:
            print(f"Error loading learning entries: {e}")
            return []
    
    def get_learning_by_classification(self, classification: str) -> List[Dict[str, Any]]:
        """Get learning entries for a specific classification"""
        all_entries = self.get_all_learning_entries()
        return [
            entry for entry in all_entries
            if entry.get("corrected_classification") == classification
        ]
    
    def get_recent_learning(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent learning entries"""
        all_entries = self.get_all_learning_entries()
        # Sort by timestamp, most recent first
        sorted_entries = sorted(
            all_entries,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        return sorted_entries[:limit]
    
    def search_learning_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Search learning entries by keywords"""
        all_entries = self.get_all_learning_entries()
        matching_entries = []
        
        for entry in all_entries:
            # Check if any keyword appears in the entry
            entry_keywords = entry.get("key_indicators", [])
            entry_text = json.dumps(entry).lower()
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in entry_text or keyword_lower in [k.lower() for k in entry_keywords]:
                    matching_entries.append(entry)
                    break
        
        return matching_entries
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the learning database"""
        data = self._load_database()
        entries = data.get("learning_entries", [])
        
        # Count by classification
        classification_counts = {}
        for entry in entries:
            classification = entry.get("corrected_classification", "Unknown")
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
        
        # Count corrections (where approved=False)
        corrections_count = sum(1 for entry in entries if not entry.get("approved", True))
        
        return {
            "total_entries": len(entries),
            "corrections_count": corrections_count,
            "approvals_count": len(entries) - corrections_count,
            "classification_distribution": classification_counts,
            "database_version": data.get("version"),
            "created_at": data.get("created_at"),
            "last_updated": data.get("last_updated")
        }
    
    def export_for_training(self) -> List[Dict[str, Any]]:
        """
        Export learning entries in a format suitable for few-shot learning
        """
        entries = self.get_all_learning_entries()
        training_data = []
        
        for entry in entries:
            # Only include entries with corrections
            if not entry.get("approved", True):
                training_data.append({
                    "document_summary": entry.get("document_context", {}).get("summary", ""),
                    "keywords": entry.get("key_indicators", []),
                    "original_classification": entry.get("original_classification"),
                    "correct_classification": entry.get("corrected_classification"),
                    "learning_instruction": entry.get("learning_instruction", ""),
                    "reasoning": entry.get("reasoning_for_correction", "")
                })
        
        return training_data
    
    def _feedback_to_dict(self, feedback: HITLFeedback) -> Dict[str, Any]:
        """Convert HITLFeedback object to dictionary"""
        return {
            "document_id": feedback.document_id,
            "reviewer_id": feedback.reviewer_id,
            "approved": feedback.approved,
            "corrected_classification": feedback.corrected_classification,
            "original_classification": feedback.original_classification,
            "feedback_notes": feedback.feedback_notes,
            "timestamp": feedback.timestamp,
            "document_context": feedback.document_context,
            "reasoning_for_correction": feedback.reasoning_for_correction,
            "key_indicators": feedback.key_indicators,
            "similar_document_patterns": feedback.similar_document_patterns,
            "learning_instruction": feedback.learning_instruction
        }
    
    def _load_database(self) -> Dict[str, Any]:
        """Load database from file"""
        if not self.database_path.exists():
            self._initialize_database()
        
        with self.database_path.open('r') as f:
            return json.load(f)
    
    def _save_database(self, data: Dict[str, Any]):
        """Save database to file"""
        with self.database_path.open('w') as f:
            json.dump(data, f, indent=2)


# Global learning database instance
LEARNING_DB_PATH = Path("results/learning_database.json")
learning_db = LearningDatabase(LEARNING_DB_PATH)
