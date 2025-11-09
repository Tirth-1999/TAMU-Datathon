/**
 * HITL Review Modal Component - Modern SaaS Design
 *
 * Full-screen modal on mobile, centered on desktop.
 * Mobile-optimized with proper touch targets and design system.
 */
import React, { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, AlertTriangle, FileText, ImageIcon } from 'lucide-react';
import type { ClassificationResult, ClassificationCategory } from '../types/classification';
import { getClassificationColor, formatConfidence } from '../lib/utils';
import { Button } from './ui/Button';
import { StatusBadge } from './ui/StatusBadge';

interface ReviewModalProps {
  result: ClassificationResult;
  onClose: () => void;
  onSubmit: (approved: boolean, correctedClassification?: ClassificationCategory, notes?: string) => void;
}

export const ReviewModal: React.FC<ReviewModalProps> = ({
  result,
  onClose,
  onSubmit,
}) => {
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);
  const [correctedClassification, setCorrectedClassification] = useState<ClassificationCategory>(result.classification);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose, isSubmitting]);

  const handleSubmit = async () => {
    if (!decision) {
      alert('Please select Approve or Reject');
      return;
    }

    if (decision === 'reject' && !notes.trim()) {
      alert('Please provide feedback notes when rejecting');
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit(
        decision === 'approve',
        decision === 'reject' ? correctedClassification : undefined,
        notes || undefined
      );
      onClose();
    } catch (error) {
      alert(`Failed to submit review: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const classifications: ClassificationCategory[] = [
    'Public' as ClassificationCategory,
    'Confidential' as ClassificationCategory,
    'Highly Sensitive' as ClassificationCategory,
    'Unsafe' as ClassificationCategory,
  ];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-0 sm:p-4 animate-fadeIn">
      <div className="bg-white w-full h-full sm:h-auto sm:rounded-lg sm:max-w-3xl sm:max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header - Mobile optimized */}
        <div className="bg-gray-50 border-b border-gray-200 px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex-1 min-w-0 pr-4">
            <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Human Review Required</h2>
            <p className="text-xs sm:text-sm text-gray-600 mt-1 truncate">Review and approve or correct the classification</p>
          </div>
          {/* Close button - proper touch target */}
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close review modal"
          >
            <X className="h-5 w-5 sm:h-6 sm:w-6" />
          </button>
        </div>

        {/* Content - Mobile responsive padding */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
          {/* Document Info */}
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">Document</h3>
            <div className="card p-3 sm:p-4 bg-gray-50">
              <p className="font-medium text-gray-900 truncate">{result.filename}</p>
              <div className="flex items-center gap-2 mt-1 text-xs sm:text-sm text-gray-600">
                <span className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {result.page_count} pages
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <ImageIcon className="h-3 w-3" />
                  {result.image_count} images
                </span>
              </div>
            </div>
          </div>

          {/* Current Classification */}
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">AI Classification</h3>
            <div className="card p-3 sm:p-4 bg-gray-50">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
                <StatusBadge status={result.classification} />
                <span className="text-xs sm:text-sm text-gray-600">
                  {formatConfidence(result.confidence)} confidence
                </span>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">{result.summary}</p>
            </div>
          </div>

          {/* Review Reason */}
          {result.review_reason && (
            <div className="card p-3 sm:p-4 bg-yellow-50 border-l-4 border-yellow-500">
              <div className="flex items-start gap-2 sm:gap-3">
                <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-yellow-900">Why Review is Needed</h4>
                  <p className="text-xs sm:text-sm text-yellow-800 mt-1 leading-relaxed">{result.review_reason}</p>
                </div>
              </div>
            </div>
          )}

          {/* Decision - 1 col on mobile, 2 on desktop */}
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-3">Your Decision</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <button
                onClick={() => setDecision('approve')}
                className={`p-3 sm:p-4 rounded-lg border-2 transition-all min-h-[60px] ${
                  decision === 'approve'
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200 hover:border-green-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <CheckCircle className={`h-5 w-5 sm:h-6 sm:w-6 flex-shrink-0 ${decision === 'approve' ? 'text-green-600' : 'text-gray-400'}`} />
                  <div className="text-left flex-1 min-w-0">
                    <p className={`text-sm sm:text-base font-semibold ${decision === 'approve' ? 'text-green-900' : 'text-gray-700'}`}>
                      Approve
                    </p>
                    <p className="text-xs text-gray-600">Classification is correct</p>
                  </div>
                </div>
              </button>

              <button
                onClick={() => setDecision('reject')}
                className={`p-3 sm:p-4 rounded-lg border-2 transition-all min-h-[60px] ${
                  decision === 'reject'
                    ? 'border-red-500 bg-red-50'
                    : 'border-gray-200 hover:border-red-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <XCircle className={`h-5 w-5 sm:h-6 sm:w-6 flex-shrink-0 ${decision === 'reject' ? 'text-red-600' : 'text-gray-400'}`} />
                  <div className="text-left flex-1 min-w-0">
                    <p className={`text-sm sm:text-base font-semibold ${decision === 'reject' ? 'text-red-900' : 'text-gray-700'}`}>
                      Reject
                    </p>
                    <p className="text-xs text-gray-600">Needs correction</p>
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Corrected Classification (if rejecting) */}
          {decision === 'reject' && (
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-3">Correct Classification</h3>
              <select
                value={correctedClassification}
                onChange={(e) => setCorrectedClassification(e.target.value as ClassificationCategory)}
                className="w-full px-3 sm:px-4 py-2 border border-gray-300 rounded-lg bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 min-h-[44px] text-sm sm:text-base"
              >
                {classifications.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Feedback Notes */}
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-3">
              Feedback Notes {decision === 'reject' && <span className="text-red-600">*</span>}
            </h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={decision === 'approve'
                ? 'Optional: Add any additional notes...'
                : 'Required: Explain why the classification is incorrect...'
              }
              rows={4}
              className="w-full px-3 sm:px-4 py-2 sm:py-3 border border-gray-300 rounded-lg bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 text-sm sm:text-base resize-none"
            />
          </div>
        </div>

        {/* Footer - Mobile optimized */}
        <div className="bg-gray-50 border-t border-gray-200 px-4 sm:px-6 py-3 sm:py-4 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2 sm:gap-3">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!decision || isSubmitting}
            loading={isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Review'}
          </Button>
        </div>
      </div>
    </div>
  );
};
