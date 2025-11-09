"""
Pydantic models for request/response schemas
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ClassificationCategory(str, Enum):
    """Document classification categories - PRIMARY LABELS"""
    PUBLIC = "Public"
    CONFIDENTIAL = "Confidential"
    HIGHLY_SENSITIVE = "Highly Sensitive"
    UNSAFE = "Unsafe"


class SecondaryLabel(str, Enum):
    """Secondary classification labels - can have multiple per document"""
    # Safety-related
    SAFE = "Safe"
    UNSAFE = "Unsafe"
    
    # Content-related
    PII_DETECTED = "PII Detected"
    GOVERNMENT_CONTENT = "Government Content"
    DEFENSE_RELATED = "Defense Related"
    PROPRIETARY = "Proprietary"
    TECHNICAL_SPECS = "Technical Specifications"
    
    # Context-related
    INTERNAL_USE = "Internal Use Only"
    EXTERNAL_SHARING = "External Sharing"
    MARKETING = "Marketing Material"
    LEGAL_DOCUMENT = "Legal Document"
    FINANCIAL_DATA = "Financial Data"
    
    # Additional flags
    MULTI_CLASSIFICATION = "Multiple Classifications"
    REQUIRES_REVIEW = "Requires Review"
    LOW_CONFIDENCE = "Low Confidence"


class SafetyFlag(str, Enum):
    """Safety concern types"""
    CHILD_SAFETY = "Child Safety Violation"
    HATE_SPEECH = "Hate Speech"
    VIOLENCE = "Violence"
    EXPLOITATIVE = "Exploitative Content"
    CRIMINAL = "Criminal Activity"
    POLITICAL = "Political News"
    CYBER_THREAT = "Cyber Threat"
    THREATS = "Threats"
    HARASSMENT = "Harassment"
    PROFANITY = "Profanity"
    NONE = "Safe"


class Evidence(BaseModel):
    """Evidence for classification decision"""
    page: Optional[int] = Field(None, description="Page number (1-indexed)")
    region: Optional[str] = Field(None, description="Description of region or field")
    quote: Optional[str] = Field(None, description="Relevant quote or description")
    reasoning: str = Field(..., description="Why this evidence supports the classification")
    image_index: Optional[int] = Field(None, description="Image index if evidence is from an image")
    sensitivity_level: Optional[str] = Field(None, description="Sensitivity level of this specific evidence")
    keywords: List[str] = Field(default_factory=list, description="Keywords that triggered this classification")
    start_char: Optional[int] = Field(None, description="Start character position in text")
    end_char: Optional[int] = Field(None, description="End character position in text")


class TextSegment(BaseModel):
    """Labeled text segment with sensitivity classification"""
    text: str = Field(..., description="The text segment")
    classification: ClassificationCategory = Field(..., description="Classification for this segment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this segment's classification")
    page: int = Field(..., description="Page number where this text appears")
    start_char: int = Field(..., description="Start character position")
    end_char: int = Field(..., description="End character position")
    keywords: List[str] = Field(default_factory=list, description="Trigger keywords in this segment")
    reasoning: str = Field(..., description="Why this segment has this classification")


class ImageAnalysis(BaseModel):
    """Analysis result for an image within the document"""
    image_index: int = Field(..., description="Index of the image")
    page: int = Field(..., description="Page where image appears")
    ocr_text: Optional[str] = Field(None, description="Text extracted from image via OCR")
    classification: ClassificationCategory = Field(..., description="Classification of image content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in classification")
    contains_sensitive_visual: bool = Field(default=False, description="Contains sensitive visual elements")
    visual_elements: List[str] = Field(default_factory=list, description="Detected visual elements (seals, logos, etc)")
    reasoning: str = Field(..., description="Why this image has this classification")
    keywords: List[str] = Field(default_factory=list, description="Keywords from OCR or visual detection")


class SafetyCheckResult(BaseModel):
    """Result of content safety check"""
    is_safe: bool = Field(..., description="Whether content is safe")
    flags: List[SafetyFlag] = Field(default_factory=list, description="Safety concerns found")
    details: str = Field(..., description="Detailed explanation of safety assessment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in safety assessment")


class DocumentContext(BaseModel):
    """Document context classification for semantic understanding"""
    context_type: str = Field(..., description="INTERNAL, EXTERNAL, PROPRIETARY, PUBLIC_DISCUSSION, BUSINESS, NEWS")
    intended_audience: str = Field(..., description="Who is this document for? (e.g., employees, public, partners)")
    content_purpose: str = Field(..., description="Purpose of document (e.g., technical_specs, marketing, news_article, contract)")
    is_proprietary: bool = Field(default=False, description="Is this proprietary content or discussion about a topic?")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in context classification")
    reasoning: str = Field(..., description="Why this context classification was chosen")


class KeywordRelevance(BaseModel):
    """Relevance scoring for defense/government/sensitive keywords"""
    keyword: str = Field(..., description="The keyword or phrase detected")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="0.0=incidental mention, 0.5=discusses topic, 1.0=is the content")
    context_window: str = Field(..., description="Surrounding text context (±50 words)")
    relationship_type: str = Field(..., description="IS (document is this), DISCUSSES (working with), MENTIONS (passing reference)")
    page: int = Field(..., description="Page where keyword appears")
    reasoning: str = Field(..., description="Why this relevance score was assigned")


class ClassificationResult(BaseModel):
    """Complete classification result for a document"""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    classification: ClassificationCategory = Field(..., description="Primary classification")
    
    # Enhanced multi-label support
    secondary_labels: List[SecondaryLabel] = Field(
        default_factory=list, 
        description="Secondary labels (e.g., Safe, PII Detected, Government Content)"
    )
    additional_labels: List[str] = Field(
        default_factory=list, 
        description="Additional freeform classification tags"
    )
    label_confidence: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence score for each label (primary + secondary)"
    )
    
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for primary classification")
    summary: str = Field(..., description="Summary of the document")
    reasoning: str = Field(..., description="Detailed reasoning for classification")
    evidence: List[Evidence] = Field(default_factory=list, description="Supporting evidence")
    safety_check: SafetyCheckResult = Field(..., description="Safety assessment")

    # Document metadata
    page_count: int = Field(..., description="Number of pages")
    image_count: int = Field(..., description="Number of images")
    processing_time: float = Field(..., description="Processing time in seconds")

    # Enhanced granular analysis
    text_segments: List[TextSegment] = Field(default_factory=list, description="Labeled text segments")
    image_analyses: List[ImageAnalysis] = Field(default_factory=list, description="Per-image analysis")
    full_text: str = Field(default="", description="Complete extracted text")
    all_keywords: List[str] = Field(default_factory=list, description="All detected keywords")
    page_images_base64: List[str] = Field(default_factory=list, description="Base64 encoded page images for preview")

    # Optional dual verification
    secondary_classification: Optional[ClassificationCategory] = Field(None, description="Secondary LLM classification")
    secondary_confidence: Optional[float] = Field(None, description="Secondary confidence score")
    consensus: Optional[bool] = Field(None, description="Whether both LLMs agree")
    verification_notes: Optional[str] = Field(None, description="Notes from verification process")

    # Context-aware classification
    document_context: Optional[DocumentContext] = Field(None, description="Document context classification")
    keyword_relevances: List[KeywordRelevance] = Field(default_factory=list, description="Relevance scores for sensitive keywords")

    # Progress tracking
    progress_steps: List[str] = Field(default_factory=list, description="Steps completed during classification process")

    # HITL
    requires_review: bool = Field(default=False, description="Whether human review is needed")
    review_reason: Optional[str] = Field(None, description="Why review is needed")
    
    # NEW: Human review tracking
    human_reviewed: bool = Field(default=False, description="Whether this was reviewed by a human")
    reviewed_by: Optional[str] = Field(None, description="Reviewer ID")
    reviewed_at: Optional[str] = Field(None, description="Timestamp of review")
    human_corrected: bool = Field(default=False, description="Whether human changed the classification")


class DocumentMetadata(BaseModel):
    """Pre-processing document metadata"""
    filename: str
    file_size: int
    page_count: int
    image_count: int
    is_legible: bool
    legibility_score: Optional[float] = None
    format: str
    warnings: List[str] = Field(default_factory=list)


class HITLFeedback(BaseModel):
    """Human-in-the-loop feedback with enhanced context for learning"""
    document_id: str
    reviewer_id: str
    approved: bool
    corrected_classification: Optional[ClassificationCategory] = None
    original_classification: Optional[str] = None
    feedback_notes: str
    timestamp: str
    
    # NEW: Enhanced context for learning
    document_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full context of the document (filename, page count, summary, key evidence)"
    )
    reasoning_for_correction: Optional[str] = Field(
        default=None,
        description="Detailed reasoning why the human made this correction"
    )
    key_indicators: Optional[List[str]] = Field(
        default_factory=list,
        description="Key words/phrases that should trigger this classification"
    )
    similar_document_patterns: Optional[List[str]] = Field(
        default_factory=list,
        description="Patterns to look for in similar documents"
    )
    
    # NEW: Machine learning instruction
    learning_instruction: Optional[str] = Field(
        default=None,
        description="Clear instruction for the model on what to learn from this correction"
    )


class BatchProcessRequest(BaseModel):
    """Request for batch processing"""
    document_ids: List[str]
    enable_dual_verification: bool = False
    auto_approve_threshold: float = 0.9


class BatchProcessStatus(BaseModel):
    """Status of batch processing"""
    batch_id: str
    total_documents: int
    processed: int
    in_progress: int
    failed: int
    completed: bool
    results: List[ClassificationResult] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response after file upload"""
    document_id: str
    filename: str
    file_size: int
    status: str
    message: str
    metadata: Optional[DocumentMetadata] = None
