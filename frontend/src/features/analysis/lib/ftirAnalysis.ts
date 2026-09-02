// Fixed FTIRAnalysisService with comprehensive error handling
import { type Series, diff } from './series';
import type { ParsedCSV, RangeWeight, ScoringMethod } from '../../../types';

export interface AnalysisResult {
  scores: { [filename: string]: number };
  deviationData: {
    x: number[];
    deviation: number[];
    maxDeviation: number;
    avgDeviation: number;
  } | null;
}

// Error classes for better error handling
export class AnalysisError extends Error {
  constructor(message: string, public code: string, public details?: any) {
    super(message);
    this.name = 'AnalysisError';
  }
}

export class FTIRAnalysisService {
  
  /**
   * Validate data arrays for analysis
   */
  private static validateData(baseline: ParsedCSV, sample: ParsedCSV): void {
    if (!baseline || !sample) {
      throw new AnalysisError('Missing baseline or sample data', 'MISSING_DATA');
    }

    if (!Array.isArray(baseline.x) || !Array.isArray(baseline.y)) {
      throw new AnalysisError('Baseline data must contain x and y arrays', 'INVALID_BASELINE');
    }

    if (!Array.isArray(sample.x) || !Array.isArray(sample.y)) {
      throw new AnalysisError('Sample data must contain x and y arrays', 'INVALID_SAMPLE');
    }

    if (baseline.x.length === 0 || baseline.y.length === 0) {
      throw new AnalysisError('Baseline arrays cannot be empty', 'EMPTY_BASELINE');
    }

    if (sample.x.length === 0 || sample.y.length === 0) {
      throw new AnalysisError('Sample arrays cannot be empty', 'EMPTY_SAMPLE');
    }

    if (baseline.x.length !== baseline.y.length) {
      throw new AnalysisError('Baseline x and y arrays must have same length', 'MISMATCHED_BASELINE_LENGTH');
    }

    if (sample.x.length !== sample.y.length) {
      throw new AnalysisError('Sample x and y arrays must have same length', 'MISMATCHED_SAMPLE_LENGTH');
    }

    // Check for NaN or infinite values
    const hasInvalidBaseline = baseline.x.some(v => !isFinite(v)) || baseline.y.some(v => !isFinite(v));
    const hasInvalidSample = sample.x.some(v => !isFinite(v)) || sample.y.some(v => !isFinite(v));

    if (hasInvalidBaseline) {
      throw new AnalysisError('Baseline contains invalid (NaN/Infinity) values', 'INVALID_BASELINE_VALUES');
    }

    if (hasInvalidSample) {
      throw new AnalysisError('Sample contains invalid (NaN/Infinity) values', 'INVALID_SAMPLE_VALUES');
    }
  }

  /**
   * Get weight for a given wavelength based on abnormality weights configuration
   */
  private static getWeightForWavelength(wavelength: number, abnormalityWeights: RangeWeight[]): number {
    if (!isFinite(wavelength)) {
      return 0; // Invalid wavelength gets zero weight
    }

    if (!abnormalityWeights || abnormalityWeights.length === 0) {
      return 1.0; // Default weight when no weights are configured
    }

    for (const range of abnormalityWeights) {
      if (!isFinite(range.weight) || range.weight < 0) {
        continue; // Skip invalid weight ranges
      }
      
      if (wavelength >= range.min && wavelength <= range.max) {
        return Math.max(0, range.weight / 100); // Ensure non-negative, convert percentage to decimal
      }
    }
    return 1.0; // Default weight if wavelength doesn't fall in any range
  }

  /**
   * Safe mathematical operations with NaN/Infinity protection
   */
  private static safeDivision(numerator: number, denominator: number): number {
    if (!isFinite(numerator) || !isFinite(denominator) || denominator === 0) {
      return 0;
    }
    const result = numerator / denominator;
    return isFinite(result) ? result : 0;
  }

  private static safeSquareRoot(value: number): number {
    if (!isFinite(value) || value < 0) {
      return 0;
    }
    const result = Math.sqrt(value);
    return isFinite(result) ? result : 0;
  }

  /**
   * Calculate deviation data for selected sample vs baseline with error handling
   */
  public static calculateDeviationData(
    baseline: ParsedCSV,
    samples: ParsedCSV[],
    selectedSampleName?: string,
    abnormalityWeights: RangeWeight[] = [],
    scoringMethod: ScoringMethod = 'hybrid'
  ): { x: number[]; deviation: number[]; maxDeviation: number; avgDeviation: number } | null {
    
    try {
      if (!baseline || !samples || samples.length === 0) return null;

      this.validateData(baseline, samples[0]);

      // Convert baseline to Series format
      const baselineSeries: Series = {
        name: baseline.filename,
        points: baseline.x.map((x, i) => ({ 
          x: isFinite(x) ? x : 0, 
          y: isFinite(baseline.y[i]) ? baseline.y[i] : 0 
        }))
      };

      // Calculate individual differences for each sample vs baseline
      const sampleDifferences = samples
        .filter(s => s && s.x && s.y && s.x.length > 0 && s.y.length > 0)
        .map(s => {
          try {
            this.validateData(baseline, s);
            const sampleSeries: Series = {
              name: s.filename,
              points: s.x.map((x, i) => ({ 
                x: isFinite(x) ? x : 0, 
                y: isFinite(s.y[i]) ? s.y[i] : 0 
              }))
            };
            return diff(baselineSeries, sampleSeries);
          } catch (error) {
            console.warn(`Skipping invalid sample ${s.filename}:`, error);
            return null;
          }
        })
        .filter(Boolean);

      if (sampleDifferences.length === 0) return null;

      const firstDiff = sampleDifferences[0];
      const x = firstDiff.x;

      // Calculate average difference across all samples at each x-point
      const avgDelta: number[] = [];
      for (let i = 0; i < x.length; i++) {
        const xValue = x[i];
        if (!isFinite(xValue)) {
          avgDelta.push(0);
          continue;
        }

        let sum = 0;
        let count = 0;

        for (const sampleDiff of sampleDifferences) {
          const idx = sampleDiff.x.findIndex(val => Math.abs(val - xValue) < 0.001); // Use tolerance for floating point comparison
          if (idx !== -1 && isFinite(sampleDiff.delta[idx])) {
            sum += sampleDiff.delta[idx];
            count++;
          }
        }

        avgDelta.push(count > 0 ? sum / count : 0);
      }

      // Apply weights and calculate final deviation
      const weightedDeviation: number[] = [];
      for (let i = 0; i < x.length; i++) {
        const weight = this.getWeightForWavelength(x[i], abnormalityWeights);
        const deviation = Math.abs(avgDelta[i]) * weight;
        weightedDeviation.push(isFinite(deviation) ? deviation : 0);
      }

      // Calculate statistics safely
      const validDeviations = weightedDeviation.filter(isFinite);
      const maxDeviation = validDeviations.length > 0 ? Math.max(...validDeviations) : 0;
      const avgDeviation = validDeviations.length > 0 ? 
        validDeviations.reduce((sum, val) => sum + val, 0) / validDeviations.length : 0;

      return {
        x: x.filter(isFinite),
        deviation: weightedDeviation,
        maxDeviation: isFinite(maxDeviation) ? maxDeviation : 0,
        avgDeviation: isFinite(avgDeviation) ? avgDeviation : 0
      };

    } catch (error) {
      console.error('Error calculating deviation data:', error);
      return null;
    }
  }

  /**
   * Calculate score for a sample with comprehensive error handling
   */
  private static calculateSampleScore(
    baseline: ParsedCSV,
    sample: ParsedCSV,
    abnormalityWeights: RangeWeight[],
    scoringMethod: ScoringMethod
  ): number {
    try {
      this.validateData(baseline, sample);

      // Find overlapping wavelength range
      const baselineXSet = new Set(baseline.x.filter(isFinite));
      const sampleXSet = new Set(sample.x.filter(isFinite));
      
      // Get intersection of wavelengths with tolerance
      const commonX: number[] = [];
      for (const bx of baseline.x) {
        if (!isFinite(bx)) continue;
        const closestSample = sample.x.find(sx => isFinite(sx) && Math.abs(sx - bx) < 0.001);
        if (closestSample !== undefined) {
          commonX.push(bx);
        }
      }

      if (commonX.length < 2) {
        console.warn(`Insufficient overlapping data points: ${commonX.length}`);
        return 50; // Return neutral score for insufficient data
      }

      let score = 0;

      if (scoringMethod === 'rmse') {
        // Method 1: Weighted RMSE
        let sumWeightedSquaredErrors = 0;
        let sumWeights = 0;

        for (const wavelength of commonX) {
          const weight = this.getWeightForWavelength(wavelength, abnormalityWeights);
          const baselineIdx = baseline.x.findIndex(x => Math.abs(x - wavelength) < 0.001);
          const sampleIdx = sample.x.findIndex(x => Math.abs(x - wavelength) < 0.001);

          if (baselineIdx !== -1 && sampleIdx !== -1 && 
              baselineIdx < baseline.y.length && sampleIdx < sample.y.length) {
            
            const baselineY = baseline.y[baselineIdx];
            const sampleY = sample.y[sampleIdx];
            
            if (isFinite(baselineY) && isFinite(sampleY)) {
              const error = baselineY - sampleY;
              sumWeightedSquaredErrors += weight * error * error;
              sumWeights += weight;
            }
          }
        }

        if (sumWeights > 0) {
          const rmse = this.safeSquareRoot(sumWeightedSquaredErrors / sumWeights);
          // Convert RMSE to score (lower RMSE = higher score)
          // Assuming RMSE of 0.1 = 90 score, RMSE of 1.0 = 0 score
          score = Math.max(0, Math.min(100, 100 - (rmse * 100)));
        }

      } else if (scoringMethod === 'pearson') {
        // Method 2: Weighted Pearson Correlation
        let sumWeightedX = 0;
        let sumWeightedY = 0;
        let sumWeightedXY = 0;
        let sumWeightedX2 = 0;
        let sumWeightedY2 = 0;
        let sumWeights = 0;

        for (const wavelength of commonX) {
          const weight = this.getWeightForWavelength(wavelength, abnormalityWeights);
          const baselineIdx = baseline.x.findIndex(x => Math.abs(x - wavelength) < 0.001);
          const sampleIdx = sample.x.findIndex(x => Math.abs(x - wavelength) < 0.001);

          if (baselineIdx !== -1 && sampleIdx !== -1 && 
              baselineIdx < baseline.y.length && sampleIdx < sample.y.length) {
            
            const baselineY = baseline.y[baselineIdx];
            const sampleY = sample.y[sampleIdx];
            
            if (isFinite(baselineY) && isFinite(sampleY)) {
              sumWeightedX += weight * baselineY;
              sumWeightedY += weight * sampleY;
              sumWeightedXY += weight * baselineY * sampleY;
              sumWeightedX2 += weight * baselineY * baselineY;
              sumWeightedY2 += weight * sampleY * sampleY;
              sumWeights += weight;
            }
          }
        }

        let correlation = 0;
        if (sumWeights > 0) {
          const meanX = sumWeightedX / sumWeights;
          const meanY = sumWeightedY / sumWeights;
          const meanXY = sumWeightedXY / sumWeights;
          const meanX2 = sumWeightedX2 / sumWeights;
          const meanY2 = sumWeightedY2 / sumWeights;
          
          const covariance = meanXY - (meanX * meanY);
          const stdX = this.safeSquareRoot(Math.abs(meanX2 - (meanX * meanX)));
          const stdY = this.safeSquareRoot(Math.abs(meanY2 - (meanY * meanY)));
          
          if (stdX > 0 && stdY > 0) {
            correlation = this.safeDivision(covariance, stdX * stdY);
            correlation = Math.max(-1, Math.min(1, correlation));
          }
        }

        // Map correlation to score (0-100 scale)
        // Correlation of 1.0 = 100 score, correlation of 0 = 50 score, correlation of -1 = 0 score
        score = Math.max(0, Math.min(100, ((correlation + 1) / 2) * 100));

      } else if (scoringMethod === 'area') {
        // Method 3: Area Difference / Integral Difference
        let totalWeightedAreaDiff = 0;
        let totalWeightedArea = 0;

        for (let i = 0; i < commonX.length - 1; i++) {
          const wavelength1 = commonX[i];
          const wavelength2 = commonX[i + 1];
          const weight = (this.getWeightForWavelength(wavelength1, abnormalityWeights) + 
                         this.getWeightForWavelength(wavelength2, abnormalityWeights)) / 2;
          
          const baseline1Idx = baseline.x.findIndex(x => Math.abs(x - wavelength1) < 0.001);
          const baseline2Idx = baseline.x.findIndex(x => Math.abs(x - wavelength2) < 0.001);
          const sample1Idx = sample.x.findIndex(x => Math.abs(x - wavelength1) < 0.001);
          const sample2Idx = sample.x.findIndex(x => Math.abs(x - wavelength2) < 0.001);

          if (baseline1Idx !== -1 && baseline2Idx !== -1 && sample1Idx !== -1 && sample2Idx !== -1 &&
              baseline1Idx < baseline.y.length && baseline2Idx < baseline.y.length &&
              sample1Idx < sample.y.length && sample2Idx < sample.y.length) {
            
            const baselineY1 = baseline.y[baseline1Idx];
            const baselineY2 = baseline.y[baseline2Idx];
            const sampleY1 = sample.y[sample1Idx];
            const sampleY2 = sample.y[sample2Idx];
            
            if (isFinite(baselineY1) && isFinite(baselineY2) && isFinite(sampleY1) && isFinite(sampleY2)) {
              const dx = Math.abs(wavelength2 - wavelength1);
              const baselineArea = dx * (baselineY1 + baselineY2) / 2;
              const sampleArea = dx * (sampleY1 + sampleY2) / 2;
              const areaDiff = Math.abs(baselineArea - sampleArea);
              
              totalWeightedAreaDiff += weight * areaDiff;
              totalWeightedArea += weight * Math.abs(baselineArea);
            }
          }
        }

        if (totalWeightedArea > 0) {
          const normalizedAreaDiff = this.safeDivision(totalWeightedAreaDiff, totalWeightedArea);
          score = Math.max(0, Math.min(100, 100 - (normalizedAreaDiff * 100)));
        }

      } else { // hybrid method (default)
        // Hybrid: Combine RMSE and Pearson correlation
        const rmseScore = this.calculateSampleScore(baseline, sample, abnormalityWeights, 'rmse');
        const pearsonScore = this.calculateSampleScore(baseline, sample, abnormalityWeights, 'pearson');
        
        if (isFinite(rmseScore) && isFinite(pearsonScore)) {
          score = (rmseScore * 0.6) + (pearsonScore * 0.4); // Weight RMSE more heavily
        } else if (isFinite(rmseScore)) {
          score = rmseScore;
        } else if (isFinite(pearsonScore)) {
          score = pearsonScore;
        } else {
          score = 50; // Neutral score if both fail
        }
      }

      // Ensure score is within valid range
      return Math.max(0, Math.min(100, score));

    } catch (error) {
      console.error(`Error calculating score for ${sample.filename}:`, error);
      return 50; // Return neutral score on error
    }
  }

  /**
   * Perform complete analysis with error handling
   */
  public static performAnalysis(
    baseline: ParsedCSV,
    samples: ParsedCSV[],
    selectedSampleName?: string,
    abnormalityWeights: RangeWeight[] = [],
    scoringMethod: ScoringMethod = 'hybrid'
  ): AnalysisResult {
    
    try {
      if (!baseline || !samples || samples.length === 0) {
        return {
          scores: {},
          deviationData: null
        };
      }

      // Validate inputs
      this.validateData(baseline, samples[0]);

      // Calculate scores for all samples
      const scores: { [filename: string]: number } = {};
      
      for (const sample of samples) {
        if (sample && sample.filename) {
          try {
            scores[sample.filename] = this.calculateSampleScore(
              baseline,
              sample,
              abnormalityWeights,
              scoringMethod
            );
          } catch (error) {
            console.warn(`Failed to calculate score for ${sample.filename}:`, error);
            scores[sample.filename] = 50; // Neutral score on error
          }
        }
      }

      // Calculate deviation data
      const deviationData = this.calculateDeviationData(
        baseline,
        samples,
        selectedSampleName,
        abnormalityWeights,
        scoringMethod
      );

      return {
        scores,
        deviationData
      };

    } catch (error) {
      console.error('Analysis failed:', error);
      
      // Return safe fallback data
      const fallbackScores: { [filename: string]: number } = {};
      samples.forEach(sample => {
        if (sample && sample.filename) {
          fallbackScores[sample.filename] = 50;
        }
      });

      return {
        scores: fallbackScores,
        deviationData: null
      };
    }
  }
}
