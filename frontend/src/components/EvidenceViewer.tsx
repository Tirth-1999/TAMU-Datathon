/**
 * Evidence viewer component with page-level citations
 */
import React from 'react';
import { FileText, Image as ImageIcon, Quote } from 'lucide-react';
import type { Evidence } from '../types/classification';

interface EvidenceViewerProps {
  evidence: Evidence[];
  title?: string;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  evidence,
  title = 'Classification Evidence',
}) => {
  if (evidence.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <FileText className="h-12 w-12 text-gray-300 mx-auto mb-3" />
        <p className="text-sm text-gray-500">No evidence available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>

      <div className="space-y-3">
        {evidence.map((item, index) => (
          <div
            key={index}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-2">
                {item.image_index !== null && item.image_index !== undefined ? (
                  <>
                    <ImageIcon className="h-4 w-4 text-blue-500" />
                    <span className="text-xs font-semibold text-blue-700">
                      Image {item.image_index + 1}
                    </span>
                  </>
                ) : item.page !== null ? (
                  <>
                    <FileText className="h-4 w-4 text-gray-500" />
                    <span className="text-xs font-semibold text-gray-700">
                      Page {item.page}
                    </span>
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 text-gray-400" />
                    <span className="text-xs font-semibold text-gray-500">
                      General
                    </span>
                  </>
                )}
              </div>

              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                Evidence #{index + 1}
              </span>
            </div>

            {/* Region/Location */}
            {item.region && (
              <div className="mb-2">
                <p className="text-xs text-gray-500 mb-1">Location</p>
                <p className="text-sm font-medium text-gray-700">{item.region}</p>
              </div>
            )}

            {/* Quote */}
            {item.quote && (
              <div className="mb-3 bg-gray-50 border-l-4 border-primary-400 p-3 rounded-r">
                <div className="flex items-start space-x-2">
                  <Quote className="h-4 w-4 text-primary-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-700 italic">"{item.quote}"</p>
                </div>
              </div>
            )}

            {/* Reasoning */}
            <div>
              <p className="text-xs text-gray-500 mb-1">Why this matters</p>
              <p className="text-sm text-gray-800">{item.reasoning}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
        <p className="text-sm text-primary-900">
          <span className="font-semibold">{evidence.length}</span> pieces of evidence support this classification.
          Each citation references specific pages or regions in the document.
        </p>
      </div>
    </div>
  );
};
