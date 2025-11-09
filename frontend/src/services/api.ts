/**
 * API client for backend communication
 */
import axios from 'axios';
import type {
  UploadResponse,
  ClassificationResult,
  HITLFeedback,
  ReviewQueueItem,
  BatchProcessRequest,
  BatchProcessStatus,
} from '../types/classification';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Upload endpoints
export const uploadApi = {
  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadResponse>('/api/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  uploadBatch: async (files: File[]): Promise<UploadResponse[]> => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await api.post<UploadResponse[]>('/api/upload/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  deleteDocument: async (documentId: string): Promise<void> => {
    await api.delete(`/api/upload/${documentId}`);
  },

  listUploads: async () => {
    const response = await api.get('/api/upload/list');
    return response.data;
  },
};

// Classification endpoints
export const classifyApi = {
  classifyDocument: async (
    documentId: string,
    enableDualVerification: boolean = false
  ): Promise<ClassificationResult> => {
    const response = await api.post<ClassificationResult>('/api/classify/', {
      document_id: documentId,
      enable_dual_verification: enableDualVerification,
    });
    return response.data;
  },

  getClassificationResult: async (documentId: string): Promise<ClassificationResult> => {
    const response = await api.get<ClassificationResult>(`/api/classify/${documentId}`);
    return response.data;
  },

  classifyBatch: async (request: BatchProcessRequest): Promise<BatchProcessStatus> => {
    const response = await api.post<BatchProcessStatus>('/api/classify/batch', request);
    return response.data;
  },

  getAllResults: async () => {
    const response = await api.get('/api/classify/results/all');
    return response.data;
  },

  deleteResult: async (documentId: string): Promise<void> => {
    await api.delete(`/api/classify/results/${documentId}`);
  },

  deleteAllResults: async (): Promise<void> => {
    await api.delete('/api/classify/results/all/clear');
  },

  /**
   * Subscribe to real-time classification progress updates via Server-Sent Events (SSE)
   * with automatic reconnection and error recovery
   */
  subscribeToProgress: (
    documentId: string,
    onProgress: (message: string) => void,
    onComplete: () => void,
    onError: (error?: string) => void
  ): (() => void) => {
    const url = `${API_BASE_URL}/api/classify/progress/${documentId}`;
    console.log('[SSE] Connecting to:', url);

    let eventSource: EventSource | null = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;
    const reconnectDelay = 2000; // 2 seconds
    let isManuallyCloseD = false;
    let reconnectTimer: number | null = null;

    const connect = () => {
      if (isManuallyCloseD) return;

      try {
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
          console.log('[SSE] Connection opened:', documentId);
          reconnectAttempts = 0; // Reset on successful connection
        };

        eventSource.onmessage = (event) => {
          try {
            // Handle keepalive comments
            if (event.data.startsWith(':')) {
              console.log('[SSE] Keepalive received');
              return;
            }

            const data = JSON.parse(event.data);
            
            if (data.type === 'connected') {
              console.log('[SSE] ✅ Connection confirmed and ready:', documentId);
            } else if (data.type === 'progress') {
              console.log('[SSE] 📨 Progress:', data.message.substring(0, 60));
              onProgress(data.message);
            } else if (data.type === 'complete') {
              console.log('[SSE] ✅ Classification complete:', documentId);
              onComplete();
              cleanup();
            } else if (data.type === 'error') {
              console.error('[SSE] ❌ Server reported error:', documentId);
              onError('Server reported an error during classification');
              cleanup();
            }
          } catch (error) {
            console.error('[SSE] Error parsing message:', error);
            // Don't close connection for parse errors, just skip this message
          }
        };

        eventSource.onerror = (error) => {
          console.error('[SSE] Connection error:', error);

          // If we've already closed, don't try to reconnect
          if (eventSource?.readyState === EventSource.CLOSED) {
            console.log('[SSE] Connection closed');

            // Attempt reconnection if not manually closed
            if (!isManuallyCloseD && reconnectAttempts < maxReconnectAttempts) {
              reconnectAttempts++;
              console.log(`[SSE] Attempting reconnection ${reconnectAttempts}/${maxReconnectAttempts}`);

              reconnectTimer = setTimeout(() => {
                eventSource?.close();
                connect();
              }, reconnectDelay);
            } else if (reconnectAttempts >= maxReconnectAttempts) {
              console.error('[SSE] Max reconnection attempts reached');
              onError('Connection lost. Please refresh the page and try again.');
              cleanup();
            }
          }
        };
      } catch (error) {
        console.error('[SSE] Error creating EventSource:', error);
        onError('Failed to establish connection');
      }
    };

    const cleanup = () => {
      isManuallyCloseD = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      console.log('[SSE] Cleanup complete:', documentId);
    };

    // Initial connection
    connect();

    // Return cleanup function
    return cleanup;
  },
};

// HITL endpoints
export const hitlApi = {
  getReviewQueue: async () => {
    const response = await api.get<{
      queue: ReviewQueueItem[];
      count: number;
      unsafe_count: number;
    }>('/api/hitl/queue');
    return response.data;
  },

  submitFeedback: async (feedback: HITLFeedback) => {
    const response = await api.post('/api/hitl/feedback', feedback);
    return response.data;
  },

  quickApprove: async (documentId: string, reviewerId: string = 'user') => {
    const response = await api.post(`/api/hitl/approve/${documentId}`, null, {
      params: { reviewer_id: reviewerId },
    });
    return response.data;
  },

  quickReject: async (
    documentId: string,
    correctedClassification: string,
    reviewerId: string = 'user',
    notes: string = ''
  ) => {
    const response = await api.post(`/api/hitl/reject/${documentId}`, null, {
      params: {
        corrected_classification: correctedClassification,
        reviewer_id: reviewerId,
        notes: notes,
      },
    });
    return response.data;
  },

  getFeedback: async (documentId: string) => {
    const response = await api.get(`/api/hitl/feedback/${documentId}`);
    return response.data;
  },

  getAllFeedback: async () => {
    const response = await api.get('/api/hitl/feedback/all');
    return response.data;
  },

  getStats: async () => {
    const response = await api.get('/api/hitl/stats');
    return response.data;
  },
};

export default api;
