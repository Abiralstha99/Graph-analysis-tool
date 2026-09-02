import { describe, expect, it } from 'vitest';
import { diff } from './series';

describe('diff', () => {
  it('subtracts baseline y values from sample y values', () => {
    expect(diff({ x: [1, 2], y: [3, 5] }, { x: [1, 2], y: [4, 1] }).y).toEqual([1, -4]);
  });

  it('rejects series with mismatched x and y lengths', () => {
    expect(() => diff({ x: [1, 2], y: [3] }, { x: [1, 2], y: [4, 1] })).toThrow(
      'Series x and y arrays must have the same length',
    );
  });

  it('rejects baseline and sample series with different lengths', () => {
    expect(() => diff({ x: [1, 2], y: [3, 5] }, { x: [1], y: [4] })).toThrow(
      'Baseline and sample series must have the same length',
    );
  });

  it('rejects a malformed sample series', () => {
    expect(() => diff({ x: [1, 2], y: [3, 5] }, { x: [1, 2], y: [4] })).toThrow(
      'Series x and y arrays must have the same length',
    );
  });
});
