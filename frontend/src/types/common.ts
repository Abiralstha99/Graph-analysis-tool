// Common types used throughout the application

export interface User {
  id?: number;
  username: string;
  name?: string;
  email?: string;
  avatarUrl?: string;
  backgroundUrl?: string;
}

export interface ParsedCSV {
  filename: string;
  x: number[];
  y: number[];
  rawContent: string;
  isFavorite?: boolean;
}

// Unified Sample interface used across all components
export interface Sample {
  filename: string;
  name?: string;
  score?: number;
  starred?: boolean;
  isFavorite?: boolean; // Legacy compatibility
  x: number[];
  y: number[];
  rawContent: string;
}

export interface RangeWeight {
  min: number;
  max: number;
  weight: number;
  label: string;
  key: string;
}

export interface SavedGraphResponse {
  saved_paths: string[];
  previews?: string[]; // base64 optional
}

// Analysis types
export type ScoringMethod = 'hybrid' | 'rmse' | 'pearson' | 'area';
export type StatusFilter = 'all' | 'good' | 'warning' | 'critical';
export type Status = 'good' | 'warning' | 'critical';

// Utility function to get sample status - centralized
export const getSampleStatus = (score: number | undefined): Status => {
  if (score === undefined) return 'good';
  if (score >= 85) return 'good';
  if (score >= 70) return 'warning';
  return 'critical';
};

// Error handling types
export interface AnalysisError {
  code: 'INVALID_DATA' | 'CALCULATION_ERROR' | 'MISSING_BASELINE';
  message: string;
  details?: Record<string, unknown>;
}

export type AnalysisResult<T> = {
  success: true;
  data: T;
} | {
  success: false;
  error: AnalysisError;
};
