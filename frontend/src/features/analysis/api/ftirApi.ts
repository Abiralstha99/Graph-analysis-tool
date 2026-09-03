import api from '../../../services/api';
import { 
  AnalysisRequest, 
  AnalysisResponse, 
  DeviationRequest, 
  DeviationResponse, 
  ScoresRequest, 
  ScoresResponse,
  ConfigSaveRequest,
  ConfigSaveResponse,
  ConfigListResponse,
  AnalysisSession,
  SessionSaveResponse,
  SessionHistoryResponse
} from '../../../types';
import type { RangeWeight, ScoringMethod } from '../../../types';

export class FTIRApiService {
  
  /**
   * Analyze FTIR samples using the backend's single-sample insights endpoint.
   * The public client method remains batch-oriented and aggregates the results.
   */
  static async analyzeSamples(request: AnalysisRequest): Promise<AnalysisResponse> {
    if (request.samples.length === 0) {
      throw new Error('At least one sample is required for analysis');
    }

    const startedAt = performance.now();
    const results = await Promise.all(request.samples.map(async (sample) => {
      const formData = new FormData();
      formData.append('baseline', request.baseline);
      formData.append('sample', sample);
      formData.append('sample_name', sample.name);

      const response = await api.post('/analysis/generate_insights', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      return response.data;
    }));

    return {
      success: true,
      results,
      metadata: {
        baseline_filename: request.baseline.name,
        sample_count: results.length,
        timestamp: new Date().toISOString(),
      },
      processingTime: performance.now() - startedAt,
    };
  }

  /**
   * Calculate deviation data for single sample comparison
   */
  static async calculateDeviation(request: DeviationRequest): Promise<DeviationResponse> {
    const formData = new FormData();
    
    formData.append('baseline', request.baseline);
    formData.append('sample', request.sample);
    
    if (request.zoneWeights) {
      formData.append('zone_weights', JSON.stringify(request.zoneWeights));
    }

    const response = await api.post<DeviationResponse>('/analysis/ftir/deviation', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    return response.data;
  }

  /**
   * Calculate scores only for batch processing (faster when deviation data not needed)
   */
  static async calculateScores(request: ScoresRequest): Promise<ScoresResponse> {
    const formData = new FormData();
    
    formData.append('baseline', request.baseline);
    request.samples.forEach(sample => formData.append('samples', sample));
    formData.append('scoring_method', request.scoringMethod);
    
    if (request.zoneWeights) {
      formData.append('zone_weights', JSON.stringify(request.zoneWeights));
    }

    const response = await api.post<ScoresResponse>('/analysis/ftir/scores', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    return response.data;
  }

  /**
   * Save analysis configuration for reuse
   */
  static async saveConfiguration(config: ConfigSaveRequest): Promise<ConfigSaveResponse> {
    const formData = new FormData();
    formData.append('config_name', config.name);
    formData.append('zone_weights', JSON.stringify(config.zoneWeights));
    formData.append('scoring_method', config.scoringMethod);

    const response = await api.post<ConfigSaveResponse>('/analysis/ftir/config/save', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    return response.data;
  }

  /**
   * Load saved user configurations
   */
  static async loadConfigurations(): Promise<ConfigListResponse> {
    const response = await api.get<ConfigListResponse>('/analysis/ftir/config/list');
    return response.data;
  }

  /**
   * Delete a saved configuration
   */
  static async deleteConfiguration(configId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(`/analysis/ftir/config/${configId}`);
    return response.data;
  }

  /**
   * Save complete analysis session for history
   */
  static async saveSession(sessionData: AnalysisSession): Promise<SessionSaveResponse> {
    const response = await api.post<SessionSaveResponse>('/analysis/ftir/sessions/save', sessionData, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  /**
   * Get paginated analysis history
   */
  static async getHistory(page: number = 1, limit: number = 20): Promise<SessionHistoryResponse> {
    const response = await api.get<SessionHistoryResponse>(
      `/analysis/ftir/sessions/history?page=${page}&limit=${limit}`
    );
    return response.data;
  }

  /**
   * Get specific analysis session by ID
   */
  static async getSession(sessionId: string): Promise<{ success: boolean; session: AnalysisSession }> {
    const response = await api.get(`/analysis/ftir/sessions/${sessionId}`);
    return response.data;
  }

  /**
   * Delete analysis session
   */
  static async deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(`/analysis/ftir/sessions/${sessionId}`);
    return response.data;
  }

  /**
   * Upload files with progress tracking
   */
  static async uploadFiles(
    files: File[],
    onProgress?: (progress: { current: number; total: number; filename?: string }) => void
  ): Promise<{ success: boolean; fileIds: string[] }> {
    const formData = new FormData();
    
    files.forEach((file, index) => {
      formData.append(`file_${index}`, file);
    });

    const response = await api.post('/analysis/ftir/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress({
            current: progressEvent.loaded,
            total: progressEvent.total,
            filename: files[0]?.name // Current file being uploaded
          });
        }
      }
    });

    return response.data;
  }

  /**
   * Health check for FTIR analysis service
   */
  static async healthCheck(): Promise<{ status: string; services: Record<string, string> }> {
    const response = await api.get('/analysis/ftir/health');
    return response.data;
  }

  /**
   * Get analysis service capabilities and limits
   */
  static async getCapabilities(): Promise<{
    maxFileSize: number;
    maxSamples: number;
    supportedFormats: string[];
    scoringMethods: ScoringMethod[];
    defaultWeights: RangeWeight[];
  }> {
    const response = await api.get('/analysis/ftir/capabilities');
    return response.data;
  }

  /**
   * Export graphs as a zip file
   */
  static async exportGraphs(request: {
    baseline: File;
    samples: File[];
    format: 'png' | 'jpeg';
    saveDir?: string;
    zipFilename?: string;
  }): Promise<Blob> {
    const formData = new FormData();
    
    formData.append('baseline', request.baseline);
    request.samples.forEach(sample => formData.append('samples', sample));
    formData.append('format', request.format);
    
    if (request.saveDir) {
      formData.append('save_dir', request.saveDir);
    }
    
    if (request.zipFilename) {
      formData.append('zip_filename', request.zipFilename);
    }

    const response = await api.post('/generate_graphs', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob', // Important for binary data
    });

    return response.data;
  }
}

// Export helper functions for common operations
export const ftirApiHelpers = {
  /**
   * Get status classification for a score
   */
  getScoreStatus: (score: number): 'good' | 'warning' | 'critical' => {
    if (score >= 90) return 'good';
    if (score >= 70) return 'warning';
    return 'critical';
  },

  /**
   * Format processing time for display
   */
  formatProcessingTime: (timeMs: number): string => {
    if (timeMs < 1000) return `${Math.round(timeMs)}ms`;
    if (timeMs < 60000) return `${(timeMs / 1000).toFixed(1)}s`;
    return `${Math.round(timeMs / 60000)}min`;
  },

  /**
   * Validate file for FTIR analysis
   */
  validateFile: (file: File): { valid: boolean; error?: string } => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['.csv', '.txt', '.dat'];
    
    if (file.size > maxSize) {
      return { valid: false, error: 'File size exceeds 10MB limit' };
    }
    
    const extension = file.name.toLowerCase().split('.').pop();
    if (!allowedTypes.some(type => type.includes(extension || ''))) {
      return { valid: false, error: 'File type not supported. Use CSV, TXT, or DAT files.' };
    }
    
    return { valid: true };
  },

  /**
   * Create default zone weights for FTIR analysis
   */
  getDefaultZoneWeights: (): RangeWeight[] => [
    { min: 4000, max: 2750, weight: 100, label: 'O-H, N-H stretch', key: 'oh-nh' },
    { min: 2750, max: 2000, weight: 100, label: 'C-H stretch', key: 'ch' },
    { min: 2000, max: 1750, weight: 100, label: 'C=C, C=N stretch', key: 'cc-cn' },
    { min: 1750, max: 550, weight: 100, label: 'Fingerprint region', key: 'fingerprint' }
  ]
};
