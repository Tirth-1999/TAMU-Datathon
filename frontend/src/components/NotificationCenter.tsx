/**
 * Notification Center
 *
 * Slide-in panel from right showing all active classifications and history.
 * Provides detailed real-time progress updates and export functionality.
 *
 * Features:
 * - Tabbed interface (Active | History)
 * - Real-time progress steps
 * - Export history as JSON
 * - Clear history
 * - Responsive (full screen on mobile)
 *
 * @example
 * <NotificationCenter isOpen={showNotifications} onClose={() => setShowNotifications(false)} />
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Download,
  Trash2,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
  FileText,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useProgress, ProgressOperation } from '../contexts/ProgressContext';
import { Button } from './ui';

export interface NotificationCenterProps {
  /** Whether panel is open */
  isOpen: boolean;

  /** Callback when panel should close */
  onClose: () => void;
}

type Tab = 'active' | 'history';

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ isOpen, onClose }) => {
  const { activeOperations, history, clearHistory, exportHistory } = useProgress();
  const [activeTab, setActiveTab] = useState<Tab>('active');
  const [expandedOperations, setExpandedOperations] = useState<Set<string>>(new Set());

  // Auto-expand active operations to show progress steps
  useEffect(() => {
    const activeOps = Array.from(activeOperations.keys());
    setExpandedOperations((prev) => {
      const newSet = new Set(prev);
      activeOps.forEach(docId => newSet.add(docId));
      return newSet;
    });
  }, [activeOperations]);

  // Auto-switch to history tab when no active operations
  useEffect(() => {
    if (activeOperations.size === 0 && activeTab === 'active') {
      setActiveTab('history');
    }
  }, [activeOperations.size, activeTab]);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Handle export
  const handleExport = () => {
    const json = exportHistory();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `classification-history-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Handle clear history
  const handleClearHistory = () => {
    if (confirm('Are you sure you want to clear all notification history? This cannot be undone.')) {
      clearHistory();
    }
  };

  // Toggle operation expansion
  const toggleExpanded = (documentId: string) => {
    setExpandedOperations((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(documentId)) {
        newSet.delete(documentId);
      } else {
        newSet.add(documentId);
      }
      return newSet;
    });
  };

  if (!isOpen) return null;

  const activeOps = Array.from(activeOperations.values());

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 animate-fadeIn"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={`
          fixed inset-y-0 right-0 z-50
          w-full md:w-[600px] md:max-w-[90vw]
          bg-white shadow-2xl
          flex flex-col
          ${isOpen ? 'animate-slide-in-right' : ''}
        `}
        role="dialog"
        aria-modal="true"
        aria-label="Notification Center"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-gray-700" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Notification Center</h2>
              <p className="text-sm text-gray-600">
                {activeOps.length} active {activeOps.length === 1 ? 'operation' : 'operations'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close notification center"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-4 sm:px-6">
          <button
            onClick={() => setActiveTab('active')}
            className={`
              relative px-4 py-3 font-medium text-sm transition-colors
              ${
                activeTab === 'active'
                  ? 'text-gray-900'
                  : 'text-gray-600 hover:text-gray-900'
              }
            `}
          >
            Active {activeOps.length > 0 && `(${activeOps.length})`}
            {activeTab === 'active' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-900" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`
              relative px-4 py-3 font-medium text-sm transition-colors
              ${
                activeTab === 'history'
                  ? 'text-gray-900'
                  : 'text-gray-600 hover:text-gray-900'
              }
            `}
          >
            History {history.length > 0 && `(${history.length})`}
            {activeTab === 'history' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-900" />
            )}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {activeTab === 'active' ? (
            activeOps.length > 0 ? (
              activeOps.map((operation) => (
                <OperationCard
                  key={operation.documentId}
                  operation={operation}
                  isExpanded={expandedOperations.has(operation.documentId)}
                  onToggleExpand={() => toggleExpanded(operation.documentId)}
                />
              ))
            ) : (
              <EmptyState
                icon={<Activity className="h-12 w-12 text-gray-400" />}
                title="No active operations"
                description="All classifications have completed. Check history for past operations."
              />
            )
          ) : history.length > 0 ? (
            history.map((operation) => (
              <OperationCard
                key={`${operation.documentId}-${operation.startedAt}`}
                operation={operation}
                isExpanded={expandedOperations.has(operation.documentId)}
                onToggleExpand={() => toggleExpanded(operation.documentId)}
              />
            ))
          ) : (
            <EmptyState
              icon={<Clock className="h-12 w-12 text-gray-400" />}
              title="No history yet"
              description="Past classification operations will appear here."
            />
          )}
        </div>

        {/* Footer (History tab only) */}
        {activeTab === 'history' && history.length > 0 && (
          <div className="border-t border-gray-200 p-4 sm:p-6 flex gap-2">
            <Button variant="ghost" icon={<Download />} onClick={handleExport}>
              Export
            </Button>
            <Button variant="ghost" icon={<Trash2 />} onClick={handleClearHistory}>
              Clear History
            </Button>
          </div>
        )}
      </div>
    </>
  );
};

/**
 * Operation Card Component
 */
interface OperationCardProps {
  operation: ProgressOperation;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const OperationCard: React.FC<OperationCardProps> = ({ operation, isExpanded, onToggleExpand }) => {
  const { documentId, filename, status, steps, startedAt, completedAt, error } = operation;

  const duration = completedAt ? (completedAt - startedAt) / 1000 : null;

  const statusConfig = {
    active: { icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50' },
    completed: { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50' },
    error: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50' },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;

  return (
    <div className="card p-4">
      {/* Header */}
      <button
        onClick={onToggleExpand}
        className="w-full flex items-start justify-between gap-3 text-left hover:bg-gray-50 -m-4 p-4 rounded-lg transition-colors"
      >
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className={`p-2 rounded-lg ${config.bg}`}>
            <StatusIcon className={`h-4 w-4 ${config.color}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <span className="text-sm font-medium text-gray-900 truncate">
                {filename || documentId}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-600">
              <span>{steps.length} steps</span>
              <span>•</span>
              <span>{new Date(startedAt).toLocaleTimeString()}</span>
              {duration && (
                <>
                  <span>•</span>
                  <span>{duration.toFixed(1)}s</span>
                </>
              )}
            </div>
            {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
          </div>
        </div>
        <div className="flex-shrink-0">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded Steps */}
      {isExpanded && steps.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 space-y-2 max-h-60 overflow-y-auto">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-start gap-2 text-sm">
              <div className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center mt-0.5">
                <span className="text-xs font-medium text-gray-600">{index + 1}</span>
              </div>
              <div className="flex-1">
                <p className="text-gray-700">{step.message}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {new Date(step.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Empty State Component
 */
interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description }) => {
  return (
    <div className="text-center py-12">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
};

export default NotificationCenter;
