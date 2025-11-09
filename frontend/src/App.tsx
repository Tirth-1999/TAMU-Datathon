/**
 * Main Application Component - Modern SaaS Theme
 */
import { useState, useEffect } from 'react';
import {
  FileText, BarChart3, Upload as UploadIcon, Play, Trash2,
  Shield, Zap, CheckCircle2, AlertTriangle, TrendingUp,
  Search, X, Image as ImageIcon, Activity, ChevronLeft, ChevronRight
} from 'lucide-react';
import { FileUpload } from './components/FileUpload';
import { ClassificationCard } from './components/ClassificationCard';
import { EvidenceViewer } from './components/EvidenceViewer';
import { StatsPanel } from './components/StatsPanel';
import { TextSegmentViewer } from './components/TextSegmentViewer';
import { ImageAnalysisViewer } from './components/ImageAnalysisViewer';
import { DocumentPageViewer } from './components/DocumentPageViewer';
import { ReviewModal } from './components/ReviewModal';
import { GlobalProgressIndicator } from './components/GlobalProgressIndicator';
import { NotificationCenter } from './components/NotificationCenter';
import { Button } from './components/ui/Button';
import { Badge } from './components/ui/Badge';
import { StatusBadge } from './components/ui/StatusBadge';
import { useProgress } from './contexts/ProgressContext';
import { classifyApi, hitlApi } from './services/api';
import type { UploadResponse, ClassificationResult, ClassificationCategory } from './types/classification';

type Tab = 'upload' | 'results' | 'stats';
type DetailTab = 'overview' | 'text-analysis' | 'images' | 'pages' | 'evidence';

function App() {
  // Use progress context
  const { startOperation, addProgress, completeOperation, errorOperation } = useProgress();

  // UI state
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [detailTab, setDetailTab] = useState<DetailTab>('overview');
  const [uploadedDocs, setUploadedDocs] = useState<UploadResponse[]>([]);
  const [classificationResults, setClassificationResults] = useState<ClassificationResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<ClassificationResult | null>(null);
  const [reviewingResult, setReviewingResult] = useState<ClassificationResult | null>(null);
  const [classifyingDocs, setClassifyingDocs] = useState<Set<string>>(new Set());
  const [showNotifications, setShowNotifications] = useState(false);
  const [currentResultIndex, setCurrentResultIndex] = useState(0);

  // Load existing results on mount
  useEffect(() => {
    loadExistingResults();
  }, []);
  
  // Reset to most recent result when classification results change
  useEffect(() => {
    if (classificationResults.length > 0) {
      setCurrentResultIndex(classificationResults.length - 1); // Show most recent (last item)
    } else {
      setCurrentResultIndex(0); // Reset when no results
    }
  }, [classificationResults.length]);

  const loadExistingResults = async () => {
    try {
      const data = await classifyApi.getAllResults();
      if (data.results) {
        // Filter out invalid results (like learning_database.json metadata)
        // Only keep results that have required classification properties
        const validResults = data.results.filter((result: any) =>
          result.document_id &&
          result.classification &&
          result.filename &&
          result.summary
        );
        setClassificationResults(validResults);
      }
    } catch (error) {
      console.error('Failed to load results:', error);
    }
  };

  const handleUploadComplete = (responses: UploadResponse[]) => {
    const successfulUploads = responses.filter(r => r.status === 'success');
    setUploadedDocs(prev => [...prev, ...successfulUploads]);
  };

  const handleClassifyDocument = async (docId: string, enableDualVerification: boolean = false) => {
    // Get filename from uploaded docs
    const doc = uploadedDocs.find(d => d.document_id === docId);
    const filename = doc?.filename;

    // Add to classifying set
    setClassifyingDocs(prev => new Set(prev).add(docId));

    // Start operation in progress context
    startOperation(docId, filename);

    // Track completion status to prevent race conditions
    let isCompleted = false;
    let completionTimer: ReturnType<typeof setTimeout> | null = null;
    let cleanupTimer: ReturnType<typeof setTimeout> | null = null;

    // Subscribe to progress updates
    const unsubscribe = classifyApi.subscribeToProgress(
      docId,
      // On progress update
      (message: string) => {
        addProgress(docId, message);
      },
      // On complete (from SSE)
      () => {
        if (!isCompleted) {
          isCompleted = true;
          completeOperation(docId);
          console.log('[Classification] ✅ Completed via SSE:', docId);
          
          // Cleanup after SSE completes
          if (completionTimer) clearTimeout(completionTimer);
          if (cleanupTimer) clearTimeout(cleanupTimer);
          
          // Remove from classifying set
          setClassifyingDocs(prev => {
            const newSet = new Set(prev);
            newSet.delete(docId);
            return newSet;
          });
        }
      },
      // On error
      (error?: string) => {
        if (!isCompleted) {
          isCompleted = true;
          errorOperation(docId, error || 'Connection error');
          
          // Cleanup SSE on error
          unsubscribe();
          if (completionTimer) clearTimeout(completionTimer);
          if (cleanupTimer) clearTimeout(cleanupTimer);
          
          // Remove from classifying set
          setClassifyingDocs(prev => {
            const newSet = new Set(prev);
            newSet.delete(docId);
            return newSet;
          });
        }
      }
    );

    // Wait 500ms to ensure SSE connection is fully established
    await new Promise(resolve => setTimeout(resolve, 500));

    try {
      const result = await classifyApi.classifyDocument(docId, enableDualVerification);
      setClassificationResults(prev => [...prev, result]);

      // Remove from uploaded docs once classified
      setUploadedDocs(prev => prev.filter(d => d.document_id !== docId));
      
      // Fallback: If SSE doesn't send DONE within 2 seconds after HTTP completes, force completion
      completionTimer = setTimeout(() => {
        if (!isCompleted) {
          isCompleted = true;
          completeOperation(docId);
          console.log('[Classification] ⚠️  Completed via HTTP fallback (SSE timeout):', docId);
          unsubscribe();
          
          // Remove from classifying set
          setClassifyingDocs(prev => {
            const newSet = new Set(prev);
            newSet.delete(docId);
            return newSet;
          });
        }
      }, 2000); // Wait 2 seconds for SSE to complete naturally
      
      // Safety cleanup: Force cleanup after 5 seconds no matter what
      cleanupTimer = setTimeout(() => {
        if (!isCompleted) {
          console.log('[Classification] 🔴 Force cleanup after 5s timeout:', docId);
          isCompleted = true;
          completeOperation(docId);
        }
        unsubscribe();
        if (completionTimer) clearTimeout(completionTimer);
        
        // Remove from classifying set
        setClassifyingDocs(prev => {
          const newSet = new Set(prev);
          newSet.delete(docId);
          return newSet;
        });
      }, 5000);
      
    } catch (error: any) {
      if (!isCompleted) {
        isCompleted = true;
        errorOperation(docId, error.message);
      }
      
      // Cleanup on error
      unsubscribe();
      if (completionTimer) clearTimeout(completionTimer);
      if (cleanupTimer) clearTimeout(cleanupTimer);
      
      // Remove from classifying set
      setClassifyingDocs(prev => {
        const newSet = new Set(prev);
        newSet.delete(docId);
        return newSet;
      });
      
      alert(`Classification failed: ${error.message}`);
    }
  };

  const handleClassifyAll = async () => {
    if (uploadedDocs.length === 0) {
      alert('No documents to classify');
      return;
    }

    // Classify all documents in parallel
    const classificationPromises = uploadedDocs.map(doc => 
      handleClassifyDocument(doc.document_id)
    );

    // Wait for all to complete (but they run in parallel)
    await Promise.allSettled(classificationPromises);
  };

  const handleViewDetails = (result: ClassificationResult) => {
    setSelectedResult(result);
  };

  const handleDeleteResult = async (documentId: string) => {
    // Check if document is currently being classified
    const isBeingClassified = classifyingDocs.has(documentId);
    
    if (isBeingClassified) {
      if (!confirm('⚠️ This document is currently being classified. Deleting it will cancel the classification process. Are you sure you want to continue?')) {
        return;
      }
    } else {
      if (!confirm('Are you sure you want to delete this document and its classification result? This action cannot be undone.')) {
        return;
      }
    }

    try {
      // If being classified, remove from classifying set first
      if (isBeingClassified) {
        setClassifyingDocs(prev => {
          const newSet = new Set(prev);
          newSet.delete(documentId);
          return newSet;
        });
      }
      
      // Delete from backend
      await classifyApi.deleteResult(documentId);
      
      // Remove from results list and adjust index if needed
      setClassificationResults(prev => {
        const filtered = prev.filter(r => r.document_id !== documentId);
        // Adjust current index if it's now out of bounds
        if (currentResultIndex >= filtered.length && filtered.length > 0) {
          setCurrentResultIndex(filtered.length - 1);
        } else if (filtered.length === 0) {
          setCurrentResultIndex(0);
        }
        return filtered;
      });
      
      // Remove from uploaded docs (in case it's still there)
      setUploadedDocs(prev => prev.filter(d => d.document_id !== documentId));
      
      // Close modal if this was the selected result
      if (selectedResult?.document_id === documentId) {
        setSelectedResult(null);
      }
    } catch (error: any) {
      alert(`Failed to delete document: ${error.message}`);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('⚠️ WARNING: This will delete ALL uploaded documents and classification results. This action CANNOT be undone. Are you absolutely sure?')) {
      return;
    }

    // Second confirmation for extra safety
    if (!confirm('This is your last chance! Click OK to permanently delete everything or Cancel to go back.')) {
      return;
    }

    try {
      await classifyApi.deleteAllResults();

      // Clear all state
      setClassificationResults([]);
      setUploadedDocs([]);
      setSelectedResult(null);
      setReviewingResult(null);
      setClassifyingDocs(new Set());
      setCurrentResultIndex(0); // Reset index
      
      alert('✅ All documents and results have been successfully deleted.');
    } catch (error: any) {
      alert(`Failed to clear all documents: ${error.message}`);
    }
  };

  const handleReview = (result: ClassificationResult) => {
    setReviewingResult(result);
  };

  const handleReviewSubmit = async (
    approved: boolean,
    correctedClassification?: ClassificationCategory,
    notes?: string
  ) => {
    if (!reviewingResult) return;

    try {
      if (approved) {
        // Approve the classification
        await hitlApi.quickApprove(reviewingResult.document_id);

        // Update the result to remove requires_review flag
        setClassificationResults(prev =>
          prev.map(r =>
            r.document_id === reviewingResult.document_id
              ? { ...r, requires_review: false }
              : r
          )
        );

        alert('Classification approved successfully!');
      } else {
        // Reject and provide correction
        await hitlApi.quickReject(
          reviewingResult.document_id,
          correctedClassification || reviewingResult.classification,
          'user',
          notes || ''
        );

        // Update the result with corrected classification
        setClassificationResults(prev =>
          prev.map(r =>
            r.document_id === reviewingResult.document_id
              ? {
                  ...r,
                  classification: correctedClassification || r.classification,
                  requires_review: false,
                }
              : r
          )
        );

        alert('Feedback submitted and classification corrected!');
      }

      setReviewingResult(null);
    } catch (error: any) {
      throw new Error(error.message || 'Failed to submit review');
    }
  };

  // Carousel navigation handlers
  const handlePreviousResult = () => {
    setCurrentResultIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNextResult = () => {
    setCurrentResultIndex((prev) => Math.min(classificationResults.length - 1, prev + 1));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Modern Header - Mobile Responsive */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Top Bar with Branding */}
          <div className="flex items-center justify-between py-3 sm:py-4 gap-3">
            {/* Logo/Brand - Hitachi Red Accent */}
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <div className="bg-gradient-to-br from-red-600 to-red-700 p-2 sm:p-2.5 rounded-lg flex-shrink-0 shadow-sm">
                <Shield className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-sm sm:text-lg font-semibold text-gray-900 truncate">
                  Hitachi Inspire
                </h1>
                <p className="text-xs text-gray-600 hidden sm:block">
                  Document Classification Platform
                </p>
              </div>
            </div>

            {/* Quick Stats - Scrollable on mobile */}
            <div className="flex items-center gap-3 sm:gap-4 lg:gap-6 overflow-x-auto scrollbar-hide max-w-xs sm:max-w-md lg:max-w-none flex-shrink-0">
              <div className="flex items-center gap-1.5 sm:gap-2 text-gray-700 flex-shrink-0">
                <CheckCircle2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-green-600 flex-shrink-0" />
                <div className="text-right">
                  <p className="text-xs text-gray-500 hidden sm:block">Classified</p>
                  <p className="text-xs sm:text-sm font-semibold">{classificationResults.length}</p>
                </div>
              </div>
              <div className="hidden sm:flex items-center gap-2 text-gray-700 flex-shrink-0">
                <TrendingUp className="h-4 w-4 text-blue-600 flex-shrink-0" />
                <div className="text-right">
                  <p className="text-xs text-gray-500">Accuracy</p>
                  <p className="text-sm font-semibold">98.3%</p>
                </div>
              </div>
              <div className="hidden lg:flex items-center gap-2 text-gray-700 flex-shrink-0">
                <Zap className="h-4 w-4 text-amber-600 flex-shrink-0" />
                <div className="text-right">
                  <p className="text-xs text-gray-500">Speed</p>
                  <p className="text-sm font-semibold">~15s</p>
                </div>
              </div>
            </div>

            {/* Global Progress Indicator */}
            <GlobalProgressIndicator onOpenNotifications={() => setShowNotifications(true)} />
          </div>

          {/* Navigation Tabs - Scrollable on mobile */}
          <nav className="flex gap-1 pb-px overflow-x-auto scrollbar-hide -mb-px">
            <button
              onClick={() => setActiveTab('upload')}
              className={`
                relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm
                transition-all rounded-t-lg flex-shrink-0 min-h-[44px] flex items-center
                ${activeTab === 'upload'
                  ? 'bg-white text-gray-900 shadow-sm border-b-2 border-red-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                }
              `}
            >
              <div className="flex items-center space-x-1 sm:space-x-2">
                <UploadIcon className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${activeTab === 'upload' ? 'text-red-600 animate-bounce' : ''}`} />
                <span className="whitespace-nowrap">Upload & Classify</span>
                {uploadedDocs.length > 0 && (
                  <Badge variant="error" className="animate-pulse ml-1">
                    {uploadedDocs.length}
                  </Badge>
                )}
              </div>
            </button>

            <button
              onClick={() => setActiveTab('results')}
              className={`
                relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm
                transition-all rounded-t-lg flex-shrink-0 min-h-[44px] flex items-center
                ${activeTab === 'results'
                  ? 'bg-white text-gray-900 shadow-sm border-b-2 border-red-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                }
              `}
            >
              <div className="flex items-center space-x-1 sm:space-x-2">
                <FileText className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${activeTab === 'results' ? 'text-red-600' : ''}`} />
                <span className="whitespace-nowrap">Results</span>
                {classificationResults.length > 0 && (
                  <Badge variant={activeTab === 'results' ? 'info' : 'neutral'} className="ml-1">
                    {classificationResults.length}
                  </Badge>
                )}
              </div>
            </button>

            <button
              onClick={() => setActiveTab('stats')}
              className={`
                relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm
                transition-all rounded-t-lg flex-shrink-0 min-h-[44px] flex items-center
                ${activeTab === 'stats'
                  ? 'bg-white text-gray-900 shadow-sm border-b-2 border-red-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                }
              `}
            >
              <div className="flex items-center space-x-1 sm:space-x-2">
                <BarChart3 className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${activeTab === 'stats' ? 'text-red-600' : ''}`} />
                <span className="whitespace-nowrap">Analytics</span>
              </div>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content - Mobile Responsive */}
      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8 space-y-4 sm:space-y-8">
        {activeTab === 'upload' && (
          <div className="space-y-4 sm:space-y-8 animate-fade-in">
            {/* Section Header - Mobile Responsive with Hitachi Red Accent */}
            <div className="card p-4 sm:p-6 border-l-4 border-red-600">
              <div className="flex items-center space-x-2 sm:space-x-3 mb-2 sm:mb-3">
                <div className="p-1.5 sm:p-2 bg-gradient-to-br from-red-600 to-red-700 rounded-lg shadow-sm">
                  <UploadIcon className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
                </div>
                <h2 className="text-lg sm:text-2xl font-bold text-gray-900">Upload Documents</h2>
              </div>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Upload PDF documents or images to classify them using AI-powered security analysis with triple verification.
              </p>
            </div>

            {/* Upload Component */}
            <FileUpload onUploadComplete={handleUploadComplete} />

            {/* Ready to Classify Queue */}
            {uploadedDocs.length > 0 && (
              <div className="card p-4 sm:p-6 border-t-4 border-blue-500">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-50 rounded-lg border border-blue-200">
                      <FileText className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">
                        Ready to Classify
                      </h3>
                      <p className="text-sm text-gray-600">
                        {uploadedDocs.length} document{uploadedDocs.length !== 1 ? 's' : ''} pending analysis
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="primary"
                    onClick={handleClassifyAll}
                    disabled={classifyingDocs.size > 0}
                    icon={<Play className="h-4 w-4" />}
                    className="w-full sm:w-auto"
                  >
                    {classifyingDocs.size > 0 ? `Classifying ${classifyingDocs.size}...` : 'Classify All'}
                  </Button>
                </div>

                <div className="space-y-3">
                  {uploadedDocs.map((doc, index) => (
                    <div
                      key={doc.document_id}
                      className="group relative overflow-hidden card p-4 hover:shadow-md transition-all duration-300"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      {/* Document Info */}
                      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
                        <div className="flex items-center space-x-3 sm:space-x-4 flex-1 min-w-0 w-full sm:w-auto">
                          <div className="flex-shrink-0 w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center border border-gray-200">
                            <FileText className="h-5 w-5 text-gray-700" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-gray-900 truncate">
                              {doc.filename}
                            </p>
                            <div className="flex items-center gap-2 sm:gap-3 mt-1 text-xs text-gray-600 flex-wrap">
                              <span className="flex items-center gap-1">
                                <FileText className="h-3 w-3" />
                                <span>{doc.metadata?.page_count} pages</span>
                              </span>
                              <span className="hidden sm:inline">•</span>
                              <span className="flex items-center gap-1">
                                <ImageIcon className="h-3 w-3" />
                                <span>{doc.metadata?.image_count} images</span>
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center gap-2 w-full sm:w-auto">
                          {classifyingDocs.has(doc.document_id) ? (
                            <>
                              {/* Simple Processing Indicator */}
                              <button
                                onClick={() => setShowNotifications(true)}
                                className="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg border border-blue-200 hover:bg-blue-100 transition-colors flex-1 min-w-0 min-h-[44px]"
                                title="View progress in notification center"
                              >
                                <div className="relative flex h-2 w-2 flex-shrink-0">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
                                </div>
                                <span className="text-sm font-medium text-blue-700 truncate">
                                  Classifying...
                                </span>
                                <Activity className="h-4 w-4 text-blue-600 animate-pulse-subtle flex-shrink-0" />
                              </button>

                              {/* Delete button */}
                              <button
                                onClick={() => handleDeleteResult(doc.document_id)}
                                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
                                title="Cancel and delete"
                                aria-label={`Cancel and delete ${doc.filename}`}
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </>
                          ) : (
                            <>
                              <Button
                                variant="secondary"
                                onClick={() => handleClassifyDocument(doc.document_id)}
                                size="sm"
                                className="flex-1 sm:flex-initial"
                              >
                                Classify Now
                              </Button>
                              {/* Delete button */}
                              <button
                                onClick={() => {
                                  if (confirm(`Delete "${doc.filename}"?`)) {
                                    setUploadedDocs(prev => prev.filter(d => d.document_id !== doc.document_id));
                                  }
                                }}
                                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
                                title="Delete document"
                                aria-label={`Delete ${doc.filename}`}
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="space-y-4 sm:space-y-8 animate-fade-in">
            {/* Results Header */}
            <div className="card p-4 sm:p-6 border-l-4 border-blue-500">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-600 rounded-lg">
                    <FileText className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Classification Results</h2>
                    <p className="text-sm sm:text-base text-gray-600 mt-1">
                      AI-powered security analysis with triple verification and detailed evidence
                    </p>
                  </div>
                </div>

                {classificationResults.length > 0 && (
                  <Button
                    variant="danger"
                    onClick={handleClearAll}
                    icon={<Trash2 className="h-4 w-4" />}
                    size="sm"
                    className="w-full sm:w-auto"
                  >
                    Clear All
                  </Button>
                )}
              </div>
            </div>

            {/* Results Content */}
            {classificationResults.length === 0 ? (
              <div className="card p-8 sm:p-16 text-center">
                <div className="max-w-md mx-auto">
                  <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4 sm:mb-6">
                    <FileText className="h-10 w-10 sm:h-12 sm:w-12 text-gray-400" />
                  </div>
                  <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-2">No Classifications Yet</h3>
                  <p className="text-sm sm:text-base text-gray-600 mb-6">
                    Upload and classify documents to see detailed security analysis results here.
                  </p>
                  <Button
                    variant="primary"
                    onClick={() => setActiveTab('upload')}
                    icon={<UploadIcon className="h-4 w-4" />}
                  >
                    Start Uploading
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {/* Carousel Navigation Header */}
                {classificationResults.length > 1 && (
                  <div className="flex items-center justify-between card p-4 mb-4">
                    <button
                      onClick={handlePreviousResult}
                      disabled={currentResultIndex === 0}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Previous result"
                    >
                      <ChevronLeft className="h-5 w-5" />
                      <span className="hidden sm:inline">Previous</span>
                    </button>
                    
                    <div className="text-center">
                      <p className="text-sm font-medium text-gray-900">
                        Document {currentResultIndex + 1} of {classificationResults.length}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {currentResultIndex === classificationResults.length - 1 ? '(Most Recent)' : ''}
                      </p>
                    </div>
                    
                    <button
                      onClick={handleNextResult}
                      disabled={currentResultIndex === classificationResults.length - 1}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Next result"
                    >
                      <span className="hidden sm:inline">Next</span>
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </div>
                )}

                {/* Current Result Card */}
                {classificationResults[currentResultIndex] && (
                  <div className="animate-fade-in">
                    <ClassificationCard
                      result={classificationResults[currentResultIndex]}
                      onViewDetails={() => handleViewDetails(classificationResults[currentResultIndex])}
                      onReview={() => handleReview(classificationResults[currentResultIndex])}
                      onDelete={() => handleDeleteResult(classificationResults[currentResultIndex].document_id)}
                    />
                  </div>
                )}
                
                {/* Show all button for quick access */}
                {classificationResults.length > 1 && (
                  <div className="mt-4 text-center">
                    <button
                      onClick={() => {
                        // Could expand to show all, for now just a hint
                        alert(`Viewing ${currentResultIndex + 1} of ${classificationResults.length} documents. Use the arrows above to navigate.`);
                      }}
                      className="text-sm text-gray-600 hover:text-gray-900 underline"
                    >
                      {classificationResults.length} documents classified • Click arrows to navigate
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="space-y-4 sm:space-y-8 animate-fade-in">
            {/* Stats Header */}
            <div className="card p-4 sm:p-6 border-l-4 border-green-500">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-green-600 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Statistics & Analytics</h2>
                  <p className="text-sm sm:text-base text-gray-600 mt-1">
                    Comprehensive overview of classification performance and security distribution
                  </p>
                </div>
              </div>
            </div>

            {/* Stats Panel */}
            <StatsPanel results={classificationResults} />
          </div>
        )}
      </main>

      {/* Detail Modal - Modern Design System */}
      {selectedResult && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-0 sm:p-4 animate-fade-in">
          <div className="bg-white rounded-none sm:rounded-2xl max-w-6xl w-full h-full sm:h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-scale-in">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-4 sm:py-5 flex items-center justify-between backdrop-blur-lg flex-shrink-0">
              <div className="flex-1 min-w-0 pr-4">
                <div className="flex items-center space-x-2 sm:space-x-3 mb-2">
                  <div className="p-2 bg-gray-900 rounded-lg flex-shrink-0">
                    <FileText className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-gray-900 truncate">
                    {selectedResult.filename}
                  </h2>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={selectedResult.classification} />
                  <Badge variant="success" icon={<CheckCircle2 className="h-3 w-3" />}>
                    {Math.round(selectedResult.confidence * 100)}% confidence
                  </Badge>
                  {selectedResult.verification_notes && (
                    <Badge variant="info" icon={<Shield className="h-3 w-3" />}>
                      Triple Verified
                    </Badge>
                  )}
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedResult(null);
                  setDetailTab('overview');
                }}
                className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label="Close modal"
              >
                <X className="h-5 w-5 sm:h-6 sm:w-6" />
              </button>
            </div>

            {/* Tabs */}
            <div className="bg-gray-50 border-b border-gray-200 px-4 sm:px-6 flex-shrink-0">
              <nav className="flex gap-1 -mb-px overflow-x-auto scrollbar-hide">
                <button
                  onClick={() => setDetailTab('overview')}
                  className={`
                    relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all whitespace-nowrap min-h-[44px] flex items-center
                    ${detailTab === 'overview'
                      ? 'text-gray-900 border-b-2 border-gray-900'
                      : 'text-gray-600 hover:text-gray-900'
                    }
                  `}
                >
                  Overview
                </button>
                {selectedResult.text_segments && selectedResult.text_segments.length > 0 && (
                  <button
                    onClick={() => setDetailTab('text-analysis')}
                    className={`
                      relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all whitespace-nowrap min-h-[44px] flex items-center gap-2
                      ${detailTab === 'text-analysis'
                        ? 'text-gray-900 border-b-2 border-gray-900'
                        : 'text-gray-600 hover:text-gray-900'
                      }
                    `}
                  >
                    <span>Text Analysis</span>
                    <Badge variant="error" className="text-xs">{selectedResult.text_segments.length}</Badge>
                  </button>
                )}
                {selectedResult.image_analyses && selectedResult.image_analyses.length > 0 && (
                  <button
                    onClick={() => setDetailTab('images')}
                    className={`
                      relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all whitespace-nowrap min-h-[44px] flex items-center gap-2
                      ${detailTab === 'images'
                        ? 'text-gray-900 border-b-2 border-gray-900'
                        : 'text-gray-600 hover:text-gray-900'
                      }
                    `}
                  >
                    <span>Images</span>
                    <Badge variant="neutral" className="text-xs">{selectedResult.image_analyses.length}</Badge>
                  </button>
                )}
                {selectedResult.page_images_base64 && selectedResult.page_images_base64.length > 0 && (
                  <button
                    onClick={() => setDetailTab('pages')}
                    className={`
                      relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all whitespace-nowrap min-h-[44px] flex items-center gap-2
                      ${detailTab === 'pages'
                        ? 'text-gray-900 border-b-2 border-gray-900'
                        : 'text-gray-600 hover:text-gray-900'
                      }
                    `}
                  >
                    <span>Pages</span>
                    <Badge variant="neutral" className="text-xs">{selectedResult.page_images_base64.length}</Badge>
                  </button>
                )}
                <button
                  onClick={() => setDetailTab('evidence')}
                  className={`
                    relative px-4 sm:px-6 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all whitespace-nowrap min-h-[44px] flex items-center gap-2
                    ${detailTab === 'evidence'
                      ? 'text-gray-900 border-b-2 border-gray-900'
                      : 'text-gray-600 hover:text-gray-900'
                    }
                  `}
                >
                  <span>Evidence</span>
                  <Badge variant="info" className="text-xs">{selectedResult.evidence?.length || 0}</Badge>
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-gray-50">
              {detailTab === 'overview' && (
                <div className="space-y-4 sm:space-y-6 animate-fade-in">
                  {/* Summary Card */}
                  <div className="card p-4 sm:p-6 border-l-4 border-blue-500">
                    <div className="flex items-center space-x-2 mb-3">
                      <FileText className="h-5 w-5 text-blue-600" />
                      <h3 className="text-base sm:text-lg font-bold text-gray-900">Summary</h3>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{selectedResult.summary}</p>
                  </div>

                  {/* Reasoning Card */}
                  <div className="card p-4 sm:p-6 border-l-4 border-gray-900">
                    <div className="flex items-center space-x-2 mb-3">
                      <Shield className="h-5 w-5 text-gray-900" />
                      <h3 className="text-base sm:text-lg font-bold text-gray-900">AI Classification Reasoning</h3>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 whitespace-pre-wrap leading-relaxed">{selectedResult.reasoning}</p>
                  </div>

                  {/* Verification Notes */}
                  {selectedResult.verification_notes && (
                    <div className="card p-4 sm:p-6 bg-gradient-to-r from-green-600/10 to-transparent border-l-4 border-green-500">
                      <div className="flex items-center space-x-2 mb-3">
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                        <h3 className="text-base sm:text-lg font-bold text-green-600">Triple Verification Notes</h3>
                      </div>
                      <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{selectedResult.verification_notes}</p>
                    </div>
                  )}

                  {/* Keywords */}
                  {selectedResult.all_keywords && selectedResult.all_keywords.length > 0 && (
                    <div className="card p-4 sm:p-6 border-l-4 border-red-500">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2">
                          <Search className="h-5 w-5 text-red-600" />
                          <h3 className="text-base sm:text-lg font-bold text-gray-900">
                            Detected Keywords
                          </h3>
                        </div>
                        <Badge variant="error">{selectedResult.all_keywords.length}</Badge>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {selectedResult.all_keywords.map((keyword, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1.5 bg-gradient-to-r from-red-600/10 to-blue-600/10 text-gray-900 rounded-lg text-sm font-semibold border border-gray-200 hover:scale-105 transition-transform duration-200"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Safety Assessment Card */}
                  {selectedResult.safety_check && (
                    <div className="card p-4 sm:p-6 border-l-4 border-green-500">
                      <div className="flex items-center space-x-2 mb-4">
                        <Shield className="h-5 w-5 text-green-600" />
                        <h3 className="text-base sm:text-lg font-bold text-gray-900">Safety Assessment</h3>
                      </div>
                      <div className={`p-4 rounded-xl ${
                        selectedResult.safety_check.is_safe
                          ? 'bg-gradient-to-r from-green-600/10 to-transparent border-2 border-green-500/30'
                          : 'bg-gradient-to-r from-red-500/10 to-transparent border-2 border-red-500/30'
                      }`}>
                        <div className="flex items-center space-x-3 mb-3">
                          {selectedResult.safety_check.is_safe ? (
                            <CheckCircle2 className="h-6 w-6 text-green-600" />
                          ) : (
                            <AlertTriangle className="h-6 w-6 text-red-600" />
                          )}
                          <span className={`text-lg font-bold ${
                            selectedResult.safety_check.is_safe ? 'text-green-600' : 'text-red-700'
                          }`}>
                            {selectedResult.safety_check.is_safe ? 'Content Safe' : 'Content Flagged'}
                          </span>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            selectedResult.safety_check.is_safe
                              ? 'bg-green-600/20 text-green-600'
                              : 'bg-red-500/20 text-red-700'
                          }`}>
                            {Math.round(selectedResult.safety_check.confidence * 100)}% confidence
                          </span>
                        </div>
                        <p className={`text-sm sm:text-base leading-relaxed ${selectedResult.safety_check.is_safe ? 'text-gray-700' : 'text-red-700'}`}>
                          {selectedResult.safety_check.details}
                        </p>
                        {selectedResult.safety_check.flags.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 mb-2">Detected Flags:</p>
                            <div className="flex flex-wrap gap-2">
                              {selectedResult.safety_check.flags.map((flag, idx) => (
                                <span key={idx} className="px-3 py-1 bg-white border border-red-300 text-red-700 rounded-lg text-xs font-semibold shadow-sm">
                                  {flag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Document Context Analysis */}
                  {selectedResult.document_context && (
                    <div className="card p-4 sm:p-6 border-l-4 border-blue-500">
                      <div className="flex items-center space-x-2 mb-4">
                        <FileText className="h-5 w-5 text-blue-600" />
                        <h3 className="text-base sm:text-lg font-bold text-gray-900">Document Context Analysis</h3>
                        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-600/20 text-blue-600">
                          {Math.round(selectedResult.document_context.confidence * 100)}% confidence
                        </span>
                      </div>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-4 bg-gradient-to-br from-blue-600/5 to-transparent rounded-lg border border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 mb-1">Context Type</p>
                            <p className="text-sm font-bold text-gray-900">{selectedResult.document_context.context_type}</p>
                          </div>
                          <div className="p-4 bg-gradient-to-br from-blue-600/5 to-transparent rounded-lg border border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 mb-1">Content Purpose</p>
                            <p className="text-sm font-bold text-gray-900">{selectedResult.document_context.content_purpose}</p>
                          </div>
                          <div className="p-4 bg-gradient-to-br from-blue-600/5 to-transparent rounded-lg border border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 mb-1">Intended Audience</p>
                            <p className="text-sm font-bold text-gray-900">{selectedResult.document_context.intended_audience}</p>
                          </div>
                          <div className="p-4 bg-gradient-to-br from-blue-600/5 to-transparent rounded-lg border border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 mb-1">Is Proprietary</p>
                            <p className={`text-sm font-bold ${selectedResult.document_context.is_proprietary ? 'text-red-600' : 'text-green-600'}`}>
                              {selectedResult.document_context.is_proprietary ? 'Yes - Proprietary Content' : 'No - Public Discussion'}
                            </p>
                          </div>
                        </div>
                        <div className="p-4 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200">
                          <p className="text-xs font-semibold text-gray-600 mb-2">Context Reasoning</p>
                          <p className="text-sm text-gray-700 leading-relaxed">{selectedResult.document_context.reasoning}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Keyword Relevance Scoring */}
                  {selectedResult.keyword_relevances && selectedResult.keyword_relevances.length > 0 && (
                    <div className="card p-4 sm:p-6 border-l-4 border-red-500">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2">
                          <Search className="h-5 w-5 text-red-600" />
                          <h3 className="text-base sm:text-lg font-bold text-gray-900">Keyword Relevance Analysis</h3>
                        </div>
                        <Badge variant="error">{selectedResult.keyword_relevances.length} keywords analyzed</Badge>
                      </div>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {selectedResult.keyword_relevances.map((kw, idx) => (
                          <div key={idx} className="p-4 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-3">
                                <span className="px-3 py-1 bg-gradient-to-r from-red-600/10 to-blue-600/10 text-gray-900 rounded-lg text-sm font-bold">
                                  {kw.keyword}
                                </span>
                                <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                  kw.relationship_type === 'IS' ? 'bg-red-500/20 text-red-700' :
                                  kw.relationship_type === 'DISCUSSES' ? 'bg-amber-500/20 text-amber-700' :
                                  'bg-green-500/20 text-green-700'
                                }`}>
                                  {kw.relationship_type}
                                </span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <span className="text-xs text-gray-600">Relevance:</span>
                                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-red-600 to-blue-600 rounded-full"
                                    style={{ width: `${kw.relevance_score * 100}%` }}
                                  ></div>
                                </div>
                                <span className="text-xs font-bold text-gray-900">{Math.round(kw.relevance_score * 100)}%</span>
                              </div>
                            </div>
                            <p className="text-xs text-gray-600 mb-2 italic">Page {kw.page}</p>
                            <p className="text-sm text-gray-700 mb-2 line-clamp-2">{kw.context_window}</p>
                            <p className="text-xs text-gray-600 leading-relaxed">{kw.reasoning}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Dual Verification Results */}
                  {selectedResult.secondary_classification && (
                    <div className="card p-4 sm:p-6 border-l-4 border-green-500">
                      <div className="flex items-center space-x-2 mb-4">
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                        <h3 className="text-base sm:text-lg font-bold text-gray-900">Dual AI Verification</h3>
                        {selectedResult.consensus !== undefined && (
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            selectedResult.consensus
                              ? 'bg-green-600/20 text-green-600'
                              : 'bg-amber-500/20 text-amber-700'
                          }`}>
                            {selectedResult.consensus ? 'Consensus Reached' : 'Disagreement Detected'}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-gradient-to-br from-blue-600/5 to-transparent rounded-lg border-2 border-blue-500/30">
                          <p className="text-xs font-semibold text-gray-600 mb-2">Primary Classification</p>
                          <p className="text-lg font-bold text-gray-900 mb-1">{selectedResult.classification}</p>
                          <p className="text-sm text-gray-600">{Math.round(selectedResult.confidence * 100)}% confidence</p>
                        </div>
                        <div className="p-4 bg-gradient-to-br from-green-600/5 to-transparent rounded-lg border-2 border-green-500/30">
                          <p className="text-xs font-semibold text-gray-600 mb-2">Secondary Classification</p>
                          <p className="text-lg font-bold text-gray-900 mb-1">{selectedResult.secondary_classification}</p>
                          <p className="text-sm text-gray-600">{Math.round((selectedResult.secondary_confidence || 0) * 100)}% confidence</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Processing Progress */}
                  {selectedResult.progress_steps && selectedResult.progress_steps.length > 0 && (
                    <div className="card p-4 sm:p-6 border-l-4 border-gray-900">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2">
                          <Zap className="h-5 w-5 text-gray-900" />
                          <h3 className="text-base sm:text-lg font-bold text-gray-900">Classification Workflow</h3>
                        </div>
                        <Badge variant="neutral">{selectedResult.progress_steps.length} steps</Badge>
                      </div>
                      <div className="space-y-2">
                        {selectedResult.progress_steps.map((step, idx) => {
                          const cleanStep = step.replace(/^[⚠✓]\s*/, '');
                          const isWarning = step.includes('⚠') || step.toLowerCase().includes('warning');
                          const isSuccess = step.includes('✓') || step.toLowerCase().includes('complete');

                          return (
                            <div key={idx} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                              <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                isSuccess ? 'bg-green-600 text-white' :
                                isWarning ? 'bg-amber-500 text-white' :
                                'bg-blue-600 text-white'
                              }`}>
                                {idx + 1}
                              </div>
                              <p className="text-sm text-gray-700 leading-relaxed flex-1">{cleanStep}</p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {detailTab === 'text-analysis' && selectedResult.text_segments && (
                <TextSegmentViewer 
                  segments={selectedResult.text_segments}
                  fullText={selectedResult.full_text}
                />
              )}

              {detailTab === 'images' && selectedResult.image_analyses && (
                <ImageAnalysisViewer 
                  imageAnalyses={selectedResult.image_analyses}
                  pageImages={selectedResult.page_images_base64}
                />
              )}

              {detailTab === 'pages' && selectedResult.page_images_base64 && (
                <DocumentPageViewer 
                  pageImages={selectedResult.page_images_base64}
                  pageCount={selectedResult.page_count}
                  filename={selectedResult.filename}
                />
              )}

              {detailTab === 'evidence' && selectedResult.evidence && (
                <EvidenceViewer evidence={selectedResult.evidence} />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {reviewingResult && (
        <ReviewModal
          result={reviewingResult}
          onClose={() => setReviewingResult(null)}
          onSubmit={handleReviewSubmit}
        />
      )}

      {/* Notification Center */}
      <NotificationCenter
        isOpen={showNotifications}
        onClose={() => setShowNotifications(false)}
      />
    </div>
  );
}

export default App;
