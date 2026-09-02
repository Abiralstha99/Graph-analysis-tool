import React, { useRef, useMemo } from 'react';
import { Box, VStack, Text, HStack, Button, Icon, useColorModeValue, useColorMode } from '@chakra-ui/react';
import { ViewIcon, ViewOffIcon, RepeatIcon } from '@chakra-ui/icons';
import type { ParsedCSV, RangeWeight } from '../../../types';
import DeviationHeatBar from '../../../components/shared/DeviationHeatBar';
import { Line } from 'react-chartjs-2';
import { type Series, diff } from '../../analysis';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  zoomPlugin
);

interface Props {
  baseline?: ParsedCSV;
  samples: ParsedCSV[];
  selectedSampleName?: string;
  onSelectSample: (name: string) => void;
  baselineFile?: File;
  sampleFiles?: FileList;
  abnormalityWeights?: RangeWeight[];
  onScoreUpdate?: (scores: { [filename: string]: number }) => void;
  scoringMethod?: 'area' | 'rmse' | 'hybrid' | 'pearson';
}

const GraphPreview: React.FC<Props> = ({ 
  baseline, 
  samples, 
  selectedSampleName, 
  onSelectSample, 
  baselineFile, 
  sampleFiles,
  abnormalityWeights = [],
  onScoreUpdate,
  scoringMethod = 'hybrid'
}) => {
  const chartRef = useRef<any>(null);
  const differenceChartRef = useRef<any>(null);
  const sample = samples.find((s: ParsedCSV) => s.filename === selectedSampleName) || samples[0];
  const hasData = baseline && sample;
  
  // Color mode support
  const { colorMode } = useColorMode();
  
  // Track whether to use custom mixed intervals or uniform 250 intervals
  const useCustomIntervals = useRef(true);
  // Force re-render trigger
  const [resetKey, setResetKey] = React.useState(0);
  const [differenceResetKey, setDifferenceResetKey] = React.useState(0);
  // Track grid visibility (synchronized across both graphs)
  const [showGrid, setShowGrid] = React.useState(true);

  // Function to get weight for a given wavelength
  const getWeightForWavelength = (wavelength: number): number => {
    if (!abnormalityWeights || abnormalityWeights.length === 0) {
      return 1.0; // Default weight when no weights are configured
    }

    for (const range of abnormalityWeights) {
      if (wavelength >= range.min && wavelength <= range.max) {
        return range.weight / 100; // Convert percentage to decimal
      }
    }
    return 1.0; // Default weight if wavelength doesn't fall in any range
  };

  // Step 2: Calculate differences and average across all samples
  const differenceData = useMemo(() => {
    if (!baseline || samples.length === 0) return null;

    // Convert baseline to Series format
    const baselineSeries: Series = { x: baseline.x, y: baseline.y };

    // Calculate individual differences for each sample vs baseline
    const sampleDifferences = samples.map(s => {
      const sampleSeries: Series = { x: s.x, y: s.y };
      return diff(baselineSeries, sampleSeries);
    });

    // Calculate average difference across all samples at each x-point
    // First, find common x-values across all samples
    if (sampleDifferences.length === 0) return null;

    const firstDiff = sampleDifferences[0];
    const x = firstDiff.x;
    const avgDelta: number[] = [];

    // For each x-point, average the deltas across all samples
    for (let i = 0; i < x.length; i++) {
      const xValue = x[i];
      let sum = 0;
      let count = 0;

      // Sum deltas from all samples at this x-point
      for (const sampleDiff of sampleDifferences) {
        const idx = sampleDiff.x.indexOf(xValue);
        if (idx !== -1) {
          sum += sampleDiff.y[idx];
          count++;
        }
      }

      avgDelta.push(count > 0 ? sum / count : 0);
    }

    // Calculate deviation from average for selected sample
    // Find the index of the selected sample
    const selectedSampleIndex = selectedSampleName 
      ? samples.findIndex(s => s.filename === selectedSampleName)
      : 0;
    const selectedSampleDiff = sampleDifferences[selectedSampleIndex >= 0 ? selectedSampleIndex : 0];
    const selectedSample = samples[selectedSampleIndex >= 0 ? selectedSampleIndex : 0];

    const deviation: number[] = [];

    for (let i = 0; i < x.length; i++) {
      const xValue = x[i];
      const idx = selectedSampleDiff.x.indexOf(xValue);
      if (idx !== -1) {
        let baseDeviation = 0;
        
        // Calculate deviation based on scoring method
        if (scoringMethod === 'rmse') {
          // For RMSE: use squared error (will be sqrt'd in visualization)
          baseDeviation = selectedSampleDiff.y[idx] * selectedSampleDiff.y[idx];
        } else if (scoringMethod === 'hybrid') {
          // For Hybrid: show absolute difference from baseline (deviation magnitude)
          baseDeviation = Math.abs(selectedSampleDiff.y[idx]);
        } else if (scoringMethod === 'pearson') {
          // For Pure Pearson: show absolute difference from baseline (deviation magnitude)
          baseDeviation = Math.abs(selectedSampleDiff.y[idx]);
        } else if (scoringMethod === 'area') {
          // For Area: show absolute difference from baseline (same as actual score calculation)
          baseDeviation = Math.abs(selectedSampleDiff.y[idx]);
        }
        
        // Apply abnormality weight for this wavelength
        const weight = getWeightForWavelength(xValue);
        const weightedDeviation = baseDeviation * weight;
        
        deviation.push(weightedDeviation);
      } else {
        deviation.push(0);
      }
    }

    return {
      x,
      avgDelta,
      selectedDelta: selectedSampleDiff.y,
      deviation,
      allSampleDifferences: sampleDifferences
    };
  }, [baseline, samples, selectedSampleName, abnormalityWeights, scoringMethod]);

  // Calculate anomaly scores for all samples (0-100, higher is better)
  const sampleScores = useMemo(() => {
    if (!baseline || samples.length === 0 || !differenceData) return {};

    const scores: { [filename: string]: number } = {};

    // Convert baseline to Series format
    const baselineSeries: Series = { x: baseline.x, y: baseline.y };

    // Calculate score for each sample based on the selected scoring method
    samples.forEach(sample => {
      const sampleSeries: Series = { x: sample.x, y: sample.y };

      const sampleDiff = diff(baselineSeries, sampleSeries);
      const { x: diffX, y: delta } = sampleDiff;

      let score = 0;

      if (scoringMethod === 'rmse') {
        // Method 1: RMSE Deviation Weighted by Interval
        let sumWeightedSquaredError = 0;
        let sumWeights = 0;

        for (let i = 0; i < diffX.length; i++) {
          const wavelength = diffX[i];
          const deviation = delta[i]; // Keep signed value for RMSE
          const weight = getWeightForWavelength(wavelength);
          
          sumWeightedSquaredError += weight * (deviation * deviation);
          sumWeights += weight;
        }

        const weightedRMSE = sumWeights > 0 ? Math.sqrt(sumWeightedSquaredError / sumWeights) : 0;
        
        // Convert RMSE to score (0-100, lower RMSE = higher score)
        // Adjusted thresholds: 0-0.10 (excellent), 0.10-0.25 (good), 0.25-0.5 (fair), >0.5 (poor)
        if (weightedRMSE <= 0.10) {
          score = 90 + (10 * (1 - weightedRMSE / 0.10)); // 90-100 for excellent
        } else if (weightedRMSE <= 0.25) {
          score = 70 + (20 * (1 - (weightedRMSE - 0.10) / 0.15)); // 70-90 for good
        } else if (weightedRMSE <= 0.5) {
          score = 40 + (30 * (1 - (weightedRMSE - 0.25) / 0.25)); // 40-70 for fair
        } else {
          score = Math.max(0, 40 * Math.exp(-(weightedRMSE - 0.5) / 0.3)); // 0-40 for poor
        }

      } else if (scoringMethod === 'hybrid') {
        // Method 2: Hybrid Score (Weighted RMSE + Pearson Penalty)
        // SCIENTIFICALLY CORRECT APPROACH FOR FTIR GREASE ANALYSIS
        
        // Step 1: Calculate Weighted RMSE (primary metric for chemical changes)
        let sumWeightedSquaredError = 0;
        let sumWeights = 0;

        for (let i = 0; i < diffX.length; i++) {
          const wavelength = diffX[i];
          const deviation = delta[i];
          const weight = getWeightForWavelength(wavelength);
          
          sumWeightedSquaredError += weight * (deviation * deviation);
          sumWeights += weight;
        }

        const weightedRMSE = sumWeights > 0 ? Math.sqrt(sumWeightedSquaredError / sumWeights) : 0;
        
        // Step 2: Calculate Pearson correlation (shape mismatch penalty only)
        let sumWeightedX = 0;
        let sumWeightedY = 0;
        let sumWeightedXY = 0;
        let sumWeightedX2 = 0;
        let sumWeightedY2 = 0;

        for (let i = 0; i < diffX.length; i++) {
          const wavelength = diffX[i];
          const weight = getWeightForWavelength(wavelength);
          
          const baselineIdx = baseline.x.indexOf(wavelength);
          const sampleIdx = sample.x.indexOf(wavelength);
          
          if (baselineIdx !== -1 && sampleIdx !== -1) {
            const baselineY = baseline.y[baselineIdx];
            const sampleY = sample.y[sampleIdx];
            
            sumWeightedX += weight * baselineY;
            sumWeightedY += weight * sampleY;
            sumWeightedXY += weight * baselineY * sampleY;
            sumWeightedX2 += weight * baselineY * baselineY;
            sumWeightedY2 += weight * sampleY * sampleY;
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
          const stdX = Math.sqrt(Math.abs(meanX2 - (meanX * meanX)));
          const stdY = Math.sqrt(Math.abs(meanY2 - (meanY * meanY)));
          
          if (stdX > 0 && stdY > 0) {
            correlation = covariance / (stdX * stdY);
            correlation = Math.max(-1, Math.min(1, correlation));
          }
        }

        // Step 3: Calculate base score from RMSE (85% weight)
        let baseScore = 0;
        if (weightedRMSE <= 0.10) {
          baseScore = 90 + (10 * (1 - weightedRMSE / 0.10));
        } else if (weightedRMSE <= 0.25) {
          baseScore = 70 + (20 * (1 - (weightedRMSE - 0.10) / 0.15));
        } else if (weightedRMSE <= 0.5) {
          baseScore = 40 + (30 * (1 - (weightedRMSE - 0.25) / 0.25));
        } else {
          baseScore = Math.max(0, 40 * Math.exp(-(weightedRMSE - 0.5) / 0.3));
        }

        // Step 4: Calculate Pearson penalty (15% weight, only penalizes shape mismatch)
        // Correlation < 0.90 indicates structural/shape problems beyond just intensity
        let pearsonPenalty = 0;
        if (correlation < 0.90) {
          // Maximum 15 point penalty for severe shape mismatch
          pearsonPenalty = 15 * (0.90 - correlation) / 0.90;
        } else if (correlation < 0.95) {
          // Small penalty (0-7.5 points) for minor shape issues
          pearsonPenalty = 7.5 * (0.95 - correlation) / 0.05;
        }
        // If correlation >= 0.95, no penalty (shape is good)

        // Step 5: Combined score = RMSE-based score - Pearson penalty
        score = Math.max(0, Math.min(100, baseScore - pearsonPenalty));

      } else if (scoringMethod === 'pearson') {
        // Method 3: Pure Pearson Correlation (for comparison/research purposes)
        // WARNING: This method alone is NOT scientifically sound for FTIR grease oxidation analysis
        // It only measures shape similarity, not chemical changes or oxidation severity
        
        let sumWeightedX = 0;
        let sumWeightedY = 0;
        let sumWeightedXY = 0;
        let sumWeightedX2 = 0;
        let sumWeightedY2 = 0;
        let sumWeights = 0;

        for (let i = 0; i < diffX.length; i++) {
          const wavelength = diffX[i];
          const weight = getWeightForWavelength(wavelength);
          
          const baselineIdx = baseline.x.indexOf(wavelength);
          const sampleIdx = sample.x.indexOf(wavelength);
          
          if (baselineIdx !== -1 && sampleIdx !== -1) {
            const baselineY = baseline.y[baselineIdx];
            const sampleY = sample.y[sampleIdx];
            
            sumWeightedX += weight * baselineY;
            sumWeightedY += weight * sampleY;
            sumWeightedXY += weight * baselineY * sampleY;
            sumWeightedX2 += weight * baselineY * baselineY;
            sumWeightedY2 += weight * sampleY * sampleY;
            sumWeights += weight;
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
          const stdX = Math.sqrt(Math.abs(meanX2 - (meanX * meanX)));
          const stdY = Math.sqrt(Math.abs(meanY2 - (meanY * meanY)));
          
          if (stdX > 0 && stdY > 0) {
            correlation = covariance / (stdX * stdY);
            correlation = Math.max(-1, Math.min(1, correlation));
          }
        }

        // Map correlation to score (0-100 scale)
        // r = 1.0 → 100, r = 0.95 → 95, r = 0.9 → 90, etc.
        // Note: This assumes higher correlation = better, which is problematic for detecting chemical changes
        score = Math.max(0, Math.min(100, correlation * 100));

      } else if (scoringMethod === 'area') {
        // Method 3: Area Difference / Integral Difference (default)
        // Calculate total weighted area difference using trapezoidal rule
        let totalWeightedAreaDiff = 0;

        for (let i = 0; i < diffX.length - 1; i++) {
          const wavelength1 = diffX[i];
          const wavelength2 = diffX[i + 1];
          const weight = (getWeightForWavelength(wavelength1) + getWeightForWavelength(wavelength2)) / 2;
          
          // Trapezoidal rule for area under the difference curve
          const dx = Math.abs(wavelength2 - wavelength1);
          const avgAbsDelta = (Math.abs(delta[i]) + Math.abs(delta[i + 1])) / 2;
          const areaDiff = dx * avgAbsDelta;
          
          totalWeightedAreaDiff += weight * areaDiff;
        }

        // The totalWeightedAreaDiff is the actual integrated difference
        // Typical values range from 0-50 (excellent), 50-200 (good), 200-500 (fair), >500 (poor)
        const areaDiff = totalWeightedAreaDiff;
        
        // Convert to score (0-100, lower area diff = higher score)
        if (areaDiff <= 50) {
          score = 90 + (10 * (1 - areaDiff / 50)); // 90-100 for excellent
        } else if (areaDiff <= 200) {
          score = 70 + (20 * (1 - (areaDiff - 50) / 150)); // 70-90 for good
        } else if (areaDiff <= 500) {
          score = 40 + (30 * (1 - (areaDiff - 200) / 300)); // 40-70 for fair
        } else {
          score = Math.max(0, 40 * Math.exp(-(areaDiff - 500) / 300)); // 0-40 for poor
        }
      }

      scores[sample.filename] = Math.round(score);
    });

    return scores;
  }, [baseline, samples, abnormalityWeights, differenceData, scoringMethod]);

  // Update parent component with scores when they change
  React.useEffect(() => {
    if (onScoreUpdate) {
      onScoreUpdate(sampleScores);
    }
  }, [sampleScores, onScoreUpdate]);

  // Find the corresponding File object for the selected sample
  const selectedSampleFile = sampleFiles && selectedSampleName ? 
    Array.from(sampleFiles).find(file => file.name === selectedSampleName) : 
    undefined;

  const handleResetZoom = () => {
    // Reset main graph
    if (chartRef.current) {
      chartRef.current.resetZoom();
    }
    // Reset difference graph
    if (differenceChartRef.current) {
      differenceChartRef.current.resetZoom();
    }
    useCustomIntervals.current = true;
    isZoomedMode.current = false;
    // Force complete chart re-render by updating keys (synchronized)
    setResetKey(prev => prev + 1);
    setDifferenceResetKey(prev => prev + 1);
  };

  const handleToggleGrid = () => {
    // Toggle grid for both graphs simultaneously
    setShowGrid(prev => !prev);
  };
  
  // Reset to custom intervals whenever new data is loaded
  React.useEffect(() => {
    useCustomIntervals.current = true;
    isZoomedMode.current = false;
    setShowGrid(true); // Reset grid to visible when new data loads
    if (chartRef.current) {
      chartRef.current.update('none');
    }
    if (differenceChartRef.current) {
      differenceChartRef.current.update('none');
    }
  }, [baseline, samples, selectedSampleName]);

  // Synchronize grid toggle across both graphs
  React.useEffect(() => {
    if (chartRef.current) {
      chartRef.current.update('none');
    }
    if (differenceChartRef.current) {
      differenceChartRef.current.update('none');
    }
  }, [showGrid]);

  // Transform x-values to equal-spaced positions (similar to backend export)
  const customXTicks = [4000, 3500, 3000, 2500, 2000, 1750, 1500, 1250, 1000, 750, 550];
  const isZoomedMode = useRef(false);
  
  const mapXToPosition = (xValues: number[]) => {
    return xValues.map(x => {
      if (x >= 4000) return 0;
      if (x <= 550) return customXTicks.length - 1;
      
      // Find which segment this x falls into
      for (let i = 0; i < customXTicks.length - 1; i++) {
        if (customXTicks[i] >= x && x >= customXTicks[i + 1]) {
          const x1 = customXTicks[i];
          const x2 = customXTicks[i + 1];
          const t = (x - x1) / (x2 - x1);
          return i + t;
        }
      }
      return 0;
    });
  };

  // Calculate dynamic y-axis max rounded up to nearest 0.5
  const getYMax = () => {
    if (!hasData) return 6;
    const maxBaseline = Math.max(...baseline!.y);
    const maxSample = Math.max(...sample.y);
    const actualMax = Math.max(maxBaseline, maxSample);
    // Round up to nearest 0.5 (e.g., 5.3 -> 5.5, 5.7 -> 6.0)
    return Math.ceil(actualMax * 2) / 2;
  };

  // Create chart data with proper x-y coordinate pairs
  const data = hasData ? (() => {
    // Remove .csv extension from filenames
    const baselineName = baseline!.filename.replace(/\.csv$/i, '');
    const sampleName = sample.filename.replace(/\.csv$/i, '');
    
    // Always use actual x values for data, transformation happens at display level
    const baselineData = baseline!.x.map((x: number, i: number) => ({ x, y: baseline!.y[i] }));
    const sampleData = sample.x.map((x: number, i: number) => ({ x, y: sample.y[i] }));
    
    return {
      datasets: [
        {
          label: `Baseline: ${baselineName}`,
          data: baselineData,
          borderColor: 'rgb(0, 100, 0)', // Darker green - fully opaque
          backgroundColor: 'rgba(0,100,0,0.05)',
          tension: 0.2,
          pointRadius: 0,
          pointHoverRadius: 3,
          borderWidth: 0.45,
          fill: false,
        },
        {
          label: `Sample: ${sampleName}`,
          data: sampleData,
          borderColor: 'rgb(0, 0, 255)', // Darker blue - fully opaque
          backgroundColor: 'rgb(0, 0, 255)',
          tension: 0.2,
          pointRadius: 0,
          pointHoverRadius: 3,
          borderWidth: 0.45,
          fill: false,
        }
      ]
    };
  })() : undefined;

  // Memoize chart options based on color mode, showGrid, and other dependencies
  const chartOptions = useMemo(() => {
    const isDark = colorMode === 'dark';
    const titleColor = isDark ? '#e0e0e0' : '#333';
    const gridColor = isDark ? '#4a5568' : '#e0e0e0';
    const tickColor = isDark ? '#cbd5e0' : '#666';
    const legendColor = isDark ? '#e0e0e0' : '#333';
    
    return {
              responsive: true,
              maintainAspectRatio: false,
              backgroundColor: isDark ? 'transparent' : 'white',
              color: titleColor,
              animation: {
                duration: 300,
                easing: 'easeInOutQuart' as const,
                delay: (context: any) => {
                  let delay = 0;
                  if (context.type === 'data' && context.mode === 'default') {
                    delay = context.dataIndex * 0.5;
                  }
                  return delay;
                }
              },
              transitions: {
                zoom: {
                  animation: {
                    duration: 0
                  }
                },
                active: {
                  animation: {
                    duration: 0
                  }
                }
              },
              interaction: {
                intersect: false,
                mode: 'index' as const
              },
              scales: {
                x: {
                  type: 'linear' as const,
                  title: { 
                    display: true, 
                    text: 'Wavenumber (cm⁻¹)',
                    font: { size: 14, weight: 'bold' as const },
                    color: titleColor
                  },
                  min: 4000,
                  max: 550,
                  reverse: true,
                  grid: {
                    display: showGrid,  // Toggle grid lines
                    color: gridColor,
                    lineWidth: 0.5
                  },
                  ticks: {
                    color: tickColor,
                    font: { size: 12 },
                    autoSkip: true,
                    maxTicksLimit: 15,
                    callback: function(value) {
                      const numValue = typeof value === 'number' ? value : parseFloat(value);
                      return Math.round(numValue);
                    }
                  },
                  afterBuildTicks: (axis) => {
                    if (useCustomIntervals.current && !isZoomedMode.current) {
                      // Equal-spaced custom ticks for default view
                      axis.ticks = customXTicks.map(value => ({ value }));
                    }
                  }
                },
                y: {
                  type: 'linear' as const,
                  title: { 
                    display: true, 
                    text: 'Absorbance',
                    font: { size: 14, weight: 'bold' as const },
                    color: titleColor
                  },
                  min: 0,
                  max: getYMax(), // Rounded to nearest 0.5 above actual max
                  grid: {
                    display: showGrid,  // Toggle grid lines
                    color: gridColor,
                    lineWidth: 0.5
                  },
                  ticks: {
                    color: tickColor,
                    font: { size: 12 },
                    stepSize: 0.5, // Interval of 0.5
                    callback: function(value) {
                      return typeof value === 'number' ? value.toFixed(1) : value;
                    }
                  }
                }
              },
              plugins: {
                tooltip: {
                  callbacks: {
                    title: function(tooltipItems) {
                      // Show only the x-value in the title
                      if (tooltipItems && tooltipItems[0] && tooltipItems[0].parsed && tooltipItems[0].parsed.x !== null) {
                        return `Wavenumber: ${tooltipItems[0].parsed.x.toFixed(2)} cm⁻¹`;
                      }
                      return '';
                    },
                    label: function(context) {
                      // Remove filename, show only "Baseline:" or "Sample:"
                      const datasetLabel = context.dataset.label || '';
                      const label = datasetLabel.split(':')[0]; // Get "Baseline" or "Sample"
                      if (context.parsed && context.parsed.y !== null) {
                        const value = context.parsed.y.toFixed(3);
                        return `${label}: ${value}`;
                      }
                      return label;
                    }
                  }
                },
                legend: { 
                  position: 'bottom' as const,
                  display: true,
                  align: 'end' as const,
                  labels: {
                    font: { size: 12 },
                    color: legendColor,
                    usePointStyle: true,  // Use circular point style
                    pointStyle: 'circle',
                    padding: 15,
                    boxWidth: 8,
                    boxHeight: 8,
                    generateLabels: (chart) => {
                      const datasets = chart.data.datasets;
                      return datasets.map((dataset, i) => {
                        const isVisible = chart.isDatasetVisible(i);
                        return {
                          text: dataset.label || '',
                          // If visible, fill with dataset color; if hidden, transparent (empty box)
                          fillStyle: isVisible ? (dataset.borderColor as string) : 'rgba(0,0,0,0)',
                          // If visible, border uses dataset color; if hidden, black border
                          strokeStyle: isVisible ? (dataset.borderColor as string) : (isDark ? '#fff' : '#000'),
                          lineWidth: 2,  // Border thickness
                          hidden: false,  // Never hide the legend item itself
                          datasetIndex: i,
                          fontColor: legendColor  // Add explicit text color for legend items
                        };
                      });
                    }
                  },
                  onClick: (e, legendItem, legend) => {
                    // Toggle dataset visibility when clicking legend
                    const index = legendItem.datasetIndex;
                    if (index !== undefined) {
                      const chart = legend.chart;
                      if (chart.isDatasetVisible(index)) {
                        chart.hide(index);
                      } else {
                        chart.show(index);
                      }
                      chart.update();
                    }
                  }
                },
                zoom: {
                  zoom: {
                    wheel: {
                      enabled: true,
                    },
                    pinch: {
                      enabled: true
                    },
                    mode: 'xy' as const,
                    onZoomStart: () => {
                      // Mark as zoomed mode
                      isZoomedMode.current = true;
                      return true;
                    },
                    onZoomComplete: ({ chart }) => {
                      // Stay in zoomed mode, don't re-render
                      isZoomedMode.current = true;
                    }
                  },
                  pan: {
                    enabled: true,
                    mode: 'xy' as const,
                    onPanStart: () => {
                      // Mark as zoomed mode
                      isZoomedMode.current = true;
                      return true;
                    },
                    onPanComplete: ({ chart }) => {
                      // Stay in zoomed mode
                      isZoomedMode.current = true;
                    }
                  },
                  limits: {
                    x: { min: 400, max: 4500 },
                    y: { min: 0, max: 7.0 } // Max zoom out limit
                  }
                }
              }
            };
  }, [colorMode, showGrid, getYMax]);

  return (
    <Box w="100%">
      <VStack align="start" spacing={4}>
        {hasData && (
          <HStack justify="space-between" w="100%" mb={4}>
            <Text fontSize="2xl" fontWeight="bold">FTIR Graph Analysis</Text>
            <HStack spacing={2}>
              <Button size="sm" onClick={handleToggleGrid} variant="outline" leftIcon={showGrid ? <ViewOffIcon /> : <ViewIcon />}>
                {showGrid ? 'Hide Grid' : 'Show Grid'}
              </Button>
              <Button size="sm" onClick={handleResetZoom} variant="outline" leftIcon={<RepeatIcon />}>
                Reset Zoom
              </Button>
            </HStack>
          </HStack>
        )}

        {/* Main Spectroscopy Graph */}
        {hasData ? (
          <Box w="100%" h="500px" bg={useColorModeValue('white', 'gray.800')} p={12} borderWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')} rounded="lg" shadow="sm">
              <Line key={`${resetKey}-${colorMode}`} ref={chartRef} data={data!} options={chartOptions} />
          </Box>
        ) : (
          <Text fontSize="sm" color={useColorModeValue('gray.500', 'gray.400')}>Upload baseline and at least one sample to see preview.</Text>
        )}
        
        {/* Deviation Heat Bar - Shows oxidation intensity */}
        {differenceData && (
          <DeviationHeatBar
            ref={differenceChartRef}
            x={differenceData.x}
            deviation={differenceData.deviation}
            selectedSampleName={selectedSampleName}
            showGrid={showGrid}
            resetKey={differenceResetKey}
            abnormalityWeights={abnormalityWeights}
          />
        )}
      </VStack>
    </Box>
  );
};

export default GraphPreview;
