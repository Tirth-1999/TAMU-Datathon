/**
 * File Upload Component - Modern SaaS Design
 *
 * Drag-and-drop file upload with mobile-optimized controls
 * and design system integration.
 */
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadApi } from '../services/api';
import type { UploadResponse } from '../types/classification';
import { formatFileSize } from '../lib/utils';
// import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

interface FileUploadProps {
  onUploadComplete?: (responses: UploadResponse[]) => void;
  onUploadStart?: () => void;
  maxFiles?: number;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUploadComplete,
  onUploadStart,
  maxFiles = 10,
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadResponse[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploading(true);
      setErrors([]);
      onUploadStart?.();

      try {
        const responses = await uploadApi.uploadBatch(acceptedFiles);

        setUploadedFiles(prev => [...prev, ...responses.filter(r => r.status === 'success')]);

        const uploadErrors = responses
          .filter(r => r.status === 'error')
          .map(r => `${r.filename}: ${r.message}`);

        if (uploadErrors.length > 0) {
          setErrors(uploadErrors);
        }

        onUploadComplete?.(responses);
      } catch (error: any) {
        setErrors([error.message || 'Upload failed']);
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete, onUploadStart]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'application/vnd.ms-powerpoint': ['.ppt'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
    },
    maxFiles,
    disabled: uploading,
  });

  const removeFile = (documentId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.document_id !== documentId));
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Dropzone - Modern Design */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer
          transition-all duration-200 overflow-hidden
          ${isDragActive
            ? 'border-blue-500 bg-blue-50 shadow-md scale-[1.02]'
            : 'border-gray-300 hover:border-gray-400 hover:shadow-sm bg-gray-50/50'
          }
          ${uploading ? 'opacity-60 cursor-not-allowed pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} />

        {/* Upload Icon */}
        <div className={`
          mx-auto w-16 h-16 sm:w-20 sm:h-20 rounded-full
          flex items-center justify-center mb-4 sm:mb-6
          transition-all duration-200
          ${isDragActive
            ? 'bg-blue-500 animate-pulse'
            : 'bg-gray-200'
          }
        `}>
          <Upload className={`h-8 w-8 sm:h-10 sm:w-10 ${isDragActive ? 'text-white' : 'text-gray-600'}`} />
        </div>

        {isDragActive ? (
          <div className="animate-fadeIn">
            <p className="text-lg sm:text-xl font-semibold text-gray-900 mb-1 sm:mb-2">Drop files here</p>
            <p className="text-sm text-gray-600">Release to upload your documents</p>
          </div>
        ) : (
          <div>
            <p className="text-lg sm:text-xl font-semibold text-gray-900 mb-1 sm:mb-2">
              Drag & drop documents
            </p>
            <p className="text-sm text-gray-600 mb-3 sm:mb-4">
              or click to browse
            </p>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 bg-white border border-gray-200 rounded-lg text-xs sm:text-sm text-gray-700">
              <FileText className="h-3.5 w-3.5 sm:h-4 sm:w-4 flex-shrink-0" />
              <span className="hidden sm:inline">Supports: PDF, Word, Excel, PowerPoint, Images, Text (max {maxFiles} files)</span>
              <span className="sm:hidden">PDF, Word, Excel, PPT, Images, Text</span>
            </div>
          </div>
        )}

        {uploading && (
          <div className="mt-4 sm:mt-6 animate-fadeIn">
            <Loader2 className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-blue-600 animate-spin" />
            <p className="text-sm font-medium text-gray-700 mt-3">Processing documents...</p>
          </div>
        )}
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="card p-4 sm:p-5 bg-red-50 border-l-4 border-red-500">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 p-2 bg-red-100 rounded-lg">
              <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 text-red-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-red-900 mb-2">Upload Errors</h4>
              <ul className="text-sm text-red-700 space-y-1">
                {errors.map((error, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-red-400 flex-shrink-0">•</span>
                    <span className="break-words">{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <div className="card overflow-hidden animate-slideUp">
          {/* Header */}
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 sm:h-5 sm:w-5 text-green-600" />
                <h3 className="text-sm font-semibold text-gray-900">
                  Successfully Uploaded
                </h3>
              </div>
              <Badge variant="neutral">{uploadedFiles.length}</Badge>
            </div>
          </div>

          {/* File List */}
          <ul className="divide-y divide-gray-200">
            {uploadedFiles.map((file, index) => (
              <li
                key={file.document_id}
                className="px-4 sm:px-6 py-3 sm:py-4 hover:bg-gray-50 transition-colors group"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-start gap-3">
                  {/* File Icon */}
                  <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <FileText className="h-5 w-5 text-green-600" />
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.filename}
                    </p>
                    <div className="flex items-center gap-2 sm:gap-3 mt-1 text-xs text-gray-600 flex-wrap">
                      <span>{formatFileSize(file.file_size)}</span>
                      {file.metadata && (
                        <>
                          <span className="hidden sm:inline">•</span>
                          <span className="hidden sm:inline">{file.metadata.format}</span>
                          {file.metadata.page_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{file.metadata.page_count} pages</span>
                            </>
                          )}
                          {file.metadata.image_count > 0 && (
                            <>
                              <span className="hidden sm:inline">•</span>
                              <span className="hidden sm:inline">{file.metadata.image_count} images</span>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Status Badge - hidden on mobile, shown on desktop */}
                  <div className="hidden md:flex flex-shrink-0">
                    <Badge variant="success" icon={<CheckCircle className="h-3 w-3" />}>
                      Ready
                    </Badge>
                  </div>

                  {/* Delete Button - ALWAYS VISIBLE on mobile, hover on desktop */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.document_id);
                    }}
                    className="
                      flex-shrink-0 p-2 rounded-lg transition-all
                      text-gray-400 hover:text-red-600 hover:bg-red-50
                      md:opacity-0 md:group-hover:opacity-100
                      min-h-[44px] min-w-[44px] flex items-center justify-center
                      -mr-2
                    "
                    title="Remove file"
                    aria-label={`Remove ${file.filename}`}
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
