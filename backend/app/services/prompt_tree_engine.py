"""
Dynamic Prompt Tree Engine - Adaptive classification prompts based on document characteristics
"""
import re
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import json

from app.models.schemas import DocumentMetadata


class PromptTreeNode:
    """Represents a node in the dynamic prompt tree"""
    
    def __init__(
        self,
        prompt_key: str,
        condition: Optional[callable] = None,
        priority: int = 0,
        children: Optional[List['PromptTreeNode']] = None
    ):
        self.prompt_key = prompt_key
        self.condition = condition  # Function that returns True if this node should be used
        self.priority = priority  # Higher priority = executed first
        self.children = children or []


class PromptTreeEngine:
    """
    Builds adaptive prompt trees based on document characteristics.
    Dynamically selects and sequences prompts for optimal classification.
    """
    
    # Defense/military keywords for detection
    DEFENSE_KEYWORDS = {
        'classified', 'secret', 'confidential', 'proprietary',
        'fighter', 'aircraft', 'stealth', 'weapon', 'military',
        'defense', 'tactical', 'strategic', 'missile', 'radar',
        'sensor', 'prototype', 'blueprint', 'specification',
        'clearance', 'restricted', 'controlled', 'export'
    }
    
    # PII data patterns - look for actual data, not just words
    # More flexible patterns to catch various formats
    PII_PATTERNS = {
        'ssn': r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b|\b\d{9}\b',  # SSN: 123-45-6789, 123456789, or any 9 digits
        'phone': r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',  # Phone: various formats
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b|\b\d{13,16}\b',  # Credit card: any 13-16 digit sequence
        'date_of_birth': r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b|\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b',  # DOB: MM/DD/YYYY or DD/MM/YYYY
        'account_number': r'\b(?:acct|account|a/c|#)[:\s#]*\d{6,}\b|\b[A-Z]{2,4}\d{6,}\b',  # Account numbers with/without labels
        'passport': r'\b[A-Z]{1,2}\d{6,9}\b',  # Passport: like US1234567
        'license': r'\b[A-Z]{1,2}\d{5,8}\b|\b\d{8,10}\b',  # Driver's license various formats
    }
    
    # Form-specific indicators (actual forms, not just words)
    FORM_INDICATORS = {
        'employee id', 'employee number', 'student id',
        'patient id', 'case number', 'reference number',
        'application form', 'enrollment form', 'registration form'
    }
    
    # Government content markers
    GOVERNMENT_MARKERS = {
        '.gov', 'federal', 'government', 'agency',
        'department of', 'bureau', 'administration',
        'congressional', 'senate', 'house of representatives',
        'executive order', 'public law', 'regulation'
    }
    
    def __init__(self, prompt_library: Dict[str, Any]):
        """Initialize with loaded prompt library"""
        self.prompts = prompt_library
        self.analysis_cache = {}
    
    def build_prompt_tree(
        self,
        metadata: DocumentMetadata,
        content_preview: str = ""
    ) -> List[str]:
        """
        Build a dynamic prompt sequence based on document characteristics.
        
        Returns list of prompt keys in execution order.
        """
        prompt_sequence = []
        detected_features = self._analyze_document_features(metadata, content_preview)
        
        # Stage 1: Pre-classification analysis (ALWAYS)
        prompt_sequence.append("pre_classification_analysis")
        
        # Stage 2: Quick safety screening (ALWAYS)
        prompt_sequence.append("quick_safety_check")
        
        # Stage 3: Conditional deep analysis based on detected features
        
        # Branch 1: PII Detection (forms, personal info)
        if detected_features['has_pii_indicators']:
            prompt_sequence.append("pii_detection")
            prompt_sequence.append("pii_sensitivity_assessment")
        
        # Branch 2: Defense/Proprietary Content
        if detected_features['has_defense_keywords']:
            prompt_sequence.append("proprietary_detection")
            prompt_sequence.append("keyword_relevance_scoring")
            
            # Sub-branch: Technical specifications
            if detected_features['has_technical_content']:
                prompt_sequence.append("technical_specification_analysis")
        
        # Branch 3: Government Content
        if detected_features['has_government_markers']:
            prompt_sequence.append("document_context_classification")
            prompt_sequence.append("government_source_verification")
        
        # Branch 4: Marketing/Public Content
        if detected_features['has_marketing_indicators']:
            prompt_sequence.append("marketing_content_analysis")
        
        # Branch 5: Multiple images (visual content heavy)
        if metadata.image_count > 5:
            prompt_sequence.append("visual_content_analysis")
        
        # Stage 4: Classification decision (ALWAYS)
        prompt_sequence.append("classification_decision")
        
        # Stage 5: Evidence extraction with page citations (ALWAYS)
        prompt_sequence.append("evidence_extraction")
        
        # Stage 6: Multi-label detection (check for multiple violations)
        if detected_features['potential_multi_label']:
            prompt_sequence.append("multi_label_detection")
        
        # Stage 7: Final confidence assessment (ALWAYS)
        prompt_sequence.append("confidence_assessment")
        
        # Cache the analysis for this document
        self.analysis_cache[metadata.filename] = detected_features
        
        return prompt_sequence
    
    def _analyze_document_features(
        self,
        metadata: DocumentMetadata,
        content_preview: str
    ) -> Dict[str, Any]:
        """
        Analyze document to detect features that guide prompt tree construction.
        """
        features = {
            'has_pii_indicators': False,
            'has_defense_keywords': False,
            'has_government_markers': False,
            'has_marketing_indicators': False,
            'has_technical_content': False,
            'potential_multi_label': False,
            'document_type': 'unknown',
            'sensitivity_score': 0.0
        }
        
        # Analyze filename
        filename_lower = metadata.filename.lower()
        
        # Check for PII indicators
        if any(indicator in filename_lower for indicator in ['application', 'form', 'personal', 'employee']):
            features['has_pii_indicators'] = True
        
        # Check content preview if available
        if content_preview:
            content_lower = content_preview.lower()
            
            # PII detection - look for ACTUAL data patterns, not just words
            pii_data_found = False
            for pattern_name, pattern in self.PII_PATTERNS.items():
                if re.search(pattern, content_preview, re.IGNORECASE):
                    pii_data_found = True
                    break
            
            # Also check for form indicators (multiple form fields)
            form_count = sum(1 for indicator in self.FORM_INDICATORS if indicator in content_lower)
            
            # Only flag as PII if we found actual data patterns OR it's clearly a form with multiple fields
            if pii_data_found or form_count >= 2:
                features['has_pii_indicators'] = True
                features['sensitivity_score'] += 30
            
            # Defense keywords
            defense_count = sum(1 for keyword in self.DEFENSE_KEYWORDS if keyword in content_lower)
            if defense_count >= 3:
                features['has_defense_keywords'] = True
                features['sensitivity_score'] += 40
            
            # Government markers
            gov_count = sum(1 for marker in self.GOVERNMENT_MARKERS if marker in content_lower)
            if gov_count >= 1:
                features['has_government_markers'] = True
                features['sensitivity_score'] += 20
            
            # Marketing indicators
            marketing_terms = ['promote', 'advertis', 'campaign', 'launch', 'product', 'sale', 'marketing']
            marketing_count = sum(1 for term in marketing_terms if term in content_lower)
            if marketing_count >= 3:
                features['has_marketing_indicators'] = True
                features['sensitivity_score'] -= 10  # Lower sensitivity
            
            # Technical content
            technical_terms = ['specification', 'blueprint', 'schematic', 'technical', 'diagram', 'part number']
            technical_count = sum(1 for term in technical_terms if term in content_lower)
            if technical_count >= 2:
                features['has_technical_content'] = True
                features['sensitivity_score'] += 25
            
            # Multi-label potential (conflicting indicators)
            if features['has_defense_keywords'] and features['has_marketing_indicators']:
                features['potential_multi_label'] = True
            
            if features['has_pii_indicators'] and (features['has_defense_keywords'] or features['has_government_markers']):
                features['potential_multi_label'] = True
        
        # Document type inference
        if features['has_marketing_indicators'] and not features['has_pii_indicators']:
            features['document_type'] = 'marketing'
        elif features['has_pii_indicators'] and 'application' in filename_lower:
            features['document_type'] = 'form_with_pii'
        elif features['has_defense_keywords'] and features['has_technical_content']:
            features['document_type'] = 'technical_defense'
        elif features['has_government_markers']:
            features['document_type'] = 'government'
        elif 'memo' in filename_lower or 'internal' in filename_lower:
            features['document_type'] = 'internal_memo'
        
        return features
    
    def get_prompt_content(self, prompt_key: str) -> str:
        """Get the actual prompt text for a given key"""
        # Map prompt keys to actual prompts in library
        prompt_map = {
            "pre_classification_analysis": self.prompts.get("pre_classification", {}).get("system_instructions", ""),
            "quick_safety_check": self.prompts.get("safety_assessment", {}).get("instructions", ""),
            "pii_detection": self.prompts.get("pii_detection", {}).get("instructions", ""),
            "pii_sensitivity_assessment": "Assess the sensitivity level of detected PII.",
            "proprietary_detection": self.prompts.get("proprietary_detection", {}).get("instructions", ""),
            "keyword_relevance_scoring": self.prompts.get("keyword_relevance", {}).get("scoring_criteria", ""),
            "technical_specification_analysis": "Analyze technical specifications and part numbers for sensitivity.",
            "document_context_classification": self.prompts.get("document_context", {}).get("instructions", ""),
            "government_source_verification": "Verify if content originates from government sources (.gov domains).",
            "marketing_content_analysis": "Analyze if this is primarily marketing/promotional content.",
            "visual_content_analysis": "Analyze visual elements for sensitive information.",
            "classification_decision": self.prompts.get("classification_decision", {}).get("instructions", ""),
            "evidence_extraction": self.prompts.get("evidence_extraction", {}).get("instructions", ""),
            "multi_label_detection": self.prompts.get("multi_label", {}).get("instructions", ""),
            "confidence_assessment": "Provide confidence score (0.0-1.0) for the classification."
        }
        
        return prompt_map.get(prompt_key, f"Execute {prompt_key}")
    
    def build_combined_prompt(
        self,
        prompt_sequence: List[str],
        metadata: DocumentMetadata
    ) -> str:
        """
        Build a single comprehensive prompt from the sequence.
        """
        prompt_parts = []
        
        # Add context about the document
        prompt_parts.append(f"**DOCUMENT ANALYSIS REQUEST**")
        prompt_parts.append(f"Filename: {metadata.filename}")
        prompt_parts.append(f"Pages: {metadata.page_count}")
        prompt_parts.append(f"Images: {metadata.image_count}")
        prompt_parts.append("")
        
        # Get detected features
        features = self.analysis_cache.get(metadata.filename, {})
        if features:
            prompt_parts.append("**DETECTED FEATURES:**")
            if features.get('has_pii_indicators'):
                prompt_parts.append("- Contains PII indicators (forms, personal data)")
            if features.get('has_defense_keywords'):
                prompt_parts.append("- Contains defense/military keywords")
            if features.get('has_government_markers'):
                prompt_parts.append("- Contains government content markers")
            if features.get('has_technical_content'):
                prompt_parts.append("- Contains technical specifications")
            prompt_parts.append(f"- Document type: {features.get('document_type', 'unknown')}")
            prompt_parts.append(f"- Sensitivity score: {features.get('sensitivity_score', 0)}")
            prompt_parts.append("")
        
        # Add the analysis pipeline
        prompt_parts.append("**ANALYSIS PIPELINE:**")
        prompt_parts.append("Execute the following analysis steps in order:")
        prompt_parts.append("")
        
        for i, prompt_key in enumerate(prompt_sequence, 1):
            prompt_content = self.get_prompt_content(prompt_key)
            prompt_parts.append(f"**Step {i}: {prompt_key.replace('_', ' ').title()}**")
            prompt_parts.append(prompt_content)
            prompt_parts.append("")
        
        # Add CRITICAL JSON-only output requirement
        prompt_parts.append("=" * 80)
        prompt_parts.append("**🚨 CRITICAL OUTPUT REQUIREMENT 🚨**")
        prompt_parts.append("=" * 80)
        prompt_parts.append("")
        prompt_parts.append("You MUST respond with ONLY valid JSON. No additional text before or after.")
        prompt_parts.append("Do NOT include explanations, analysis steps, or commentary outside the JSON.")
        prompt_parts.append("Do NOT start with phrases like 'I'll proceed with...' or 'Let me analyze...'")
        prompt_parts.append("")
        prompt_parts.append("**REQUIRED JSON FORMAT:**")
        prompt_parts.append("""
{
  "classification": "Public|Confidential|Highly Sensitive|Unsafe",
  "additional_labels": ["Array of strings like 'Government Content', 'Defense Related'"],
  "confidence": 0.95,
  "summary": "Brief 2-3 sentence summary",
  "reasoning": "Detailed explanation referencing specific findings",
  "evidence": [
    {
      "page": 1,
      "region": "Description of location",
      "quote": "Relevant quote",
      "reasoning": "Why this supports classification"
    }
  ],
  "safety_assessment": {
    "is_safe": true,
    "flags": ["Safe"],
    "details": "Safety assessment explanation",
    "confidence": 0.98
  }
}
""")
        prompt_parts.append("")
        prompt_parts.append("START YOUR RESPONSE WITH THE OPENING BRACE { AND END WITH CLOSING BRACE }")
        prompt_parts.append("=" * 80)
        
        return "\n".join(prompt_parts)
    
    def get_adaptive_insights(self, metadata: DocumentMetadata) -> Dict[str, Any]:
        """
        Get insights about how the prompt tree was adapted for this document.
        Useful for debugging and transparency.
        """
        features = self.analysis_cache.get(metadata.filename, {})
        
        return {
            "document_type": features.get('document_type', 'unknown'),
            "detected_features": [k for k, v in features.items() if isinstance(v, bool) and v],
            "sensitivity_score": features.get('sensitivity_score', 0),
            "recommended_review": features.get('sensitivity_score', 0) >= 50
        }
