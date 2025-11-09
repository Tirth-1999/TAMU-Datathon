/**
 * Image Analysis Viewer Component - Modern SaaS Design
 *
 * Displays analyzed images with classifications and detected elements.
 * Mobile-optimized with proper touch targets and responsive layout.
 */
import React, { useState } from 'react';
import { Image as ImageIcon, Tag, Eye, Shield, X, AlertTriangle } from 'lucide-react';
import type { ImageAnalysis } from '../types/classification';
import { getClassificationColor, formatConfidence, cn } from '../lib/utils';
import { StatusBadge } from './ui/StatusBadge';
import { Badge } from './ui/Badge';

interface ImageAnalysisViewerProps {
  imageAnalyses: ImageAnalysis[];
  pageImages?: string[];
}

export const ImageAnalysisViewer: React.FC<ImageAnalysisViewerProps> = ({
  imageAnalyses,
  pageImages = [],
}) => {
  const [selectedImage, setSelectedImage] = useState<number | null>(null);

  if (imageAnalyses.length === 0) {
    return (
      <div className="text-center py-8 sm:py-12 text-gray-500">
        <ImageIcon className="h-10 w-10 sm:h-12 sm:w-12 mx-auto mb-3 text-gray-400" />
        <p className="text-sm">No images analyzed in this document.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <ImageIcon className="h-4 w-4 sm:h-5 sm:w-5 text-gray-600 flex-shrink-0" />
        <h3 className="text-base sm:text-lg font-semibold text-gray-900">
          Image Analysis
        </h3>
        <Badge variant="neutral" className="text-xs">
          {imageAnalyses.length}
        </Badge>
      </div>

      {/* Image Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
        {imageAnalyses.map((analysis, index) => (
          <div
            key={index}
            className="card overflow-hidden hover:shadow-md transition-shadow"
          >
            {/* Image Preview */}
            {pageImages[analysis.image_index] && (
              <div className="relative bg-gray-100 aspect-video">
                <img
                  src={`data:image/png;base64,${pageImages[analysis.image_index]}`}
                  alt={`Image ${analysis.image_index + 1}`}
                  className="w-full h-full object-contain cursor-pointer"
                  onClick={() => setSelectedImage(analysis.image_index)}
                />
                {/* View Button - Proper touch target (44px min) */}
                <button
                  onClick={() => setSelectedImage(analysis.image_index)}
                  className="absolute top-2 right-2 bg-white hover:bg-gray-50 rounded-lg p-2 shadow-sm hover:shadow-md transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label={`View full size image ${analysis.image_index + 1}`}
                >
                  <Eye className="h-5 w-5 text-gray-700" />
                </button>
              </div>
            )}

            {/* Analysis Details */}
            <div className="p-3 sm:p-4 space-y-3">
              {/* Header */}
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs sm:text-sm font-medium text-gray-600">
                  Image {analysis.image_index + 1} • Page {analysis.page}
                </span>
                <StatusBadge status={analysis.classification} />
              </div>

              {/* Confidence */}
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Confidence:</span>
                <span className="font-semibold text-gray-900">{formatConfidence(analysis.confidence)}</span>
              </div>

              {/* Sensitive Visual Indicator */}
              {analysis.contains_sensitive_visual && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-2">
                  <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
                  <span className="text-xs text-red-800 font-medium">
                    Contains Sensitive Visual Elements
                  </span>
                </div>
              )}

              {/* Visual Elements */}
              {analysis.visual_elements && analysis.visual_elements.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-700 mb-1.5">
                    Detected Elements:
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {analysis.visual_elements.map((element, idx) => (
                      <Badge key={idx} variant="info">
                        {element}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* OCR Text */}
              {analysis.ocr_text && (
                <div>
                  <div className="text-xs font-semibold text-gray-700 mb-1.5">
                    Extracted Text (OCR):
                  </div>
                  <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2 max-h-20 overflow-y-auto">
                    {analysis.ocr_text}
                  </p>
                </div>
              )}

              {/* Keywords */}
              {analysis.keywords && analysis.keywords.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-700 mb-1.5 flex items-center gap-1">
                    <Tag className="h-3 w-3" />
                    <span>Keywords:</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {analysis.keywords.map((keyword, idx) => (
                      <Badge key={idx} variant="warning">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Reasoning */}
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-1.5">Reasoning:</div>
                <p className="text-xs text-gray-600 leading-relaxed">{analysis.reasoning}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Full Image Modal */}
      {selectedImage !== null && pageImages[selectedImage] && (
        <div
          className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-5xl max-h-[90vh] bg-white rounded-lg overflow-hidden shadow-2xl">
            {/* Close Button - Proper touch target */}
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute top-2 right-2 sm:top-4 sm:right-4 bg-white hover:bg-gray-100 rounded-lg p-2 shadow-lg transition-colors z-10 min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Close image viewer"
            >
              <X className="h-5 w-5 sm:h-6 sm:w-6 text-gray-700" />
            </button>
            <img
              src={`data:image/png;base64,${pageImages[selectedImage]}`}
              alt={`Image ${selectedImage + 1}`}
              className="w-full h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </div>
  );
};
