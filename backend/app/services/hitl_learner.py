"""
Human-in-the-Loop Learning System
Learns from human feedback to improve future classifications
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import re


class HITLLearner:
    """
    Learns from human feedback to continuously improve classification accuracy.
    
    Key features:
    1. Pattern recognition from corrections
    2. Confidence adjustment based on historical accuracy
    3. Few-shot learning with real examples
    4. Dynamic prompt enhancement
    5. **PERMANENT learning database integration - never loses learning even when cards deleted**
    """
    
    def __init__(self, feedback_dir: Path, prompt_library_path: Path):
        self.feedback_dir = feedback_dir
        self.prompt_library_path = prompt_library_path
        self.feedback_cache = None
        self.patterns = None
        
        # **NEW: Import and use permanent learning database**
        from app.services.learning_database import learning_db
        self.learning_db = learning_db
        
    def load_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Load all feedback from BOTH:
        1. Permanent learning database (primary source - never deleted)
        2. Feedback directory (archival files - may be incomplete if cards deleted)
        """
        if self.feedback_cache is not None:
            return self.feedback_cache
            
        feedback_list = []
        
        # **PRIMARY SOURCE: Load from permanent learning database**
        try:
            permanent_feedback = self.learning_db.get_all_learning_entries()
            feedback_list.extend(permanent_feedback)
            print(f"[HITL] Loaded {len(permanent_feedback)} entries from permanent learning database")
        except Exception as e:
            print(f"[HITL] Error loading from permanent database: {e}")
        
        # **SECONDARY SOURCE: Load from feedback directory (for any additional archival data)**
        if self.feedback_dir.exists():
            for feedback_file in self.feedback_dir.glob("*.json"):
                try:
                    with open(feedback_file, 'r') as f:
                        feedback = json.load(f)
                        # Only add if not already in permanent database
                        doc_id = feedback.get("document_id")
                        if not any(f.get("document_id") == doc_id for f in feedback_list):
                            feedback_list.append(feedback)
                except Exception as e:
                    print(f"[HITL] Error loading feedback {feedback_file}: {e}")
        
        self.feedback_cache = feedback_list
        print(f"[HITL] Total feedback loaded: {len(feedback_list)}")
        return feedback_list
    
    def analyze_corrections(self) -> Dict[str, Any]:
        """
        Analyze all feedback to identify patterns in human corrections.
        
        Returns dict with:
        - frequent_misclassifications: Common AI mistakes
        - keyword_confidence_adjustments: Keywords that indicate lower AI accuracy
        - context_patterns: Document patterns that often get misclassified
        - accuracy_by_category: Success rate per category
        """
        feedback_list = self.load_all_feedback()
        
        if not feedback_list:
            return self._empty_patterns()
        
        patterns = {
            "total_feedback_count": len(feedback_list),
            "correction_rate": 0.0,
            "frequent_misclassifications": [],
            "keyword_confidence_adjustments": {},
            "context_patterns": [],
            "accuracy_by_category": {},
            "common_corrections": [],
            "learned_examples": []
        }
        
        # Track corrections
        corrections = []
        agreements = []
        category_stats = defaultdict(lambda: {"total": 0, "correct": 0, "corrections": []})
        
        for feedback in feedback_list:
            original_class = feedback.get("original_classification")
            human_class = feedback.get("human_classification")
            filename = feedback.get("filename", "unknown")
            reasoning = feedback.get("reasoning", "")
            
            category_stats[original_class]["total"] += 1
            
            if original_class != human_class:
                # This was a correction
                corrections.append({
                    "from": original_class,
                    "to": human_class,
                    "filename": filename,
                    "reasoning": reasoning,
                    "timestamp": feedback.get("timestamp")
                })
                category_stats[original_class]["corrections"].append({
                    "to": human_class,
                    "filename": filename
                })
            else:
                # Human agreed with AI
                agreements.append({
                    "classification": original_class,
                    "filename": filename
                })
                category_stats[original_class]["correct"] += 1
        
        # Calculate correction rate
        patterns["correction_rate"] = len(corrections) / len(feedback_list) if feedback_list else 0.0
        
        # Find most frequent misclassifications
        misclass_counter = Counter((c["from"], c["to"]) for c in corrections)
        patterns["frequent_misclassifications"] = [
            {
                "from": from_cat,
                "to": to_cat,
                "count": count,
                "percentage": count / len(feedback_list) * 100
            }
            for (from_cat, to_cat), count in misclass_counter.most_common(10)
        ]
        
        # Calculate accuracy by category
        for category, stats in category_stats.items():
            total = stats["total"]
            correct = stats["correct"]
            accuracy = (correct / total * 100) if total > 0 else 0
            
            patterns["accuracy_by_category"][category] = {
                "accuracy": accuracy,
                "total_reviews": total,
                "correct": correct,
                "corrections": len(stats["corrections"])
            }
        
        # Extract keyword patterns from corrections
        patterns["keyword_confidence_adjustments"] = self._extract_keyword_patterns(corrections)
        
        # Extract context patterns
        patterns["context_patterns"] = self._extract_context_patterns(corrections)
        
        # Create learned examples for few-shot learning
        patterns["learned_examples"] = self._create_learned_examples(feedback_list)
        
        # Store patterns for future use
        self.patterns = patterns
        
        return patterns
    
    def _extract_keyword_patterns(self, corrections: List[Dict]) -> Dict[str, Any]:
        """
        Extract keywords that correlate with misclassifications.
        Returns confidence adjustment factors for specific keywords.
        """
        keyword_corrections = defaultdict(list)
        
        for correction in corrections:
            filename = correction["filename"].lower()
            reasoning = correction.get("reasoning", "").lower()
            
            # Extract keywords from filename
            words = re.findall(r'\b\w+\b', filename)
            
            for word in words:
                if len(word) > 3:  # Skip short words
                    keyword_corrections[word].append({
                        "from": correction["from"],
                        "to": correction["to"]
                    })
        
        # Calculate confidence adjustments
        adjustments = {}
        for keyword, corr_list in keyword_corrections.items():
            if len(corr_list) >= 2:  # At least 2 corrections with this keyword
                adjustments[keyword] = {
                    "correction_count": len(corr_list),
                    "confidence_multiplier": max(0.5, 1.0 - (len(corr_list) * 0.1)),
                    "common_correction": Counter((c["from"], c["to"]) for c in corr_list).most_common(1)[0]
                }
        
        return adjustments
    
    def _extract_context_patterns(self, corrections: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract document context patterns that often lead to misclassification.
        """
        patterns = []
        
        # Group corrections by type
        correction_groups = defaultdict(list)
        for correction in corrections:
            key = (correction["from"], correction["to"])
            correction_groups[key].append(correction)
        
        # Analyze each group
        for (from_cat, to_cat), group in correction_groups.items():
            if len(group) >= 2:  # Pattern needs at least 2 instances
                # Find common themes in reasoning
                common_words = self._find_common_words([c.get("reasoning", "") for c in group])
                
                patterns.append({
                    "misclassification": {"from": from_cat, "to": to_cat},
                    "frequency": len(group),
                    "common_indicators": common_words[:5],
                    "rule": f"Documents with '{', '.join(common_words[:3])}' are often {to_cat}, not {from_cat}"
                })
        
        return patterns
    
    def _find_common_words(self, texts: List[str]) -> List[str]:
        """Find common meaningful words across texts"""
        if not texts:
            return []
        
        # Extract words from all texts
        all_words = []
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            all_words.extend([w for w in words if len(w) > 4])  # Meaningful words only
        
        # Return most common
        return [word for word, count in Counter(all_words).most_common(10) if count >= 2]
    
    def _create_learned_examples(self, feedback_list: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Create few-shot learning examples from approved feedback.
        Returns examples organized by category.
        """
        examples_by_category = defaultdict(list)
        
        for feedback in feedback_list:
            human_class = feedback.get("human_classification")
            filename = feedback.get("filename", "unknown")
            reasoning = feedback.get("reasoning", "")
            
            # Create example
            example = {
                "filename": filename,
                "classification": human_class,
                "reasoning": reasoning,
                "timestamp": feedback.get("timestamp"),
                "confidence": "high" if feedback.get("original_classification") == human_class else "corrected"
            }
            
            examples_by_category[human_class].append(example)
        
        # Limit to top 3 per category
        for category in examples_by_category:
            examples_by_category[category] = examples_by_category[category][:3]
        
        return dict(examples_by_category)
    
    def _empty_patterns(self) -> Dict[str, Any]:
        """Return empty patterns structure"""
        return {
            "total_feedback_count": 0,
            "correction_rate": 0.0,
            "frequent_misclassifications": [],
            "keyword_confidence_adjustments": {},
            "context_patterns": [],
            "accuracy_by_category": {},
            "common_corrections": [],
            "learned_examples": {}
        }
    
    def adjust_confidence_for_document(
        self,
        classification: str,
        confidence: float,
        filename: str,
        content_preview: str
    ) -> Tuple[float, bool, Optional[str]]:
        """
        Adjust confidence score based on historical feedback patterns.
        
        Returns:
            (adjusted_confidence, requires_review, review_reason)
        """
        if self.patterns is None:
            self.patterns = self.analyze_corrections()
        
        original_confidence = confidence
        requires_review = False
        review_reason = None
        
        # Check category accuracy
        category_stats = self.patterns.get("accuracy_by_category", {}).get(classification)
        if category_stats:
            accuracy = category_stats["accuracy"]
            if accuracy < 70:  # Low historical accuracy for this category
                confidence *= 0.85
                requires_review = True
                review_reason = f"AI has {accuracy:.1f}% accuracy for {classification} (below threshold)"
        
        # Check for problematic keywords
        filename_lower = filename.lower()
        keyword_adjustments = self.patterns.get("keyword_confidence_adjustments", {})
        
        for keyword, adjustment in keyword_adjustments.items():
            if keyword in filename_lower or keyword in content_preview.lower():
                multiplier = adjustment["confidence_multiplier"]
                confidence *= multiplier
                
                if multiplier < 0.8:
                    requires_review = True
                    review_reason = f"Documents with '{keyword}' have been corrected {adjustment['correction_count']} times"
        
        # Check for known misclassification patterns
        for pattern in self.patterns.get("context_patterns", []):
            if pattern["misclassification"]["from"] == classification:
                # Check if any indicators are present
                indicators = pattern["common_indicators"]
                matches = sum(1 for ind in indicators if ind in content_preview.lower())
                
                if matches >= 2:  # Multiple indicators match
                    confidence *= 0.75
                    requires_review = True
                    review_reason = f"Similar documents have been reclassified as {pattern['misclassification']['to']}"
        
        # Ensure confidence stays in valid range
        confidence = max(0.1, min(1.0, confidence))

        return confidence, requires_review, review_reason

    def apply_learned_classification(
        self,
        classification: str,
        confidence: float,
        filename: str,
        content_preview: str,
        keywords: List[str]
    ) -> Tuple[str, float, bool, Optional[str]]:
        """
        Check if a learned classification pattern should override the AI's classification.
        This applies strong learning rules (e.g., "PII documents must be Highly Sensitive").

        Returns:
            (final_classification, final_confidence, was_overridden, override_reason)
        """
        if self.patterns is None:
            self.patterns = self.analyze_corrections()

        feedback_list = self.load_all_feedback()
        if not feedback_list:
            return classification, confidence, False, None

        # Check for strong classification rules from human feedback
        for feedback in feedback_list:
            if not feedback.get("approved"):  # Only look at corrections
                original_class = feedback.get("original_classification")
                corrected_class = feedback.get("corrected_classification")

                # Check if current AI classification matches a previously corrected one
                if classification == original_class:
                    # Get key indicators from the learned feedback
                    learned_indicators = feedback.get("key_indicators", [])
                    feedback_notes = feedback.get("feedback_notes", "").lower()

                    # Count how many learned indicators match current document
                    content_lower = content_preview.lower()
                    filename_lower = filename.lower()
                    combined_keywords = set([k.lower() for k in keywords]) if keywords else set()

                    indicator_matches = 0
                    for indicator in learned_indicators:
                        indicator_lower = indicator.lower()
                        if (indicator_lower in content_lower or
                            indicator_lower in filename_lower or
                            indicator_lower in combined_keywords):
                            indicator_matches += 1

                    # Strong match threshold: 3+ matching indicators or 50%+ of indicators match
                    match_threshold = max(3, len(learned_indicators) * 0.5)

                    # **DEBUG: Log matching details**
                    print(f"[HITL DEBUG] Checking learned pattern: {original_class} → {corrected_class}")
                    print(f"[HITL DEBUG] Indicators to match: {len(learned_indicators)}")
                    print(f"[HITL DEBUG] Indicators found: {indicator_matches}")
                    print(f"[HITL DEBUG] Match threshold: {match_threshold}")
                    print(f"[HITL DEBUG] Keywords available: {len(keywords) if keywords else 0}")

                    if indicator_matches >= match_threshold:
                        # Apply the learned classification
                        override_reason = (
                            f"Learned rule applied: '{original_class}' → '{corrected_class}'. "
                            f"Matched {indicator_matches}/{len(learned_indicators)} indicators. "
                            f"Human feedback: {feedback.get('feedback_notes', 'Rule from previous correction')[:100]}"
                        )

                        print(f"[HITL OVERRIDE] {override_reason}")

                        # Increase confidence since this is a learned pattern
                        new_confidence = min(0.98, confidence + 0.10)

                        return corrected_class, new_confidence, True, override_reason

        return classification, confidence, False, None

    def get_few_shot_examples(self, classification: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Get few-shot learning examples for a specific classification.
        These can be added to prompts to improve accuracy.
        """
        if self.patterns is None:
            self.patterns = self.analyze_corrections()
        
        learned_examples = self.patterns.get("learned_examples", {})
        examples = learned_examples.get(classification, [])
        
        return examples[:limit]
    
    def generate_prompt_enhancements(self) -> Dict[str, str]:
        """
        Generate prompt enhancements based on learned patterns.
        Returns additional instructions to add to classification prompts.
        """
        if self.patterns is None:
            self.patterns = self.analyze_corrections()
        
        enhancements = {}
        
        # Add warnings for frequent misclassifications
        for misclass in self.patterns.get("frequent_misclassifications", [])[:3]:
            from_cat = misclass["from"]
            to_cat = misclass["to"]
            
            warning = (
                f"⚠️ LEARNED PATTERN: Documents initially classified as '{from_cat}' "
                f"have been corrected to '{to_cat}' {misclass['count']} times "
                f"({misclass['percentage']:.1f}% of feedback). "
                f"Carefully verify this classification."
            )
            
            enhancements[f"warning_{from_cat}"] = warning
        
        # Add context pattern rules
        for pattern in self.patterns.get("context_patterns", [])[:3]:
            rule_key = f"rule_{pattern['misclassification']['from']}_to_{pattern['misclassification']['to']}"
            enhancements[rule_key] = pattern["rule"]
        
        return enhancements
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics about the learning system.
        """
        if self.patterns is None:
            self.patterns = self.analyze_corrections()
        
        return {
            "total_feedback": self.patterns["total_feedback_count"],
            "correction_rate": f"{self.patterns['correction_rate'] * 100:.1f}%",
            "accuracy_by_category": self.patterns["accuracy_by_category"],
            "patterns_learned": len(self.patterns["context_patterns"]),
            "keywords_tracked": len(self.patterns["keyword_confidence_adjustments"]),
            "examples_available": sum(
                len(examples) 
                for examples in self.patterns["learned_examples"].values()
            )
        }
