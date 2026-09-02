// TypeScript type definitions for API integration

import type { RangeWeight, ScoringMethod } from './common';

export type { RangeWeight, ScoringMethod } from './common';

// ===== REQUEST TYPES =====

export interface AnalysisRequest {
  baseline: File;
  samples: File[];
  scoringMethod: ScoringMethod;
  zoneWeights?: RangeWeight[];
}

export interface DeviationRequest {
  baseline: File;
  sample: File;
  zoneWeights?: RangeWeight[];
}

export interface ScoresRequest {
  baseline: File;
  samples: File[];
  scoringMethod: ScoringMethod;
  zoneWeights?: RangeWeight[];
}

export interface ConfigSaveRequest {
  name: string;
  zoneWeights: RangeWeight[];
  scoringMethod: ScoringMethod;
}

// ===== RESPONSE TYPES =====

export interface SampleScore {
  filename: string;
  score: number;
  status: 'good' | 'warning' | 'critical';
}

export interface DeviationData {
  x: number[];
  deviation: number[];
  maxDeviation: number;
  avgDeviation: number;
}

export interface AnalysisResponse {
  success: boolean;
  scores: { [filename: string]: number };
  deviationData?: DeviationData;
  processingTime: number;
  metadata: {
    baseline_filename: string;
    sample_count: number;
    scoring_method: ScoringMethod;
    zone_weights_used: RangeWeight[];
    timestamp: string;
  };
}

export interface DeviationResponse {
  success: boolean;
  deviationData: DeviationData;
  sampleInfo: {
    filename: string;
    dataPoints: number;
    wavelengthRange: [number, number];
  };
  processingTime: number;
}

export interface ScoresResponse {
  success: boolean;
  scores: { [filename: string]: number };
  summary: {
    totalSamples: number;
    good: number;
    warning: number;
    critical: number;
  };
  processingTime: number;
}

export interface ConfigSaveResponse {
  success: boolean;
  configId: string;
  message: string;
}

export interface ConfigListResponse {
  success: boolean;
  configurations: AnalysisConfiguration[];
}

// ===== ERROR TYPES =====

export interface ApiError {
  success: false;
  error: string;
  errorCode?: string;
  details?: any;
  timestamp: string;
}

// ===== CONFIGURATION TYPES =====

export interface AnalysisConfiguration {
  id: string;
  name: string;
  zoneWeights: RangeWeight[];
  scoringMethod: ScoringMethod;
  createdAt: string;
  updatedAt: string;
}

// ===== SESSION TYPES =====

export interface AnalysisSession {
  id?: string;
  name?: string;
  baselineInfo: {
    filename: string;
    uploadedAt: string;
  };
  samples: Array<{
    filename: string;
    score?: number;
    uploadedAt: string;
  }>;
  configuration: {
    scoringMethod: ScoringMethod;
    zoneWeights: RangeWeight[];
  };
  results: {
    scores: { [filename: string]: number };
    summary: {
      good: number;
      warning: number;
      critical: number;
    };
  };
  createdAt: string;
}

export interface SessionSaveResponse {
  success: boolean;
  sessionId: string;
  message: string;
}

export interface SessionHistoryResponse {
  success: boolean;
  sessions: AnalysisSession[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ===== LOADING TYPES =====

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface LoadingStates {
  fileUpload: LoadingState;
  analysis: LoadingState;
  deviation: LoadingState;
  configSave: LoadingState;
  configLoad: LoadingState;
  sessionSave: LoadingState;
  historyLoad: LoadingState;
}

export interface ProgressState {
  fileUpload?: {
    current: number;
    total: number;
    filename?: string;
  };
  analysis?: {
    stage: 'parsing' | 'calculating' | 'processing' | 'complete';
    progress: number; // 0-100
    currentSample?: string;
  };
}
