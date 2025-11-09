/**
 * Text Segment Viewer Component - Modern SaaS Design
 *
 * Displays text segments with color-coded sensitivity levels
 * and mobile-optimized grid layout.
 */
import React, { useState } from 'react';
import { Shield, Tag, ChevronDown, ChevronUp } from 'lucide-react';
import type { TextSegment, ClassificationCategory } from '../types/classification';
import { getClassificationColor, formatConfidence, cn } from '../lib/utils';
import { StatusBadge } from './ui/StatusBadge';
import { Badge } from './ui/Badge';

interface TextSegmentViewerProps {
  segments: TextSegment[];
  fullText?: string;
}

export const TextSegmentViewer: React.FC<TextSegmentViewerProps> = ({
  segments,
}) => {
  const [expandedSegments, setExpandedSegments] = useState<Set<number>>(new Set());
  const [filterLevel, setFilterLevel] = useState<ClassificationCategory | 'All'>('All');

  const toggleSegment = (index: number) => {
    const newExpanded = new Set(expandedSegments);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSegments(newExpanded);
  };

  const filteredSegments = segments.filter(seg => 
    filterLevel === 'All' || seg.classification === filterLevel
  );

  const getSegmentColor = (classification: ClassificationCategory) => {
    switch (classification) {
      case 'Public':
        return 'bg-green-50 border-green-200 text-green-900';
      case 'Confidential':
        return 'bg-yellow-50 border-yellow-200 text-yellow-900';
      case 'Highly Sensitive':
        return 'bg-red-50 border-red-200 text-red-900';
      case 'Unsafe':
        return 'bg-purple-50 border-purple-200 text-purple-900';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-900';
    }
  };

  const stats = {
    total: segments.length,
    public: segments.filter(s => s.classification === 'Public').length,
    confidential: segments.filter(s => s.classification === 'Confidential').length,
    highlySensitive: segments.filter(s => s.classification === 'Highly Sensitive').length,
    unsafe: segments.filter(s => s.classification === 'Unsafe').length,
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header with stats and filter - Mobile responsive */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 sm:h-5 sm:w-5 text-gray-600 flex-shrink-0" />
          <h3 className="text-base sm:text-lg font-semibold text-gray-900">
            Text Analysis
          </h3>
          <Badge variant="neutral" className="text-xs">
            {filteredSegments.length}
          </Badge>
        </div>

        <select
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value as ClassificationCategory | 'All')}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 min-h-[44px]"
        >
          <option value="All">All Segments ({stats.total})</option>
          <option value="Public">Public ({stats.public})</option>
          <option value="Confidential">Confidential ({stats.confidential})</option>
          <option value="Highly Sensitive">Highly Sensitive ({stats.highlySensitive})</option>
          <option value="Unsafe">Unsafe ({stats.unsafe})</option>
        </select>
      </div>

      {/* Statistics Bar - 2 cols on mobile, 4 on desktop */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="text-xl sm:text-2xl font-bold text-green-700">{stats.public}</div>
          <div className="text-xs text-green-600">Public</div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="text-xl sm:text-2xl font-bold text-yellow-700">{stats.confidential}</div>
          <div className="text-xs text-yellow-600">Confidential</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-xl sm:text-2xl font-bold text-red-700">{stats.highlySensitive}</div>
          <div className="text-xs text-red-600">Highly Sensitive</div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
          <div className="text-xl sm:text-2xl font-bold text-purple-700">{stats.unsafe}</div>
          <div className="text-xs text-purple-600">Unsafe</div>
        </div>
      </div>

      {/* Segment List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredSegments.map((segment, index) => {
          const isExpanded = expandedSegments.has(index);
          const colorClass = getSegmentColor(segment.classification);

          return (
            <div
              key={index}
              className={cn(
                'border rounded-lg overflow-hidden transition-all card',
                colorClass
              )}
            >
              {/* Segment Header - Mobile optimized */}
              <button
                onClick={() => toggleSegment(index)}
                className="w-full px-3 sm:px-4 py-3 flex items-start sm:items-center gap-2 sm:gap-3 hover:opacity-80 transition-opacity text-left min-h-[44px]"
              >
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 flex-1 min-w-0">
                  {/* First row on mobile: badge + confidence + page */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={segment.classification} />
                    <span className="text-xs font-medium text-gray-700">
                      {formatConfidence(segment.confidence)}
                    </span>
                    <span className="text-xs text-gray-600">Page {segment.page}</span>
                  </div>
                  {/* Second row on mobile: preview text */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate text-gray-800">
                      {segment.text.substring(0, 80)}{segment.text.length > 80 ? '...' : ''}
                    </p>
                  </div>
                </div>
                <div className="flex-shrink-0">
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-gray-600" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-600" />
                  )}
                </div>
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="px-3 sm:px-4 py-3 border-t border-gray-200 space-y-3 bg-white/50">
                  {/* Full Text */}
                  <div>
                    <div className="text-xs font-semibold text-gray-700 mb-1">Text:</div>
                    <p className="text-sm leading-relaxed text-gray-800">{segment.text}</p>
                  </div>

                  {/* Keywords */}
                  {segment.keywords && segment.keywords.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
                        <Tag className="h-3 w-3" />
                        <span>Keywords:</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {segment.keywords.map((keyword, idx) => (
                          <Badge key={idx} variant="neutral" className="text-xs">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reasoning */}
                  <div>
                    <div className="text-xs font-semibold text-gray-700 mb-1">Reasoning:</div>
                    <p className="text-xs text-gray-700 leading-relaxed">{segment.reasoning}</p>
                  </div>

                  {/* Position Info */}
                  <div className="text-xs text-gray-600">
                    Position: {segment.start_char} - {segment.end_char}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredSegments.length === 0 && (
        <div className="text-center py-8 sm:py-12 text-gray-500">
          <p className="text-sm">No segments found with the selected filter.</p>
        </div>
      )}
    </div>
  );
};
