export interface Series {
  name: string;
  points: Array<{ x: number; y: number }>;
}

export interface DiffResult {
  x: number[];
  delta: number[];
}

export function diff(baseline: Series, sample: Series): DiffResult {
  const x: number[] = [];
  const delta: number[] = [];

  const baselineMap = new Map<number, number>();
  for (const point of baseline.points) {
    baselineMap.set(point.x, point.y);
  }

  for (const samplePoint of sample.points) {
    const baselineY = baselineMap.get(samplePoint.x);
    if (baselineY !== undefined) {
      x.push(samplePoint.x);
      delta.push(samplePoint.y - baselineY);
    }
  }

  return { x, delta };
}
