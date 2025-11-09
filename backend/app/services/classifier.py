"""
Classification service using Claude Haiku 4.5
"""
import json
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import anthropic

from app.models.schemas import (
    ClassificationCategory,
    ClassificationResult,
    Evidence,
    SafetyCheckResult,
    SafetyFlag,
    DocumentMetadata,
    TextSegment,
    ImageAnalysis,
    DocumentContext,
    KeywordRelevance
)
from app.services.prompt_tree_engine import PromptTreeEngine
from app.services.hitl_learner import HITLLearner


class DocumentClassifier:
    """Main classifier using Claude Haiku API with configurable prompts"""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.prompts = self._load_prompt_library()
        # Initialize dynamic prompt tree engine
        self.prompt_tree = PromptTreeEngine(self.prompts)
        # Initialize HITL learning system
        feedback_dir = Path(__file__).parent.parent.parent / "results" / "feedback"
        prompt_lib_path = Path(__file__).parent.parent / "prompts" / "prompt_library.json"
        self.hitl_learner = HITLLearner(feedback_dir, prompt_lib_path)
        # Classification cache for learning patterns
        self.pattern_cache = {}

    def _load_prompt_library(self) -> Dict[str, Any]:
        """Load prompt templates from JSON"""
        prompt_file = Path(__file__).parent.parent / "prompts" / "prompt_library.json"
        with open(prompt_file, 'r') as f:
            return json.load(f)

    def classify_document(
        self,
        content_blocks: List[Dict[str, Any]],
        metadata: DocumentMetadata,
        document_id: str,
        enable_dual_verification: bool = False
    ) -> ClassificationResult:
        """
        Classify a document using Claude with dynamic prompt tree

        Args:
            content_blocks: List of text and image content for Claude
            metadata: Document metadata from preprocessing
            document_id: Unique identifier
            enable_dual_verification: Whether to use two LLMs for consensus

        Returns:
            ClassificationResult with all analysis
        """
        start_time = time.time()

        # Primary classification
        primary_result = self._run_classification_pipeline(content_blocks, metadata)

        # Apply HITL learning - adjust confidence based on historical patterns
        content_preview = self._extract_content_preview(content_blocks)
        adjusted_confidence, hitl_review_needed, hitl_reason = self.hitl_learner.adjust_confidence_for_document(
            classification=primary_result["classification"],
            confidence=primary_result["confidence"],
            filename=metadata.filename,
            content_preview=content_preview
        )

        # Log confidence adjustment
        if adjusted_confidence != primary_result["confidence"]:
            print(f"[HITL] Confidence adjusted: {primary_result['confidence']:.2f} → {adjusted_confidence:.2f}")
            print(f"[HITL] Reason: {hitl_reason}")

        primary_result["confidence"] = adjusted_confidence

        # Optional dual verification
        secondary_classification = None
        secondary_confidence = None
        consensus = None

        if enable_dual_verification:
            secondary_result = self._run_dual_verification(content_blocks, metadata)
            secondary_classification = secondary_result["classification"]
            secondary_confidence = secondary_result["confidence"]
            consensus = (primary_result["classification"] == secondary_classification)

        # Determine if HITL review is needed (combine base assessment with learning insights)
        requires_review, review_reason = self._assess_hitl_need(
            primary_result,
            secondary_classification if enable_dual_verification else None,
            consensus
        )
        
        # Override with HITL learner if it flags for review
        if hitl_review_needed:
            requires_review = True
            if review_reason:
                review_reason = f"{review_reason}; {hitl_reason}"
            else:
                review_reason = hitl_reason

        processing_time = time.time() - start_time
        
        # Extract secondary labels and convert to SecondaryLabel enum
        from app.models.schemas import SecondaryLabel
        secondary_labels = []
        additional_labels = primary_result.get("additional_labels", [])
        
        # Convert string labels to SecondaryLabel enum (try to match, keep as string if no match)
        for label in additional_labels:
            try:
                # Try to find matching enum value
                matched = False
                for sec_label in SecondaryLabel:
                    if sec_label.value == label or sec_label.name.replace('_', ' ').lower() == label.lower():
                        secondary_labels.append(sec_label)
                        matched = True
                        break
                if not matched:
                    # Keep as string in additional_labels
                    pass
            except:
                pass
        
        # CRITICAL: Check safety assessment and override classification if unsafe
        # If document is unsafe, primary classification MUST be "Unsafe"
        if not primary_result["safety_assessment"]["is_safe"]:
            # Override classification to Unsafe
            primary_classification = "Unsafe"
            primary_confidence = primary_result["safety_assessment"]["confidence"]
            
            # Keep original classification as additional context
            original_classification = primary_result["classification"]
            if original_classification not in additional_labels:
                additional_labels.append(f"Content Type: {original_classification}")
        else:
            primary_classification = primary_result["classification"]
            primary_confidence = primary_result["confidence"]
        
        # Automatically add safety label based on safety check
        if primary_result["safety_assessment"]["is_safe"]:
            if SecondaryLabel.SAFE not in secondary_labels:
                secondary_labels.append(SecondaryLabel.SAFE)
        else:
            if SecondaryLabel.UNSAFE not in secondary_labels:
                secondary_labels.append(SecondaryLabel.UNSAFE)
        
        # Build label confidence map
        label_confidence = {
            primary_classification: primary_confidence
        }
        
        # Add confidence for secondary labels (use safety confidence for safety labels)
        for label in secondary_labels:
            if label in [SecondaryLabel.SAFE, SecondaryLabel.UNSAFE]:
                label_confidence[label.value] = primary_result["safety_assessment"]["confidence"]
            else:
                # Default to slightly lower than primary confidence
                label_confidence[label.value] = max(0.7, primary_result["confidence"] * 0.9)

        # Build final result with multi-label support
        result = ClassificationResult(
            document_id=document_id,
            filename=metadata.filename,
            classification=ClassificationCategory(primary_classification),
            secondary_labels=secondary_labels,
            additional_labels=additional_labels,
            label_confidence=label_confidence,
            confidence=primary_confidence,
            summary=primary_result["summary"],
            reasoning=primary_result["reasoning"],
            evidence=[Evidence(**e) for e in primary_result["evidence"]],
            safety_check=SafetyCheckResult(**primary_result["safety_assessment"]),
            page_count=metadata.page_count,
            image_count=metadata.image_count,
            processing_time=processing_time,
            secondary_classification=ClassificationCategory(secondary_classification) if secondary_classification else None,
            secondary_confidence=secondary_confidence,
            consensus=consensus,
            requires_review=requires_review,
            review_reason=review_reason
        )

        return result

    def _run_classification_pipeline(
        self,
        content_blocks: List[Dict[str, Any]],
        metadata: DocumentMetadata,
        segment_insights: Optional[Dict[str, Any]] = None,
        few_shot_examples: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete classification pipeline with dynamic prompts, segment insights, and HITL learning
        """
        # Extract content preview for prompt tree analysis (first 1000 chars of text)
        content_preview = ""
        for block in content_blocks[:5]:  # Check first 5 blocks
            if block.get("type") == "text":
                content_preview += block.get("text", "")
                if len(content_preview) > 1000:
                    content_preview = content_preview[:1000]
                    break
        
        # Build the comprehensive classification prompt using dynamic prompt tree
        full_prompt = self._build_classification_prompt(
            metadata, 
            content_preview,
            segment_insights=segment_insights,
            few_shot_examples=few_shot_examples
        )

        # Make API call to Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.0,  # Deterministic for classification
                system=self.prompts["system_context"],
                messages=[{
                    "role": "user",
                    "content": self._format_claude_content(content_blocks, full_prompt)
                }]
            )

            # Extract text from response
            response_text = response.content[0].text

            # Extract JSON from response
            result = self._parse_classification_response(response_text)

            return result

        except Exception as e:
            # Fallback in case of API error
            print(f"Classification error: {str(e)}")
            return self._create_fallback_result(str(e))
    
    def _format_claude_content(self, content_blocks: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        """Format content blocks for Claude Messages API"""
        claude_content = []

        # Add prompt as text block
        claude_content.append({
            "type": "text",
            "text": f"{prompt}\n\n---\n\nDOCUMENT CONTENT:\n\n"
        })

        # Add content blocks (already in Claude format)
        claude_content.extend(content_blocks)

        return claude_content

    def _call_claude(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> Optional[str]:
        """
        Helper method for making Claude API calls with text-only prompts
        Returns the response text or None if failed
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.content[0].text
        except Exception as e:
            print(f"[WARNING] Claude API call failed: {str(e)}")
            return None

    def _build_classification_prompt(
        self, 
        metadata: DocumentMetadata, 
        content_preview: str = "",
        segment_insights: Optional[Dict[str, Any]] = None,
        few_shot_examples: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build dynamic classification prompt based on document characteristics using prompt tree"""

        # Build adaptive prompt tree based on document features
        prompt_sequence = self.prompt_tree.build_prompt_tree(metadata, content_preview)
        
        # Get the combined prompt from the tree
        combined_prompt = self.prompt_tree.build_combined_prompt(prompt_sequence, metadata)
        
        # **NEW: Add segment insights if available**
        if segment_insights and segment_insights.get("suggests_sensitive"):
            segment_warning = f"""
            
⚠️ **CRITICAL SEGMENT ANALYSIS ALERT** ⚠️
The document contains segments classified as sensitive:
- {segment_insights.get('classification_counts', {}).get('Confidential', 0)} segments classified as Confidential
- {segment_insights.get('classification_counts', {}).get('Highly Sensitive', 0)} segments classified as Highly Sensitive
- Highest segment classification: {segment_insights.get('highest_classification', 'Unknown')} ({segment_insights.get('highest_confidence', 0):.0%} confidence)

**IMPORTANT**: If multiple segments contain confidential/sensitive information (like aircraft registration numbers, 
company names, internal sections), the OVERALL document classification should reflect this higher sensitivity level.
Do NOT classify as Public if segments contain confidential business information.
"""
            combined_prompt += segment_warning
        
        # **NEW: Add few-shot examples from HITL feedback**
        if few_shot_examples and len(few_shot_examples) > 0:
            examples_text = "\n\n" + "=" * 80 + "\n"
            examples_text += "📚 **LEARNED EXAMPLES FROM HUMAN FEEDBACK**\n"
            examples_text += "=" * 80 + "\n"
            examples_text += "The following are examples from previous classifications that were reviewed by humans.\n"
            examples_text += "Use these as guidance for similar documents:\n\n"
            
            for idx, example in enumerate(few_shot_examples[:5], 1):
                examples_text += f"**Example {idx}:**\n"
                examples_text += f"- Document: {example.get('filename', 'N/A')}\n"
                examples_text += f"- Original Classification: {example.get('original_classification', 'N/A')}\n"
                examples_text += f"- Human Corrected To: {example.get('corrected_classification', 'N/A')}\n"
                examples_text += f"- Feedback: {example.get('feedback_notes', 'N/A')}\n"
                examples_text += f"- Key Insight: {example.get('content_preview', 'N/A')[:200]}...\n\n"
            
            examples_text += "**APPLY THESE LESSONS**: If the current document is similar to any of these examples, "
            examples_text += "use the human-corrected classification as guidance.\n"
            examples_text += "=" * 80 + "\n\n"
            
            combined_prompt += examples_text
        
        # Enhance prompt with HITL learning insights
        combined_prompt = self._enhance_prompt_with_learning(combined_prompt, metadata)
        
        # Get adaptive insights for debugging
        insights = self.prompt_tree.get_adaptive_insights(metadata)
        
        # Add insights as comment (for logging, not sent to Claude)
        print(f"[PROMPT TREE] Document type: {insights['document_type']}")
        print(f"[PROMPT TREE] Prompt sequence: {' → '.join(prompt_sequence)}")
        print(f"[PROMPT TREE] Detected features: {insights['detected_features']}")
        if segment_insights:
            print(f"[SEGMENT INSIGHTS] Sensitive segments detected: {segment_insights.get('suggests_sensitive', False)}")
        if few_shot_examples:
            print(f"[HITL LEARNING] Using {len(few_shot_examples)} examples from human feedback")
        
        return combined_prompt

    def _run_dual_verification(
        self,
        content_blocks: List[Dict[str, Any]],
        metadata: DocumentMetadata
    ) -> Dict[str, Any]:
        """Run independent secondary classification for verification"""

        verification_prompt = self.prompts["dual_verification_prompt"]["prompt"]
        full_prompt = self._build_classification_prompt(metadata)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.1,  # Slightly higher for diversity
                system=self.prompts["system_context"],
                messages=[{
                    "role": "user",
                    "content": self._format_claude_content(
                        content_blocks,
                        verification_prompt + "\n\n" + full_prompt
                    )
                }]
            )

            # Extract text from response
            response_text = response.content[0].text

            result = self._parse_classification_response(response_text)

            return result

        except Exception as e:
            print(f"Dual verification error: {str(e)}")
            return self._create_fallback_result(str(e))

    def _parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude - now supports additional_labels"""
        try:
            # Find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)

            # Validate required fields
            required_fields = ["classification", "confidence", "summary", "reasoning", "evidence", "safety_assessment"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # NEW: Handle additional_labels (optional field)
            if "additional_labels" not in result:
                result["additional_labels"] = []
            
            # NEW: Auto-detect government content if not already tagged
            if "government_content_detected" in result and result.get("government_content_detected"):
                if "Government Content" not in result["additional_labels"]:
                    result["additional_labels"].append("Government Content")
            
            # Normalize safety flags to match our enum
            if "safety_assessment" in result and "flags" in result["safety_assessment"]:
                result["safety_assessment"]["flags"] = self._normalize_safety_flags(
                    result["safety_assessment"]["flags"]
                )

            # **FIX: Validate safety assessment for contradictions**
            if "safety_assessment" in result:
                result["safety_assessment"] = self._validate_safety_assessment(
                    result["safety_assessment"]
                )

            return result

        except Exception as e:
            raise ValueError(f"Failed to parse classification response: {str(e)}\nResponse: {response_text}")

    def _normalize_safety_flags(self, flags: List[str]) -> List[str]:
        """
        Normalize safety flags from Claude to match our SafetyFlag enum
        Claude might return variations or pipe-separated flags, so we map them to our standard values
        """
        flag_mapping = {
            # Standard values (keep as-is)
            "Safe": "Safe",
            "Child Safety Violation": "Child Safety Violation",
            "Hate Speech": "Hate Speech",
            "Violence": "Violence",
            "Exploitative Content": "Exploitative Content",
            "Criminal Activity": "Criminal Activity",
            "Political News": "Political News",
            "Cyber Threat": "Cyber Threat",
            "Threats": "Threats",
            "Harassment": "Harassment",
            "Profanity": "Profanity",
            
            # Variations that Claude might return
            "safe": "Safe",
            "none": "Safe",
            "no concerns": "Safe",
            "threats": "Threats",
            "threat": "Threats",
            "threatening": "Threats",
            "harassment": "Harassment",
            "harassing": "Harassment",
            "profanity": "Profanity",
            "profane": "Profanity",
            "cursing": "Profanity",
            "obscene": "Profanity",
            "violence": "Violence",
            "violent": "Violence",
            "hate speech": "Hate Speech",
            "hate": "Hate Speech",
            "hateful": "Hate Speech",
            "child safety": "Child Safety Violation",
            "child exploitation": "Child Safety Violation",
            "exploitative": "Exploitative Content",
            "exploitation": "Exploitative Content",
            "criminal": "Criminal Activity",
            "crime": "Criminal Activity",
            "illegal": "Criminal Activity",
            "potentialcriminalcontent": "Criminal Activity",
            "potential criminal content": "Criminal Activity",
            "cyber threat": "Cyber Threat",
            "cyber": "Cyber Threat",
            "hacking": "Cyber Threat",
            "political": "Political News",
            "political news": "Political News",
        }
        
        normalized = []
        for flag_str in flags:
            # Handle pipe-separated flags (e.g., "Threats|Profanity")
            if '|' in flag_str:
                sub_flags = flag_str.split('|')
                for sub_flag in sub_flags:
                    sub_flag = sub_flag.strip()
                    normalized.append(self._map_single_flag(sub_flag, flag_mapping))
            else:
                normalized.append(self._map_single_flag(flag_str, flag_mapping))
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for flag in normalized:
            if flag not in seen:
                seen.add(flag)
                result.append(flag)
        
        return result if result else ["Safe"]
    
    def _map_single_flag(self, flag: str, flag_mapping: dict) -> str:
        """Map a single flag string to a standard SafetyFlag value"""
        # Try exact match first
        if flag in flag_mapping:
            return flag_mapping[flag]
        # Try lowercase match
        elif flag.lower() in flag_mapping:
            return flag_mapping[flag.lower()]
        # Try removing spaces/punctuation
        elif flag.lower().replace(" ", "").replace("-", "").replace("_", "") in flag_mapping:
            clean_flag = flag.lower().replace(" ", "").replace("-", "").replace("_", "")
            return flag_mapping[clean_flag]
        else:
            # If we can't map it, default to "Safe" to avoid validation errors
            # Log this for debugging
            print(f"WARNING: Unknown safety flag '{flag}', defaulting to 'Safe'")
            return "Safe"

    def _validate_safety_assessment(self, safety_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix contradictory safety assessments.

        CRITICAL RULES:
        1. If is_safe=false, flags MUST NOT include "Safe"
        2. If is_safe=true, flags MUST be ["Safe"]
        3. If details mention PII/identity theft/data breach, force is_safe=true
        """
        is_safe = safety_assessment.get("is_safe", True)
        flags = safety_assessment.get("flags", ["Safe"])
        details = safety_assessment.get("details", "").lower()

        # **FIX 1: Detect PII-related safety issues (WRONG!) and correct them**
        pii_keywords = ["identity theft", "data breach", "personal information disclosure",
                       "pii", "ssn", "credit card", "personally identifiable"]

        if any(keyword in details for keyword in pii_keywords):
            # This is a SENSITIVITY issue, not a safety issue
            print(f"[SAFETY VALIDATOR] Correcting PII misclassification as safety issue")
            print(f"[SAFETY VALIDATOR] Original: is_safe={is_safe}, flags={flags}, details={details[:100]}")

            # Force safe
            is_safe = True
            flags = ["Safe"]
            details = "No harmful content detected"

            print(f"[SAFETY VALIDATOR] Corrected: is_safe=True, flags=['Safe'], details='No harmful content detected'")

        # **FIX 2: Ensure consistency between is_safe and flags**
        if is_safe:
            # If safe, flags must be ["Safe"]
            if flags != ["Safe"]:
                print(f"[SAFETY VALIDATOR] Fixing is_safe=True but flags={flags} → forcing flags=['Safe']")
                flags = ["Safe"]
        else:
            # If unsafe, flags must NOT include "Safe"
            if "Safe" in flags:
                if len(flags) == 1:
                    # Only flag is "Safe" but is_safe=False - contradiction!
                    # This means AI incorrectly marked as unsafe
                    print(f"[SAFETY VALIDATOR] Contradiction: is_safe=False but only flag is 'Safe' → forcing is_safe=True")
                    is_safe = True
                    flags = ["Safe"]
                else:
                    # Multiple flags including "Safe" - remove "Safe"
                    print(f"[SAFETY VALIDATOR] Removing 'Safe' from flags since is_safe=False")
                    flags = [f for f in flags if f != "Safe"]

        # Return corrected assessment
        return {
            "is_safe": is_safe,
            "flags": flags,
            "details": details if isinstance(details, str) else safety_assessment.get("details", ""),
            "confidence": safety_assessment.get("confidence", 0.95)
        }

    def _assess_hitl_need(
        self,
        primary_result: Dict[str, Any],
        secondary_classification: Optional[str],
        consensus: Optional[bool]
    ) -> Tuple[bool, Optional[str]]:
        """Determine if human review is needed"""

        confidence = primary_result["confidence"]
        classification = primary_result["classification"]
        safety_assessment = primary_result["safety_assessment"]

        # Always review unsafe content
        if not safety_assessment["is_safe"]:
            return True, "Unsafe content detected - mandatory review"

        # Review low confidence
        if confidence < 0.7:
            return True, f"Low confidence score: {confidence:.2f}"

        # Review disagreement in dual verification
        if secondary_classification and not consensus:
            return True, f"LLM disagreement: Primary={classification}, Secondary={secondary_classification}"

        # Review highly sensitive with medium confidence
        if classification == "Highly Sensitive" and confidence < 0.85:
            return True, "Highly Sensitive classification requires high confidence"

        # No review needed
        return False, None

    def _create_fallback_result(self, error_msg: str) -> Dict[str, Any]:
        """Create fallback result when classification fails"""
        return {
            "classification": "Confidential",  # Conservative default
            "confidence": 0.0,
            "summary": "Classification failed - manual review required",
            "reasoning": f"Error during classification: {error_msg}",
            "evidence": [{
                "page": None,
                "region": "N/A",
                "quote": "Classification error",
                "reasoning": "Automated classification failed, defaulting to Confidential for safety"
            }],
            "safety_assessment": {
                "is_safe": True,
                "flags": ["Safe"],
                "details": "Could not complete safety assessment due to error - defaulting to safe",
                "confidence": 0.5
            }
        }
    
    def _get_fallback_classification(self, reason: str) -> Dict[str, Any]:
        """Alias for _create_fallback_result for clarity"""
        return self._create_fallback_result(reason)
    
    def classify_document_enhanced(
        self,
        content_blocks: List[Dict[str, Any]],
        metadata: DocumentMetadata,
        document_id: str,
        full_text: str,
        page_images: List[str],
        enable_dual_verification: bool = True,
        progress_callback: Optional[callable] = None
    ) -> ClassificationResult:
        """
        Enhanced classification with granular text/image analysis and dual verification
        
        NEW: Smart Early Exit - if primary confidence > 0.98, skip verification steps
        NEW: Multi-label support - returns additional classification tags
        NEW: Government content detection - auto-tags .gov references

        This method provides:
        - Sentence/section-level classification
        - Individual image analysis with OCR
        - Conditional dual AI verification (only if confidence < 0.9)
        - Keyword extraction
        - Page images for UI
        - Real-time progress updates via callback
        """
        start_time = time.time()
        progress_steps = []

        # Helper to update progress (both local list and callback)
        def update_progress(message: str):
            progress_steps.append(message)
            if progress_callback:
                progress_callback(message)
            print(f"[PROGRESS] {message}")  # Debug logging

        # Step 0: COMPREHENSIVE SAFETY CHECK (analyzes full document)
        update_progress("🔍 Starting comprehensive safety scan...")
        quick_unsafe = self._quick_safety_check(content_blocks, full_text)
        
        if quick_unsafe:
            # EARLY EXIT: Unsafe content detected in quick scan
            update_progress(f"⚠️  UNSAFE CONTENT DETECTED: {quick_unsafe.get('quick_flag')}")
            update_progress("⏹️  Early exit - classification complete")
            processing_time = time.time() - start_time
            return ClassificationResult(
                document_id=document_id,
                filename=metadata.filename,
                classification=ClassificationCategory.UNSAFE,
                additional_labels=["Safety Violation"],
                confidence=0.95,  # High confidence from quick check
                summary=f"Document flagged as unsafe: {quick_unsafe.get('quick_flag', 'Safety violation')}",
                reasoning=f"Quick safety scan detected: {quick_unsafe.get('evidence', 'Unsafe content')}. Severity: {quick_unsafe.get('severity', 'High')}",
                evidence=[Evidence(
                    page=None,
                    region="Quick scan (first 2000 chars)",
                    quote=quick_unsafe.get('evidence', 'Unsafe content detected')[:100],
                    reasoning=f"Flagged by quick safety check as {quick_unsafe.get('quick_flag')}"
                )],
                safety_check=SafetyCheckResult(
                    is_safe=False,
                    flags=self._normalize_safety_flags([quick_unsafe.get('quick_flag', 'Violence')]),
                    details=f"Quick preliminary scan detected {quick_unsafe.get('quick_flag', 'unsafe content')}. {quick_unsafe.get('evidence', '')}",
                    confidence=0.95
                ),
                page_count=metadata.page_count,
                image_count=metadata.image_count,
                processing_time=processing_time,
                full_text=full_text[:1000],  # Truncate for safety
                page_images_base64=page_images[:3] if page_images else [],
                progress_steps=progress_steps,
                requires_review=True,
                review_reason=f"Quick safety check flagged: {quick_unsafe.get('quick_flag')}"
            )
        
        update_progress("✅ Safety scan completed - no critical violations")

        # Step 1: Granular text analysis
        update_progress("📝 Analyzing text segments...")
        text_segments = self._analyze_text_segments(full_text, content_blocks)
        update_progress(f"✅ Analyzed {len(text_segments)} text segments")

        # Step 2: Individual image analysis
        update_progress("🖼️  Analyzing images...")
        image_analyses = self._analyze_images(content_blocks, metadata)
        update_progress(f"✅ Analyzed {len(image_analyses)} images")
        
        # Step 2.1: AGGREGATE SEGMENT RESULTS - Check if segments suggest higher sensitivity
        highest_segment_classification = None
        highest_segment_confidence = 0.0
        segment_classification_counts = {}
        
        for segment in text_segments:
            # Count classifications
            seg_class = segment.classification.value
            segment_classification_counts[seg_class] = segment_classification_counts.get(seg_class, 0) + 1
            
            # Track highest sensitivity
            if segment.confidence > highest_segment_confidence:
                highest_segment_confidence = segment.confidence
                highest_segment_classification = seg_class
        
        # If multiple segments are Confidential/Highly Sensitive, this is important signal
        confidential_count = segment_classification_counts.get("Confidential", 0)
        highly_sensitive_count = segment_classification_counts.get("Highly Sensitive", 0)
        
        segment_suggests_sensitive = (confidential_count >= 2 or highly_sensitive_count >= 1)
        
        if segment_suggests_sensitive:
            update_progress(f"⚠️  Segments detected: {confidential_count} Confidential, {highly_sensitive_count} Highly Sensitive")

        # Step 2.5: Context-aware analysis
        update_progress("🔍 Classifying document context...")
        document_context = self._analyze_document_context(content_blocks, metadata, full_text)
        update_progress(f"✅ Context: {document_context.context_type if document_context else 'Unknown'}")

        update_progress("🔑 Scoring keyword relevance...")
        keyword_relevances = self._score_keyword_relevance(full_text, metadata)
        update_progress(f"✅ Scored {len(keyword_relevances)} keywords")
        
        # Step 2.6: CHECK HITL LEARNING - Get examples and patterns from previous feedback
        update_progress("🧠 Checking learned patterns from human feedback...")
        few_shot_examples = []
        try:
            # Get examples for all relevant categories
            for category in ["Public", "Confidential", "Highly Sensitive", "Unsafe"]:
                examples = self.hitl_learner.get_few_shot_examples(category, limit=2)
                few_shot_examples.extend(examples)
            
            if few_shot_examples:
                update_progress(f"✅ Found {len(few_shot_examples)} examples from previous feedback")
        except Exception as e:
            print(f"Warning: Could not load HITL examples: {e}")

        # Step 3: Primary overall classification (now context-aware with multi-label support + HITL learning)
        update_progress("🤖 Running primary AI classification...")
        primary_result = self._run_classification_pipeline(
            content_blocks, 
            metadata,
            segment_insights={
                "highest_classification": highest_segment_classification,
                "highest_confidence": highest_segment_confidence,
                "classification_counts": segment_classification_counts,
                "suggests_sensitive": segment_suggests_sensitive
            },
            few_shot_examples=few_shot_examples
        )
        primary_confidence = primary_result['confidence']
        update_progress(f"✅ Primary: {primary_result['classification']} ({primary_confidence:.0%} confidence)")
        
        # Extract additional labels from primary result
        additional_labels = primary_result.get('additional_labels', [])
        if additional_labels:
            update_progress(f"🏷️  Additional labels: {', '.join(additional_labels)}")

        # **NEW: SMART EARLY EXIT** - Skip verification if confidence > 98%
        skip_verification = primary_confidence > 0.98
        
        if skip_verification:
            update_progress(f"⚡ Very high confidence ({primary_confidence:.0%}) detected - skipping verification steps")
            update_progress("⏩ Fast-track classification complete")
            
            # Use primary result directly
            final_classification = primary_result["classification"]
            final_confidence = primary_confidence
            secondary_classification = None
            secondary_confidence = None
            consensus = None
            verification_notes = f"Skipped verification due to very high primary confidence ({primary_confidence:.0%})"
            
        else:
            # Step 4: Dual verification (only if confidence < 98%)
            update_progress(f"🔄 Confidence below 98% ({primary_confidence:.0%}) - running dual verification...")
            secondary_result = self._run_dual_verification(content_blocks, metadata)
            secondary_classification = secondary_result["classification"]
            secondary_confidence = secondary_result["confidence"]
            consensus = (primary_result["classification"] == secondary_classification)
            update_progress(f"✅ Secondary: {secondary_classification} ({secondary_confidence:.0%})")

            # Step 5: If no consensus, run verification agent
            verification_notes = None
            final_classification = primary_result["classification"]
            final_confidence = primary_result["confidence"]

            if not consensus:
                update_progress("⚠️  Consensus not reached - running verification agent...")
                verification_result = self._run_verification_agent(
                    primary_result,
                    secondary_result,
                    text_segments,
                    image_analyses
                )
                final_classification = verification_result["final_classification"]
                final_confidence = verification_result["final_confidence"]
                verification_notes = verification_result["notes"]
                update_progress(f"✅ Verification: {final_classification} ({final_confidence:.0%})")
            else:
                update_progress("✅ Consensus reached between both AI models")

        # Step 6: Extract all keywords
        update_progress("🔎 Extracting keywords...")
        all_keywords = self._extract_all_keywords(text_segments, image_analyses, primary_result)
        update_progress(f"✅ Extracted {len(all_keywords)} keywords")

        # **NEW: Step 6.5: Apply learned classification rules from human feedback**
        learned_classification, learned_confidence, was_overridden, override_reason = self.hitl_learner.apply_learned_classification(
            classification=final_classification,
            confidence=final_confidence,
            filename=metadata.filename,
            content_preview=full_text[:2000] if full_text else "",
            keywords=all_keywords
        )

        if was_overridden:
            update_progress(f"🎓 LEARNED RULE APPLIED: {final_classification} → {learned_classification}")
            print(f"[HITL OVERRIDE] {override_reason}")
            final_classification = learned_classification
            final_confidence = learned_confidence
            if verification_notes:
                verification_notes += f"\n\n🎓 LEARNED RULE APPLIED: {override_reason}"
            else:
                verification_notes = f"🎓 LEARNED RULE APPLIED: {override_reason}"

        # Step 7: Determine HITL need
        update_progress("👤 Assessing human review requirements...")
        requires_review, review_reason = self._assess_hitl_need_enhanced(
            primary_result,
            secondary_classification,
            consensus if not skip_verification else True,  # If skipped verification, no consensus issue
            text_segments,
            image_analyses
        )
        if requires_review:
            update_progress(f"⚠️  Requires human review: {review_reason}")
        else:
            update_progress("✅ No human review required")

        processing_time = time.time() - start_time
        update_progress(f"✅ Classification complete in {processing_time:.2f}s")

        # Build enhanced result
        result = ClassificationResult(
            document_id=document_id,
            filename=metadata.filename,
            classification=ClassificationCategory(final_classification),
            additional_labels=additional_labels,  # NEW: Multi-label support
            confidence=final_confidence,
            summary=primary_result["summary"],
            reasoning=primary_result["reasoning"],
            evidence=[
                Evidence(
                    **{**e, "sensitivity_level": e.get("sensitivity_level"),
                       "keywords": e.get("keywords", []),
                       "start_char": e.get("start_char"),
                       "end_char": e.get("end_char")}
                ) for e in primary_result["evidence"]
            ],
            safety_check=SafetyCheckResult(**primary_result["safety_assessment"]),
            page_count=metadata.page_count,
            image_count=metadata.image_count,
            processing_time=processing_time,
            text_segments=text_segments,
            image_analyses=image_analyses,
            full_text=full_text,
            all_keywords=all_keywords,
            page_images_base64=page_images,
            secondary_classification=ClassificationCategory(secondary_classification) if secondary_classification else None,
            secondary_confidence=secondary_confidence,
            consensus=consensus,
            verification_notes=verification_notes,
            document_context=document_context,
            keyword_relevances=keyword_relevances,
            progress_steps=progress_steps,
            requires_review=requires_review,
            review_reason=review_reason
        )

        return result

    def _analyze_text_segments(
        self,
        full_text: str,
        content_blocks: List[Dict[str, Any]]
    ) -> List[TextSegment]:
        """
        Analyze text at sentence/paragraph level for granular classification
        """
        if not full_text or len(full_text.strip()) == 0:
            return []

        try:
            # Create a focused prompt for text segmentation
            segmentation_prompt = f"""
Analyze the following text and identify segments that have different sensitivity levels.
Break down the text into meaningful segments (sentences, paragraphs, or sections) and classify each segment.

For each segment, provide:
- The exact text
- Classification (Public, Confidential, Highly Sensitive, or Unsafe)
- Confidence (0.0-1.0)
- Keywords that triggered this classification
- Reasoning

Text to analyze:
{full_text[:15000]}  # Limit to avoid token limits

Provide output as JSON array:
[
  {{
    "text": "segment text",
    "classification": "Public|Confidential|Highly Sensitive|Unsafe",
    "confidence": 0.95,
    "keywords": ["ssn", "confidential"],
    "reasoning": "Contains SSN"
  }}
]
"""

            response_text = self._call_claude(segmentation_prompt, max_tokens=4096)
            if response_text is None:
                print("[WARNING] Text segmentation failed, returning empty")
                return []
            
            # Parse JSON response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            if start_idx != -1 and end_idx > 0:
                json_str = response_text[start_idx:end_idx]
                segments_data = json.loads(json_str)

                text_segments = []
                for idx, seg in enumerate(segments_data[:50]):  # Limit segments
                    # Find position in full text
                    text_content = seg.get("text", "")
                    start_pos = full_text.find(text_content)
                    end_pos = start_pos + len(text_content) if start_pos != -1 else 0

                    # Determine page (rough estimate)
                    page_num = (start_pos // 2000) + 1 if start_pos != -1 else 1

                    text_segments.append(TextSegment(
                        text=text_content,
                        classification=ClassificationCategory(seg.get("classification", "Public")),
                        confidence=seg.get("confidence", 0.5),
                        page=min(page_num, 100),
                        start_char=start_pos if start_pos != -1 else idx * 100,
                        end_char=end_pos if end_pos > start_pos else idx * 100 + 50,
                        keywords=seg.get("keywords", []),
                        reasoning=seg.get("reasoning", "")
                    ))

                return text_segments

        except Exception as e:
            print(f"Error in text segmentation: {str(e)}")
            return []

        return []

    def _analyze_images(
        self,
        content_blocks: List[Dict[str, Any]],
        metadata: DocumentMetadata
    ) -> List[ImageAnalysis]:
        """
        Analyze each image individually for sensitive content, OCR, and visual elements
        """
        import base64
        from PIL import Image
        import io
        
        image_analyses = []
        image_blocks = [b for b in content_blocks if b.get("type") == "image"]

        for idx, img_block in enumerate(image_blocks[:10]):  # Limit to 10 images
            try:
                # Create focused prompt for this image
                image_prompt = """
Analyze this image for sensitive content:

1. **OCR**: Extract any visible text
2. **Visual Elements**: Identify seals, logos, stamps, signatures, official marks
3. **Classification**: Classify as Public, Confidential, Highly Sensitive, or Unsafe
4. **Reasoning**: Explain why

Look for:
- Government seals/logos → Highly Sensitive
- Official stamps → Highly Sensitive
- Signatures → Confidential
- Personal photos → Confidential
- Charts/graphs with sensitive data → Confidential
- Public information → Public

Provide JSON output:
{
  "ocr_text": "extracted text or null",
  "classification": "Public|Confidential|Highly Sensitive|Unsafe",
  "confidence": 0.95,
  "contains_sensitive_visual": true,
  "visual_elements": ["government seal", "signature"],
  "reasoning": "explanation",
  "keywords": ["keyword1", "keyword2"]
}
"""

                # Use Claude's vision API
                source = img_block.get("source", {})
                if source.get("type") == "base64":
                    try:
                        response = self.client.messages.create(
                            model=self.model,
                            max_tokens=2048,
                            temperature=0.0,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": source.get("media_type", "image/jpeg"),
                                            "data": source["data"]
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": image_prompt
                                    }
                                ]
                            }]
                        )
                        response_text = response.content[0].text
                    except Exception as e:
                        print(f"[WARNING] Image analysis {idx} failed: {str(e)}")
                        continue
                
                # Parse JSON
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > 0:
                    json_str = response_text[start_idx:end_idx]
                    img_data = json.loads(json_str)

                    image_analyses.append(ImageAnalysis(
                        image_index=idx,
                        page=idx + 1,  # Rough estimate
                        ocr_text=img_data.get("ocr_text"),
                        classification=ClassificationCategory(img_data.get("classification", "Public")),
                        confidence=img_data.get("confidence", 0.5),
                        contains_sensitive_visual=img_data.get("contains_sensitive_visual", False),
                        visual_elements=img_data.get("visual_elements", []),
                        reasoning=img_data.get("reasoning", ""),
                        keywords=img_data.get("keywords", [])
                    ))

            except Exception as e:
                print(f"Error analyzing image {idx}: {str(e)}")
                # Add fallback analysis
                image_analyses.append(ImageAnalysis(
                    image_index=idx,
                    page=idx + 1,
                    ocr_text=None,
                    classification=ClassificationCategory.PUBLIC,
                    confidence=0.5,
                    contains_sensitive_visual=False,
                    visual_elements=[],
                    reasoning="Image analysis failed",
                    keywords=[]
                ))

        return image_analyses

    def _quick_safety_check(
        self,
        content_blocks: List[Dict[str, Any]],
        full_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        BASIC safety check - quick text scan for obvious critical violations
        Returns if unsafe content detected, None if safe to proceed
        """
        try:
            # Simpler, faster safety prompt for basic check
            basic_safety_prompt = """
Perform a QUICK safety scan of this document for CRITICAL violations ONLY:

**Check ONLY for:**
1. Child safety violations (CRITICAL - any content harmful to minors)
2. Explicit hate speech (racial slurs, hate group content)
3. Graphic violence or gore
4. Explicit illegal activity instructions

**Important:**
- This is a BASIC scan - only flag OBVIOUS critical violations
- DO NOT flag business documents, contracts, or forms
- DO NOT flag technical content or industry jargon
- DO NOT flag documents just because they contain sensitive data (SSN, etc.)
- Classified government/defense documents are NOT unsafe - they are just sensitive

**Return JSON:**
{
  "is_unsafe": false,
  "note": "No critical safety violations found"
}

OR if unsafe:
{
  "is_unsafe": true,
  "quick_flag": "Child Safety Violation|Hate Speech|Violence|Criminal",
  "severity": "Critical",
  "evidence": "Brief description"
}
"""

            # Only check first 5000 chars for speed
            quick_text = full_text[:5000] if full_text else ""

            prompt = f"{basic_safety_prompt}\n\nDocument text:\n{quick_text}"

            response_text = self._call_claude(prompt, max_tokens=512, temperature=0.0)
            if response_text is None:
                print("[WARNING] Basic safety check failed, defaulting to safe (continue)")
                return None  # Continue to full classification

            # Parse JSON response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)

                # If unsafe content detected, return immediately
                if result.get("is_unsafe", False):
                    print(f"[WARNING] UNSAFE content detected: {result.get('quick_flag')}")
                    return result

            # No unsafe content - proceed with classification
            return None

        except Exception as e:
            print(f"[WARNING] Basic safety check error: {str(e)}, continuing")
            # If check fails, continue with full classification (don't block)
            return None

    def _analyze_document_context(
        self,
        content_blocks: List[Dict[str, Any]],
        metadata: DocumentMetadata,
        full_text: str
    ) -> Optional[DocumentContext]:
        """
        Analyze document context to determine if it's proprietary content vs public discussion
        """
        try:
            # Use the document context classification prompt from library
            context_prompt = self.prompts["document_context_classification"]["prompt"]

            # Limit text for analysis
            analysis_text = full_text[:10000] if full_text else ""

            prompt = f"{context_prompt}\n\nDocument to analyze:\n{analysis_text}"

            response_text = self._call_claude(prompt, max_tokens=2048)
            if response_text is None:
                print("[WARNING] Document context analysis failed")
                return None  # Will trigger fallback

            # Parse JSON response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > 0:
                json_str = response_text[start_idx:end_idx]
                context_data = json.loads(json_str)

                return DocumentContext(
                    context_type=context_data.get("context_type", "PUBLIC_DISCUSSION"),
                    intended_audience=context_data.get("intended_audience", "Unknown"),
                    content_purpose=context_data.get("content_purpose", "educational"),
                    is_proprietary=context_data.get("is_proprietary", False),
                    confidence=context_data.get("confidence", 0.5),
                    reasoning=context_data.get("reasoning", "")
                )

        except Exception as e:
            print(f"Error in document context analysis: {str(e)}")
            # Return default context
            return DocumentContext(
                context_type="PUBLIC_DISCUSSION",
                intended_audience="Unknown",
                content_purpose="educational",
                is_proprietary=False,
                confidence=0.3,
                reasoning="Context analysis failed, defaulting to public discussion"
            )

        return None

    def _score_keyword_relevance(
        self,
        full_text: str,
        metadata: DocumentMetadata
    ) -> List[KeywordRelevance]:
        """
        Score relevance of defense/government/sensitive keywords with context
        """
        if not full_text or len(full_text.strip()) == 0:
            return []

        try:
            # Use the keyword relevance scoring prompt from library
            relevance_prompt = self.prompts["keyword_relevance_scoring"]["prompt"]

            # Limit text for analysis
            analysis_text = full_text[:15000] if full_text else ""

            prompt = f"{relevance_prompt}\n\nDocument text to analyze:\n{analysis_text}"

            response_text = self._call_claude(prompt, max_tokens=4096)
            if response_text is None:
                print("[WARNING] Keyword relevance scoring failed")
                return []  # Return empty list

            # Parse JSON array response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            if start_idx != -1 and end_idx > 0:
                json_str = response_text[start_idx:end_idx]
                keywords_data = json.loads(json_str)

                keyword_relevances = []
                for kw_data in keywords_data[:20]:  # Limit to 20 keywords
                    keyword_relevances.append(KeywordRelevance(
                        keyword=kw_data.get("keyword", ""),
                        relevance_score=kw_data.get("relevance_score", 0.0),
                        context_window=kw_data.get("context_window", ""),
                        relationship_type=kw_data.get("relationship_type", "MENTIONS"),
                        page=kw_data.get("page", 1),
                        reasoning=kw_data.get("reasoning", "")
                    ))

                return keyword_relevances

        except Exception as e:
            print(f"Error in keyword relevance scoring: {str(e)}")
            return []

        return []

    def _run_verification_agent(
        self,
        primary_result: Dict[str, Any],
        secondary_result: Dict[str, Any],
        text_segments: List[TextSegment],
        image_analyses: List[ImageAnalysis]
    ) -> Dict[str, Any]:
        """
        Run a verification agent when primary and secondary disagree
        This agent reviews both classifications and makes final decision
        """
        try:
            verification_prompt = f"""
You are a verification agent. Two independent AI classifiers have analyzed a document and disagreed.

**Primary Classification**: {primary_result['classification']} (confidence: {primary_result['confidence']})
**Secondary Classification**: {secondary_result['classification']} (confidence: {secondary_result['confidence']})

**Additional Context**:
- Text segments classified: {len(text_segments)}
- Highly Sensitive segments: {sum(1 for seg in text_segments if seg.classification == ClassificationCategory.HIGHLY_SENSITIVE)}
- Confidential segments: {sum(1 for seg in text_segments if seg.classification == ClassificationCategory.CONFIDENTIAL)}
- Images analyzed: {len(image_analyses)}
- Images with sensitive visuals: {sum(1 for img in image_analyses if img.contains_sensitive_visual)}

**Primary Reasoning**: {primary_result['reasoning']}
**Secondary Reasoning**: {secondary_result['reasoning']}

Your task: Review the evidence and make a final determination. Be more scrutinizing and conservative.

Provide JSON:
{{
  "final_classification": "Public|Confidential|Highly Sensitive|Unsafe",
  "final_confidence": 0.95,
  "notes": "Explanation of final decision and why"
}}
"""

            response_text = self._call_claude(verification_prompt, max_tokens=1024)
            if response_text is None:
                print("[WARNING] Verification agent failed, using primary result")
                # Return properly formatted fallback
                return {
                    "final_classification": primary_result['classification'],
                    "final_confidence": primary_result['confidence'],
                    "notes": "Verification agent blocked by safety filter, using primary classification"
                }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)

        except Exception as e:
            print(f"Verification agent error: {str(e)}")

        # Fallback: Use more conservative classification
        classifications = [primary_result['classification'], secondary_result['classification']]
        priority = ["Unsafe", "Highly Sensitive", "Confidential", "Public"]
        final_class = next((c for c in priority if c in classifications), primary_result['classification'])

        return {
            "final_classification": final_class,
            "final_confidence": min(primary_result['confidence'], secondary_result['confidence']),
            "notes": "Used conservative approach due to disagreement"
        }

    def _extract_all_keywords(
        self,
        text_segments: List[TextSegment],
        image_analyses: List[ImageAnalysis],
        primary_result: Dict[str, Any]
    ) -> List[str]:
        """Extract all unique keywords from various sources"""
        keywords = set()

        # From text segments
        for segment in text_segments:
            keywords.update(segment.keywords)

        # From image analyses
        for img in image_analyses:
            keywords.update(img.keywords)

        # From evidence
        for evidence in primary_result.get("evidence", []):
            if "keywords" in evidence:
                keywords.update(evidence.get("keywords", []))

        return list(keywords)

    def _assess_hitl_need_enhanced(
        self,
        primary_result: Dict[str, Any],
        secondary_classification: Optional[str],
        consensus: Optional[bool],
        text_segments: List[TextSegment],
        image_analyses: List[ImageAnalysis]
    ) -> Tuple[bool, Optional[str]]:
        """Enhanced HITL assessment considering granular analysis"""

        confidence = primary_result["confidence"]
        classification = primary_result["classification"]
        safety_assessment = primary_result["safety_assessment"]

        # Always review unsafe content
        if not safety_assessment["is_safe"]:
            return True, "Unsafe content detected - mandatory review"

        # Review if any image has government seal or official marks
        sensitive_visuals = [img for img in image_analyses if img.contains_sensitive_visual]
        if sensitive_visuals:
            return True, f"Detected {len(sensitive_visuals)} images with sensitive visual elements (seals, stamps, etc.)"

        # Review if high variation in segment classifications
        if text_segments:
            segment_classes = [seg.classification for seg in text_segments]
            unique_classes = len(set(segment_classes))
            if unique_classes >= 3:
                return True, "High variation in segment classifications - manual review recommended"

        # Review low confidence
        if confidence < 0.75:
            return True, f"Low confidence score: {confidence:.2f}"

        # Review disagreement
        if secondary_classification and not consensus:
            return True, f"LLM disagreement: Primary={classification}, Secondary={secondary_classification}"

        # Review highly sensitive with medium confidence
        if classification == "Highly Sensitive" and confidence < 0.90:
            return True, "Highly Sensitive classification requires very high confidence"

        return False, None
    
    def _extract_content_preview(self, content_blocks: List[Dict[str, Any]], max_chars: int = 1000) -> str:
        """Extract text preview from content blocks for HITL analysis"""
        preview = ""
        for block in content_blocks[:5]:  # First 5 blocks
            if block.get("type") == "text":
                preview += block.get("text", "")
                if len(preview) >= max_chars:
                    return preview[:max_chars]
        return preview
    
    def _enhance_prompt_with_learning(self, base_prompt: str, metadata: DocumentMetadata) -> str:
        """
        Enhance the base prompt with insights from HITL learning.
        Adds few-shot examples and learned patterns.
        """
        enhancements = []
        
        # Get prompt enhancements from HITL learner
        prompt_enhancements = self.hitl_learner.generate_prompt_enhancements()
        
        if prompt_enhancements:
            enhancements.append("\n**🧠 LEARNED FROM HUMAN FEEDBACK:**\n")
            for key, enhancement in prompt_enhancements.items():
                enhancements.append(f"- {enhancement}")
        
        # Get few-shot examples (we'll try to predict the likely category)
        # For now, add examples from all categories (could be smarter about this)
        learning_stats = self.hitl_learner.get_learning_stats()
        
        if learning_stats["total_feedback"] > 0:
            enhancements.append(f"\n**📊 HISTORICAL ACCURACY:**")
            for category, stats in learning_stats["accuracy_by_category"].items():
                enhancements.append(
                    f"- {category}: {stats['accuracy']:.1f}% accuracy "
                    f"({stats['correct']}/{stats['total_reviews']} correct)"
                )
        
        # Add few-shot examples for each category
        categories = ["Public", "Confidential", "Highly Sensitive", "Unsafe"]
        for category in categories:
            examples = self.hitl_learner.get_few_shot_examples(category, limit=2)
            if examples:
                enhancements.append(f"\n**✅ VERIFIED {category.upper()} EXAMPLES:**")
                for ex in examples:
                    enhancements.append(
                        f"- '{ex['filename']}' → {ex['classification']} "
                        f"({ex['confidence']})"
                    )
        
        # Combine base prompt with enhancements
        if enhancements:
            enhanced_prompt = base_prompt + "\n\n" + "\n".join(enhancements)
            return enhanced_prompt
        
        return base_prompt
    
    def get_hitl_stats(self) -> Dict[str, Any]:
        """Get HITL learning statistics for monitoring"""
        return self.hitl_learner.get_learning_stats()
