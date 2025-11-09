/**
 * TypeScript types matching backend schemas
 */

export enum ClassificationCategory {
  PUBLIC = "Public",
  CONFIDENTIAL = "Confidential",
  HIGHLY_SENSITIVE = "Highly Sensitive",
  UNSAFE = "Unsafe"
}

export enum SecondaryLabel {
  // Safety-related
  SAFE = "Safe",
  UNSAFE = "Unsafe",
  
  // Content-related
  PII_DETECTED = "PII Detected",
  GOVERNMENT_CONTENT = "Government Content",
  DEFENSE_RELATED = "Defense Related",
  PROPRIETARY = "Proprietary",
  TECHNICAL_SPECS = "Technical Specifications",
  
  // Context-related
  INTERNAL_USE = "Internal Use Only",
  EXTERNAL_SHARING = "External Sharing",
  MARKETING = "Marketing Material",
  LEGAL_DOCUMENT = "Legal Document",
  FINANCIAL_DATA = "Financial Data",
  
  // Additional flags
  MULTI_CLASSIFICATION = "Multiple Classifications",
  REQUIRES_REVIEW = "Requires Review",
  LOW_CONFIDENCE = "Low Confidence"
}

export enum SafetyFlag {
  CHILD_SAFETY = "Child Safety Violation",
  HATE_SPEECH = "Hate Speech",
  VIOLENCE = "Violence",
  EXPLOITATIVE = "Exploitative Content",
  CRIMINAL = "Criminal Activity",
  POLITICAL = "Political News",
  CYBER_THREAT = "Cyber Threat",
  THREATS = "Threats",
  HARASSMENT = "Harassment",
  PROFANITY = "Profanity",
  NONE = "Safe"
}

export interface Evidence {
  page: number | null;
  region: string | null;
  quote: string | null;
  reasoning: string;
  image_index?: number | null;
  sensitivity_level?: string | null;
  keywords?: string[];
  start_char?: number | null;
  end_char?: number | null;
}

export interface TextSegment {
  text: string;
  classification: ClassificationCategory;
  confidence: number;
  page: number;
  start_char: number;
  end_char: number;
  keywords: string[];
  reasoning: string;
}

export interface ImageAnalysis {
  image_index: number;
  page: number;
  ocr_text: string | null;
  classification: ClassificationCategory;
  confidence: number;
  contains_sensitive_visual: boolean;
  visual_elements: string[];
  reasoning: string;
  keywords: string[];
}

export interface SafetyCheckResult {
  is_safe: boolean;
  flags: SafetyFlag[];
  details: string;
  confidence: number;
}

export interface DocumentContext {
  context_type: string; // INTERNAL, EXTERNAL, PROPRIETARY, PUBLIC_DISCUSSION, BUSINESS, NEWS
  intended_audience: string;
  content_purpose: string; // technical_specs, marketing, news_article, contract, internal_communication, educational
  is_proprietary: boolean;
  confidence: number;
  reasoning: string;
}

export interface KeywordRelevance {
  keyword: string;
  relevance_score: number; // 0.0-1.0: 0.0=incidental, 0.5=discusses, 1.0=is the content
  context_window: string; // Surrounding text (±50 words)
  relationship_type: string; // IS, DISCUSSES, MENTIONS
  page: number;
  reasoning: string;
}

export interface ClassificationResult {
  document_id: string;
  filename: string;
  classification: ClassificationCategory;
  
  // Multi-label support
  secondary_labels?: SecondaryLabel[] | string[];  // NEW: Secondary classification labels
  additional_labels?: string[];  // Freeform additional tags
  label_confidence?: Record<string, number>;  // NEW: Confidence for each label
  
  confidence: number;
  summary: string;
  reasoning: string;
  evidence: Evidence[];
  safety_check: SafetyCheckResult;
  page_count: number;
  image_count: number;
  processing_time: number;
  secondary_classification?: ClassificationCategory;
  secondary_confidence?: number;
  consensus?: boolean;
  requires_review: boolean;
  review_reason?: string;
  
  // Enhanced fields
  text_segments?: TextSegment[];
  image_analyses?: ImageAnalysis[];
  full_text?: string;
  all_keywords?: string[];
  page_images_base64?: string[];
  verification_notes?: string;

  // Context-aware classification fields
  document_context?: DocumentContext;
  keyword_relevances?: KeywordRelevance[];

  // Progress tracking
  progress_steps?: string[];
  
  // NEW: Human review tracking
  human_reviewed?: boolean;
  reviewed_by?: string;
  reviewed_at?: string;
  human_corrected?: boolean;
}

export interface DocumentMetadata {
  filename: string;
  file_size: number;
  page_count: number;
  image_count: number;
  is_legible: boolean;
  legibility_score?: number;
  format: string;
  warnings: string[];
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  file_size: number;
  status: string;
  message: string;
  metadata?: DocumentMetadata;
}

export interface HITLFeedback {
  document_id: string;
  reviewer_id: string;
  approved: boolean;
  corrected_classification?: ClassificationCategory;
  feedback_notes: string;
  timestamp: string;
}

export interface ReviewQueueItem {
  document_id: string;
  filename: string;
  classification: ClassificationCategory;
  confidence: number;
  review_reason?: string;
  safety_check: SafetyCheckResult;
  submitted_at: number;
}

export interface BatchProcessRequest {
  document_ids: string[];
  enable_dual_verification: boolean;
  auto_approve_threshold: number;
}

export interface BatchProcessStatus {
  batch_id: string;
  total_documents: number;
  processed: number;
  in_progress: number;
  failed: number;
  completed: boolean;
  results: ClassificationResult[];
}
