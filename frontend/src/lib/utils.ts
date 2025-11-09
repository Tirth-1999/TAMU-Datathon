import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { ClassificationCategory, SafetyFlag } from '../types/classification';

/**
 * Merge Tailwind classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Get color for classification category
 */
export function getClassificationColor(category: ClassificationCategory): string {
  switch (category) {
    case ClassificationCategory.PUBLIC:
      return 'bg-green-100 text-green-800 border-green-300';
    case ClassificationCategory.CONFIDENTIAL:
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case ClassificationCategory.HIGHLY_SENSITIVE:
      return 'bg-red-100 text-red-800 border-red-300';
    case ClassificationCategory.UNSAFE:
      return 'bg-purple-100 text-purple-800 border-purple-300';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300';
  }
}

/**
 * Get confidence color based on score
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-600';
  if (confidence >= 0.7) return 'text-yellow-600';
  return 'text-red-600';
}

/**
 * Get safety flag color
 */
export function getSafetyFlagColor(flag: SafetyFlag): string {
  if (flag === SafetyFlag.NONE) return 'bg-green-100 text-green-800';
  if (flag === SafetyFlag.CHILD_SAFETY) return 'bg-red-100 text-red-800';
  return 'bg-orange-100 text-orange-800';
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format processing time
 */
export function formatProcessingTime(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${minutes}m ${secs}s`;
}

/**
 * Format confidence percentage
 */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}
