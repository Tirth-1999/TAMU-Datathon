/**
 * Classification Result Card - Modern SaaS Design
 *
 * Displays classification results with mobile-optimized layout
 * and design system components.
 */
import React, { useState } from 'react';
import {
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  Eye,
  BarChart3,
  Trash2,
  ChevronDown,
  ChevronUp,
  ImageIcon,
  XCircle,
} from 'lucide-react';
import type { ClassificationResult } from '../types/classification';
import {
  getConfidenceColor,
  formatConfidence,
  formatProcessingTime,
  cn,
} from '../lib/utils';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { StatusBadge } from './ui/StatusBadge';

interface ClassificationCardProps {
  result: ClassificationResult;
  onViewDetails?: () => void;
  onReview?: () => void;
  onDelete?: () => void;
}

export const ClassificationCard: React.FC<ClassificationCardProps> = ({
  result,
  onViewDetails,
  onReview,
  onDelete,
}) => {
  const [showProgress, setShowProgress] = useState(false);
  const confidenceColorClass = getConfidenceColor(result.confidence);
  
  // Check if this was human-reviewed
  const isHumanReviewed = result.human_reviewed || result.reviewed_by;
  const wasHumanCorrected = result.human_corrected;

  return (
    <div className={cn(
      "card overflow-hidden group hover:shadow-md transition-shadow relative",
      // Add special styling for human-reviewed documents
      isHumanReviewed && "ring-2 ring-purple-300 bg-gradient-to-br from-purple-50 to-pink-50"
    )}>
      
      {/* Header - Mobile optimized */}
      <div className={cn(
        "px-4 sm:px-6 py-4 sm:py-5 border-b border-gray-200 relative",
        isHumanReviewed ? "bg-gradient-to-r from-purple-100 to-pink-100" : "bg-gray-50"
      )}>
        {/* Human Review Badge - Intelligent Positioning */}
        {isHumanReviewed && (
          <div className="absolute top-2 left-2 z-10">
            <Badge
              variant="info"
              className="bg-gradient-to-r from-purple-600 to-pink-600 text-white text-[10px] font-bold px-2 py-0.5 shadow-md"
            >
              {wasHumanCorrected ? "✓ CORRECTED" : "✓ REVIEWED"}
            </Badge>
          </div>
        )}
        
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="flex items-start gap-3 sm:gap-4 flex-1 min-w-0">
            {/* Icon - smaller on mobile */}
            <div className="flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 bg-gray-900 rounded-lg flex items-center justify-center">
              <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 truncate">
                {result.filename}
              </h3>
              <div className="flex items-center gap-2 sm:gap-3 mt-1 text-xs sm:text-sm text-gray-600 flex-wrap">
                <span className="flex items-center gap-1">
                  <FileText className="h-3 w-3 flex-shrink-0" />
                  <span>{result.page_count} pages</span>
                </span>
                <span className="hidden sm:inline">•</span>
                <span className="flex items-center gap-1">
                  <ImageIcon className="h-3 w-3 flex-shrink-0" />
                  <span>{result.image_count} images</span>
                </span>
              </div>
            </div>
          </div>

          {/* Classification Labels - Redesigned for Better Visibility */}
          <div className="flex flex-col gap-2 items-end">
            {/* Primary Classification - Most Prominent */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Classification</span>
              <StatusBadge 
                status={result.classification} 
                className="text-base font-bold px-4 py-2 shadow-lg" 
              />
            </div>
            
            {/* Safety Label - Distinct from Primary */}
            {result.safety_check && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Safety</span>
                <Badge
                  variant={result.safety_check.is_safe ? 'success' : 'error'}
                  className="text-sm font-bold px-3 py-1.5 shadow-md"
                  icon={result.safety_check.is_safe ? 
                    <CheckCircle className="h-3.5 w-3.5" /> : 
                    <AlertTriangle className="h-3.5 w-3.5" />
                  }
                >
                  {result.safety_check.is_safe ? 'Safe' : 'Unsafe'}
                </Badge>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Additional Tags Row - Below header, separate section */}
      {result.additional_labels && result.additional_labels.length > 0 && (
        <div className="px-4 sm:px-6 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100">
          <div className="flex items-start gap-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide pt-1 flex-shrink-0">
              Tags:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {result.additional_labels.map((label, index) => (
                <Badge
                  key={index}
                  variant="info"
                  className="text-xs font-medium px-2.5 py-1 bg-white border border-blue-200 text-blue-700 shadow-sm"
                >
                  {label}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Body - Mobile responsive spacing */}
      <div className="px-4 sm:px-6 py-4 sm:py-5 space-y-4 sm:space-y-5">
        {/* Summary */}
        <div className="bg-blue-50 p-3 sm:p-4 rounded-lg border-l-4 border-blue-500">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-blue-600 flex-shrink-0" />
            <h4 className="text-sm font-semibold text-gray-900">Summary</h4>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{result.summary}</p>
        </div>

        {/* Metrics Grid - 1 col on mobile, 2 on desktop */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          {/* Confidence */}
          <div className="flex items-center gap-3 p-3 sm:p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="p-2 bg-green-100 rounded-lg flex-shrink-0">
              <BarChart3 className="h-5 w-5 text-green-600" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-600 mb-0.5">Confidence</p>
              <p className={cn('text-base sm:text-lg font-bold truncate', confidenceColorClass)}>
                {formatConfidence(result.confidence)}
              </p>
            </div>
          </div>

          {/* Processing Time */}
          <div className="flex items-center gap-3 p-3 sm:p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="p-2 bg-blue-100 rounded-lg flex-shrink-0">
              <Clock className="h-5 w-5 text-blue-600" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-600 mb-0.5">Processing Time</p>
              <p className="text-base sm:text-lg font-bold text-gray-900 truncate">
                {formatProcessingTime(result.processing_time)}
              </p>
            </div>
          </div>
        </div>

        {/* Safety Details - Only show if there are specific flags or important details */}
        {(result.safety_check && !result.safety_check.is_safe && result.safety_check.flags.length > 0) && (
          <div className="p-3 sm:p-4 rounded-lg border-2 bg-red-50 border-red-200">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-red-600 flex-shrink-0" />
              <h4 className="text-sm font-semibold text-gray-900">Safety Concerns Detected</h4>
            </div>

            <div className="flex flex-wrap gap-1 sm:gap-2 mb-2">
              {result.safety_check.flags.map((flag, idx) => (
                <Badge
                  key={idx}
                  variant="error"
                  icon={<XCircle className="h-3 w-3" />}
                >
                  {flag}
                </Badge>
              ))}
            </div>
            <p className="text-xs sm:text-sm text-gray-700 leading-relaxed">{result.safety_check.details}</p>
          </div>
        )}

        {/* Dual Verification (if enabled) - Remove emojis */}
        {result.secondary_classification && (
          <div className="card p-3 sm:p-4 bg-blue-50 border-l-4 border-blue-500">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4 text-blue-600 flex-shrink-0" />
              <h4 className="text-xs sm:text-sm font-semibold text-gray-900">
                Triple AI Verification
              </h4>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs sm:text-sm">
              <span className="text-gray-700">
                Secondary: <span className="font-semibold">{result.secondary_classification}</span> ({formatConfidence(result.secondary_confidence || 0)})
              </span>
              <Badge
                variant={result.consensus ? 'success' : 'warning'}
                icon={result.consensus ? <CheckCircle className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
              >
                {result.consensus ? 'Consensus' : 'Disagreement'}
              </Badge>
            </div>
          </div>
        )}

        {/* Review Status */}
        {result.requires_review && (
          <div className="card p-3 sm:p-4 bg-yellow-50 border-l-4 border-yellow-500">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <h4 className="text-xs sm:text-sm font-semibold text-yellow-900 mb-1">
                  Human Review Required
                </h4>
                <p className="text-xs sm:text-sm text-yellow-700 leading-relaxed">{result.review_reason}</p>
              </div>
            </div>
          </div>
        )}

        {/* Evidence Count */}
        {result.evidence && result.evidence.length > 0 && (
          <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-gray-50 rounded-lg border border-gray-200">
            <Shield className="h-4 w-4 text-gray-700 flex-shrink-0" />
            <span className="text-xs sm:text-sm text-gray-700">
              <span className="font-semibold text-gray-900">{result.evidence.length}</span> pieces of evidence collected
            </span>
          </div>
        )}

        {/* Progress Steps (Expandable) - Remove emoji logic */}
        {result.progress_steps && result.progress_steps.length > 0 && (
          <div className="card overflow-hidden border border-gray-200">
            <button
              onClick={() => setShowProgress(!showProgress)}
              className="w-full px-4 sm:px-5 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between text-sm font-semibold text-gray-900 transition-colors min-h-[44px]"
            >
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-gray-700 flex-shrink-0" />
                <span>AI Processing Steps</span>
                <Badge variant="neutral" className="text-xs">{result.progress_steps.length}</Badge>
              </div>
              {showProgress ? (
                <ChevronUp className="h-5 w-5 text-gray-600 flex-shrink-0" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-600 flex-shrink-0" />
              )}
            </button>

            {showProgress && (
              <div className="px-4 sm:px-5 py-4 bg-white border-t border-gray-200">
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {result.progress_steps.map((step, idx) => {
                    // Remove emoji prefixes and detect type from content
                    const cleanStep = step.replace(/^[⚠✓]\s*/, '');
                    const isWarning = step.includes('⚠') || step.toLowerCase().includes('warning');
                    const isSuccess = step.includes('✓') || step.toLowerCase().includes('complete');

                    return (
                      <div
                        key={idx}
                        className="flex items-start gap-3 text-xs sm:text-sm"
                      >
                        <span className="flex-shrink-0 w-6 h-6 bg-gray-100 text-gray-700 font-semibold rounded-full flex items-center justify-center text-xs">
                          {idx + 1}
                        </span>
                        <span className={cn(
                          'flex-1 leading-relaxed',
                          isWarning ? 'text-orange-700 font-medium' :
                          isSuccess ? 'text-green-700 font-medium' :
                          'text-gray-700'
                        )}>
                          {cleanStep}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Actions - Mobile optimized */}
      <div className="px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 border-t border-gray-200">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3">
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              icon={<Eye className="h-4 w-4" />}
              onClick={onViewDetails}
              size="sm"
            >
              <span className="hidden sm:inline">View Details</span>
              <span className="sm:hidden">Details</span>
            </Button>

            {onDelete && (
              <Button
                variant="ghost"
                icon={<Trash2 className="h-4 w-4" />}
                onClick={onDelete}
                size="sm"
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <span className="hidden sm:inline">Delete</span>
                <span className="sm:hidden">Delete</span>
              </Button>
            )}
          </div>

          {result.requires_review && (
            <Button
              variant="primary"
              onClick={onReview}
              size="sm"
              className="sm:w-auto"
            >
              Review Now
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
