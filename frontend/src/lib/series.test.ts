import { describe, expect, it } from 'vitest';
import { diff } from './series';

describe('legacy point-series diff', () => {
  it('matches by x in sample order and omits unmatched points', () => {
    expect(
      diff(
        { name: 'baseline', points: [{ x: 1, y: 3 }, { x: 2, y: 5 }] },
        { name: 'sample', points: [{ x: 2, y: 1 }, { x: 3, y: 8 }] },
      ),
    ).toEqual({ x: [2], delta: [-4] });
  });
});
