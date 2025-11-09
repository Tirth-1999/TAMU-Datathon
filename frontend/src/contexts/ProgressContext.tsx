/**
 * Progress Context
 *
 * Global state management for document classification progress.
 * Provides real-time updates, history tracking, and persistence.
 *
 * Features:
 * - Track multiple active classifications simultaneously
 * - Store progress history (last 50 operations)
 * - Persist to localStorage
 * - Real-time SSE integration
 * - Export functionality
 *
 * @example
 * const { addProgress, activeOperations, history } = useProgress();
 * addProgress(documentId, 'Processing started...');
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface ProgressStep {
  /** Unique step ID */
  id: string;

  /** Step message */
  message: string;

  /** Timestamp */
  timestamp: number;

  /** Step type */
  type?: 'info' | 'success' | 'warning' | 'error';
}

export interface ProgressOperation {
  /** Document ID */
  documentId: string;

  /** Document filename */
  filename?: string;

  /** Status of operation */
  status: 'active' | 'completed' | 'error';

  /** Progress steps */
  steps: ProgressStep[];

  /** Start time */
  startedAt: number;

  /** End time (if completed) */
  completedAt?: number;

  /** Error message (if error) */
  error?: string;
}

interface ProgressContextValue {
  /** All active operations */
  activeOperations: Map<string, ProgressOperation>;

  /** Operation history (last 50) */
  history: ProgressOperation[];

  /** Add a new operation */
  startOperation: (documentId: string, filename?: string) => void;

  /** Add progress step to an operation */
  addProgress: (documentId: string, message: string, type?: ProgressStep['type']) => void;

  /** Mark operation as completed */
  completeOperation: (documentId: string) => void;

  /** Mark operation as error */
  errorOperation: (documentId: string, error: string) => void;

  /** Remove operation from active list */
  removeOperation: (documentId: string) => void;

  /** Clear all history */
  clearHistory: () => void;

  /** Export history as JSON */
  exportHistory: () => string;

  /** Get operation by document ID */
  getOperation: (documentId: string) => ProgressOperation | undefined;
}

const ProgressContext = createContext<ProgressContextValue | undefined>(undefined);

const STORAGE_KEY = 'classification_history';
const ACTIVE_STORAGE_KEY = 'classification_active';
const MAX_HISTORY = 50;

/**
 * Progress Provider Component
 */
export const ProgressProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeOperations, setActiveOperations] = useState<Map<string, ProgressOperation>>(() => {
    // Load active operations from localStorage on mount
    try {
      const stored = localStorage.getItem(ACTIVE_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Convert array back to Map
        return new Map(parsed.map((op: ProgressOperation) => [op.documentId, op]));
      }
    } catch (error) {
      console.error('Failed to load active operations:', error);
    }
    return new Map();
  });
  
  const [history, setHistory] = useState<ProgressOperation[]>(() => {
    // Load history from localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Persist active operations to localStorage whenever they change
  useEffect(() => {
    try {
      const activeArray = Array.from(activeOperations.values());
      localStorage.setItem(ACTIVE_STORAGE_KEY, JSON.stringify(activeArray));
    } catch (error) {
      console.error('Failed to save active operations:', error);
    }
  }, [activeOperations]);

  // Persist history to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      console.error('Failed to save progress history:', error);
    }
  }, [history]);

  // On mount: Check for stale active operations (older than 5 minutes)
  // and move them to history as interrupted
  useEffect(() => {
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;
    
    setActiveOperations((prev) => {
      const newMap = new Map(prev);
      const staleOps: ProgressOperation[] = [];
      
      prev.forEach((op) => {
        if (now - op.startedAt > fiveMinutes) {
          // Mark as interrupted and move to history
          staleOps.push({
            ...op,
            status: 'error',
            completedAt: now,
            error: 'Operation interrupted (page refresh)',
          });
          newMap.delete(op.documentId);
        }
      });
      
      if (staleOps.length > 0) {
        console.log(`[Progress] Moving ${staleOps.length} stale operations to history`);
        setHistory((prevHistory) => [...staleOps, ...prevHistory].slice(0, MAX_HISTORY));
      }
      
      return newMap;
    });
  }, []); // Run only once on mount

  /**
   * Start a new operation
   */
  const startOperation = useCallback((documentId: string, filename?: string) => {
    const operation: ProgressOperation = {
      documentId,
      filename,
      status: 'active',
      steps: [],
      startedAt: Date.now(),
    };

    setActiveOperations((prev) => {
      const newMap = new Map(prev);
      newMap.set(documentId, operation);
      return newMap;
    });
  }, []);

  /**
   * Add a progress step
   */
  const addProgress = useCallback(
    (documentId: string, message: string, type: ProgressStep['type'] = 'info') => {
      setActiveOperations((prev) => {
        const newMap = new Map(prev);
        const operation = newMap.get(documentId);

        if (operation) {
          const step: ProgressStep = {
            id: `${documentId}-${Date.now()}-${Math.random()}`,
            message,
            timestamp: Date.now(),
            type,
          };

          operation.steps.push(step);
          newMap.set(documentId, { ...operation });
        }

        return newMap;
      });
    },
    []
  );

  /**
   * Complete an operation
   */
  const completeOperation = useCallback((documentId: string) => {
    setActiveOperations((prev) => {
      const newMap = new Map(prev);
      const operation = newMap.get(documentId);

      if (!operation) {
        // Operation already completed or doesn't exist
        console.log(`[Progress] Operation ${documentId} already completed or not found`);
        return prev;
      }

      const completedOperation: ProgressOperation = {
        ...operation,
        status: 'completed',
        completedAt: Date.now(),
      };

      // Add to history (check for duplicates by documentId + startedAt)
      setHistory((prevHistory) => {
        // Prevent duplicates: check if this operation is already in history
        const isDuplicate = prevHistory.some(
          (h) => h.documentId === documentId && h.startedAt === operation.startedAt
        );
        
        if (isDuplicate) {
          console.log(`[Progress] Operation ${documentId} already in history`);
          return prevHistory; // Don't add duplicate
        }
        
        console.log(`[Progress] Adding operation ${documentId} to history`);
        const newHistory = [completedOperation, ...prevHistory].slice(0, MAX_HISTORY);
        return newHistory;
      });

      // Remove from active
      newMap.delete(documentId);
      console.log(`[Progress] Removed operation ${documentId} from active`);

      return newMap;
    });
  }, []);

  /**
   * Mark operation as error
   */
  const errorOperation = useCallback((documentId: string, error: string) => {
    setActiveOperations((prev) => {
      const newMap = new Map(prev);
      const operation = newMap.get(documentId);

      if (!operation) {
        // Operation already completed or doesn't exist
        console.log(`[Progress] Error for operation ${documentId} but operation not found`);
        return prev;
      }

      const erroredOperation: ProgressOperation = {
        ...operation,
        status: 'error',
        completedAt: Date.now(),
        error,
      };

      // Add to history (check for duplicates by documentId + startedAt)
      setHistory((prevHistory) => {
        // Prevent duplicates: check if this operation is already in history
        const isDuplicate = prevHistory.some(
          (h) => h.documentId === documentId && h.startedAt === operation.startedAt
        );
        
        if (isDuplicate) {
          console.log(`[Progress] Error operation ${documentId} already in history`);
          return prevHistory; // Don't add duplicate
        }
        
        console.log(`[Progress] Adding error operation ${documentId} to history`);
        const newHistory = [erroredOperation, ...prevHistory].slice(0, MAX_HISTORY);
        return newHistory;
      });

      // Remove from active
      newMap.delete(documentId);
      console.log(`[Progress] Removed error operation ${documentId} from active`);

      return newMap;
    });
  }, []);

  /**
   * Remove an operation
   */
  const removeOperation = useCallback((documentId: string) => {
    setActiveOperations((prev) => {
      const newMap = new Map(prev);
      newMap.delete(documentId);
      return newMap;
    });
  }, []);

  /**
   * Clear all history
   */
  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(ACTIVE_STORAGE_KEY); // Also clear active operations
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  }, []);

  /**
   * Export history as JSON
   */
  const exportHistory = useCallback(() => {
    return JSON.stringify(history, null, 2);
  }, [history]);

  /**
   * Get operation by document ID
   */
  const getOperation = useCallback(
    (documentId: string) => {
      return activeOperations.get(documentId);
    },
    [activeOperations]
  );

  const value: ProgressContextValue = {
    activeOperations,
    history,
    startOperation,
    addProgress,
    completeOperation,
    errorOperation,
    removeOperation,
    clearHistory,
    exportHistory,
    getOperation,
  };

  return <ProgressContext.Provider value={value}>{children}</ProgressContext.Provider>;
};

/**
 * Hook to access progress context
 */
export const useProgress = (): ProgressContextValue => {
  const context = useContext(ProgressContext);
  if (!context) {
    throw new Error('useProgress must be used within a ProgressProvider');
  }
  return context;
};

/**
 * Hook to access progress for a specific document
 */
export const useDocumentProgress = (documentId: string): ProgressOperation | undefined => {
  const { getOperation } = useProgress();
  const [operation, setOperation] = useState<ProgressOperation | undefined>();

  useEffect(() => {
    setOperation(getOperation(documentId));
  }, [documentId, getOperation]);

  return operation;
};

export default ProgressContext;
