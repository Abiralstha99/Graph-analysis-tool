export interface Series {
  x: number[];
  y: number[];
}

export interface DiffResult {
  x: number[];
  y: number[];
}

function validateSeries(series: Series, name: string): void {
  if (series.x.length !== series.y.length) {
    throw new Error(`Series x and y arrays must have the same length (${name})`);
  }
}

export function diff(baseline: Series, sample: Series): DiffResult {
  validateSeries(baseline, 'baseline');
  validateSeries(sample, 'sample');

  if (baseline.x.length !== sample.x.length) {
    throw new Error('Baseline and sample series must have the same length');
  }

  return {
    x: baseline.x,
    y: baseline.y.map((baselineY, index) => sample.y[index] - baselineY),
  };
}
