import { useState, useCallback, useEffect, useRef } from 'react';
import { FTIRApiService, ftirApiHelpers } from '../api/ftirApi';
import { 
  LoadingStates, 
  ProgressState, 
  AnalysisResponse, 
  DeviationResponse,
  ScoresResponse,
  AnalysisRequest,
  DeviationRequest,
  ScoresRequest,
  LoadingState,
  AnalysisConfiguration,
  AnalysisSession
} from '../../../types/api';

export const useFTIRAnalysis = () => {
  // Loading states for different operations
  const [loadingStates, setLoadingStates] = useState<LoadingStates>({
    fileUpload: 'idle',
    analysis: 'idle',
    deviation: 'idle',
    configSave: 'idle',
    configLoad: 'idle',
    sessionSave: 'idle',
    historyLoad: 'idle',
  });

  // Progress tracking
  const [progressState, setProgressState] = useState<ProgressState>({});

  // Error state
  const [error, setError] = useState<string | null>(null);

  // Results state
  const [analysisResults, setAnalysisResults] = useState<AnalysisResponse | null>(null);
  const [deviationResults, setDeviationResults] = useState<DeviationResponse | null>(null);
  const [scoresResults, setScoresResults] = useState<ScoresResponse | null>(null);
  const [configurations, setConfigurations] = useState<AnalysisConfiguration[]>([]);
  const [sessionHistory, setSessionHistory] = useState<AnalysisSession[]>([]);

  // Abort controller for cancelling requests
  const abortControllerRef = useRef<AbortController | null>(null);
  const scoresRequestIdRef = useRef(0);

  // Helper to set loading state for specific operation
  const setLoadingState = useCallback((operation: keyof LoadingStates, state: LoadingState) => {
    setLoadingStates(prev => ({ ...prev, [operation]: state }));
  }, []);

  // Helper to set progress
  const setProgress = useCallback((operation: 'fileUpload' | 'analysis', progress: any) => {
    setProgressState(prev => ({ ...prev, [operation]: progress }));
  }, []);

  // Clear error
  const clearError = useCallback(() => setError(null), []);

  // Clear all results
  const clearResults = useCallback(() => {
    setAnalysisResults(null);
    setDeviationResults(null);
    setScoresResults(null);
    setError(null);
  }, []);

  const clearScores = useCallback(() => {
    scoresRequestIdRef.current += 1;
    setScoresResults(null);
  }, []);

  // Cancel current operation
  const cancelOperation = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // Reset loading states
    setLoadingStates({
      fileUpload: 'idle',
      analysis: 'idle',
      deviation: 'idle',
      configSave: 'idle',
      configLoad: 'idle',
      sessionSave: 'idle',
      historyLoad: 'idle',
    });
    
    setProgressState({});
  }, []);

  // Analyze samples (full analysis with scores and deviation data)
  const analyzeSamples = useCallback(async (request: AnalysisRequest) => {
    try {
      setLoadingState('analysis', 'loading');
      setProgress('analysis', { stage: 'parsing', progress: 10 });
      clearError();

      // Validate files
      const baselineValidation = ftirApiHelpers.validateFile(request.baseline);
      if (!baselineValidation.valid) {
        throw new Error(`Baseline file error: ${baselineValidation.error}`);
      }

      for (const sample of request.samples) {
        const validation = ftirApiHelpers.validateFile(sample);
        if (!validation.valid) {
          throw new Error(`Sample file "${sample.name}" error: ${validation.error}`);
        }
      }

      setProgress('analysis', { stage: 'calculating', progress: 30 });

      abortControllerRef.current = new AbortController();
      const response = await FTIRApiService.analyzeSamples(request);
      
      setProgress('analysis', { stage: 'processing', progress: 80 });
      
      setAnalysisResults(response);
      setLoadingState('analysis', 'success');
      setProgress('analysis', { stage: 'complete', progress: 100 });
      
      return response;
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setLoadingState('analysis', 'idle');
        return null;
      }
      
      const errorMessage = err.response?.data?.error || err.message || 'Analysis failed';
      setError(errorMessage);
      setLoadingState('analysis', 'error');
      throw err;
    } finally {
      abortControllerRef.current = null;
    }
  }, [setLoadingState, setProgress, clearError]);

  // Calculate deviation data only
  const calculateDeviation = useCallback(async (request: DeviationRequest) => {
    try {
      setLoadingState('deviation', 'loading');
      clearError();

      const response = await FTIRApiService.calculateDeviation(request);
      setDeviationResults(response);
      setLoadingState('deviation', 'success');
      
      return response;
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Deviation calculation failed';
      setError(errorMessage);
      setLoadingState('deviation', 'error');
      throw err;
    }
  }, [setLoadingState, clearError]);

  // Calculate scores only (faster for batch processing)
  const calculateScores = useCallback(async (request: ScoresRequest) => {
    const requestId = ++scoresRequestIdRef.current;
    try {
      setLoadingState('analysis', 'loading');
      setScoresResults(null);
      setProgress('analysis', { stage: 'calculating', progress: 50 });
      clearError();

      const response = await FTIRApiService.calculateScores(request);
      if (requestId !== scoresRequestIdRef.current) return response;
      setScoresResults(response);
      setLoadingState('analysis', 'success');
      setProgress('analysis', { stage: 'complete', progress: 100 });
      
      return response;
    } catch (err: any) {
      if (requestId !== scoresRequestIdRef.current) throw err;
      const errorMessage = err.response?.data?.error || err.message || 'Score calculation failed';
      setError(errorMessage);
      setLoadingState('analysis', 'error');
      setScoresResults(null);
      throw err;
    }
  }, [setLoadingState, setProgress, clearError]);

  // Save configuration
  const saveConfiguration = useCallback(async (config: {
    name: string;
    zoneWeights: any[];
    scoringMethod: any;
  }) => {
    try {
      setLoadingState('configSave', 'loading');
      clearError();

      const response = await FTIRApiService.saveConfiguration(config);
      setLoadingState('configSave', 'success');
      
      // Refresh configurations list
      loadConfigurations();
      
      return response;
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Configuration save failed';
      setError(errorMessage);
      setLoadingState('configSave', 'error');
      throw err;
    }
  }, [setLoadingState, clearError]);

  // Load configurations
  const loadConfigurations = useCallback(async () => {
    try {
      setLoadingState('configLoad', 'loading');
      clearError();

      const response = await FTIRApiService.loadConfigurations();
      setConfigurations(response.configurations);
      setLoadingState('configLoad', 'success');
      
      return response;
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Configuration load failed';
      setError(errorMessage);
      setLoadingState('configLoad', 'error');
      throw err;
    }
  }, [setLoadingState, clearError]);

  // Save analysis session
  const saveSession = useCallback(async (sessionData: AnalysisSession) => {
    try {
      setLoadingState('sessionSave', 'loading');
      clearError();

      const response = await FTIRApiService.saveSession(sessionData);
      setLoadingState('sessionSave', 'success');
      
      return response;
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Session save failed';
      setError(errorMessage);
      setLoadingState('sessionSave', 'error');
      throw err;
    }
  }, [setLoadingState, clearError]);

  // Load analysis history
  const loadHistory = useCallback(async (page: number = 1, limit: number = 20) => {
    try {
      setLoadingState('historyLoad', 'loading');
      clearError();

      const response = await FTIRApiService.getHistory(page, limit);
      setSessionHistory(response.sessions);
      setLoadingState('historyLoad', 'success');
      
      return response;
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'History load failed';
      setError(errorMessage);
      setLoadingState('historyLoad', 'error');
      throw err;
    }
  }, [setLoadingState, clearError]);

  // Health check
  const checkHealth = useCallback(async () => {
    try {
      const response = await FTIRApiService.healthCheck();
      return response;
    } catch (err: any) {
      console.warn('Health check failed:', err);
      return { status: 'error', services: {} };
    }
  }, []);

  // Auto-load configurations on mount
  useEffect(() => {
    loadConfigurations().catch(console.warn);
  }, [loadConfigurations]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    // State
    loadingStates,
    progressState,
    error,
    analysisResults,
    deviationResults,
    scoresResults,
    configurations,
    sessionHistory,

    // Actions
    analyzeSamples,
    calculateDeviation,
    calculateScores,
    saveConfiguration,
    loadConfigurations,
    saveSession,
    loadHistory,
    checkHealth,
    
    // Utility
    clearError,
    clearResults,
    clearScores,
    cancelOperation,
  };
};
