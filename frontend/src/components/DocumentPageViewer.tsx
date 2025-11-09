/**
 * Document Page Viewer Component - Modern SaaS Design
 *
 * Page-by-page document viewer with mobile-optimized navigation.
 */
import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, FileText } from 'lucide-react';
import { cn } from '../lib/utils';
import { Badge } from './ui/Badge';

interface DocumentPageViewerProps {
  pageImages: string[];
  pageCount?: number;
  filename?: string;
}

export const DocumentPageViewer: React.FC<DocumentPageViewerProps> = ({
  pageImages,
}) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [showScrollHint, setShowScrollHint] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Check if page numbers container needs scrolling
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      setShowScrollHint(container.scrollWidth > container.clientWidth);
    }
  }, [pageImages]);

  if (!pageImages || pageImages.length === 0) {
    return (
      <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-8 sm:p-12 text-center">
        <FileText className="h-10 w-10 sm:h-12 sm:w-12 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-600">No preview available</p>
      </div>
    );
  }

  const goToPrevPage = () => setCurrentPage((prev) => Math.max(0, prev - 1));
  const goToNextPage = () => setCurrentPage((prev) => Math.min(pageImages.length - 1, prev + 1));
  const jumpToPage = (pageNum: number) => setCurrentPage(pageNum);

  return (
    <div className="space-y-3 sm:space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between p-3 sm:p-4 card">
        <div className="flex items-center gap-2">
          <h3 className="text-sm sm:text-base font-semibold text-gray-900">Document Preview</h3>
        </div>
        <Badge variant="neutral" className="text-xs">
          Page {currentPage + 1} / {pageImages.length}
        </Badge>
      </div>

      {/* Page Image Display */}
      <div className="card overflow-hidden">
        <img
          src={`data:image/png;base64,${pageImages[currentPage]}`}
          alt={`Page ${currentPage + 1}`}
          className="w-full h-auto"
        />
      </div>

      {/* Navigation Controls - Mobile optimized */}
      <div className="card p-3 sm:p-4">
        <div className="flex items-center justify-between gap-2 sm:gap-3">
          {/* Previous Button - Icon only on mobile */}
          <button
            onClick={goToPrevPage}
            disabled={currentPage === 0}
            className={cn(
              'flex items-center justify-center gap-1 px-3 sm:px-4 py-2 rounded-lg font-medium transition-all min-h-[44px] min-w-[44px]',
              currentPage === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-900 text-white hover:bg-gray-800'
            )}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-5 w-5 flex-shrink-0" />
            <span className="hidden sm:inline">Previous</span>
          </button>

          {/* Page Number Buttons - Scrollable with indicator */}
          <div className="relative flex-1 max-w-md mx-auto">
            <div
              ref={scrollContainerRef}
              className="flex gap-1 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 pb-2 scroll-smooth"
            >
              {pageImages.map((_, index) => (
                <button
                  key={index}
                  onClick={() => jumpToPage(index)}
                  className={cn(
                    'px-3 py-2 rounded-lg text-sm font-medium transition-all min-w-[44px] min-h-[44px] flex items-center justify-center flex-shrink-0',
                    currentPage === index
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  )}
                  aria-label={`Go to page ${index + 1}`}
                  aria-current={currentPage === index ? 'page' : undefined}
                >
                  {index + 1}
                </button>
              ))}
            </div>
            {/* Scroll hint for mobile */}
            {showScrollHint && (
              <div className="absolute -bottom-1 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-blue-500/30 to-transparent pointer-events-none" />
            )}
          </div>

          {/* Next Button - Icon only on mobile */}
          <button
            onClick={goToNextPage}
            disabled={currentPage === pageImages.length - 1}
            className={cn(
              'flex items-center justify-center gap-1 px-3 sm:px-4 py-2 rounded-lg font-medium transition-all min-h-[44px] min-w-[44px]',
              currentPage === pageImages.length - 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-900 text-white hover:bg-gray-800'
            )}
            aria-label="Next page"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="h-5 w-5 flex-shrink-0" />
          </button>
        </div>
      </div>
    </div>
  );
};

