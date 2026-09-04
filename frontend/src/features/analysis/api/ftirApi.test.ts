import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../../services/api';
import { FTIRApiService } from './ftirApi';

vi.mock('../../../services/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('FTIRApiService.analyzeSamples', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockReset();
  });

  it('uses the backend FTIR analyze contract for every sample', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({
        data: {
          sample_name: 'sample-one.csv',
          statistics: { differences: { mean_diff: 0.1 } },
          ai_insights: 'First sample insight',
          metadata: { baseline_file: 'baseline.csv', sample_file: 'sample-one.csv' },
        },
      })
      .mockResolvedValueOnce({
        data: {
          sample_name: 'sample-two.csv',
          statistics: { differences: { mean_diff: 0.2 } },
          ai_insights: 'Second sample insight',
          metadata: { baseline_file: 'baseline.csv', sample_file: 'sample-two.csv' },
        },
      });

    const baseline = new File(['baseline'], 'baseline.csv', { type: 'text/csv' });
    const samples = [
      new File(['one'], 'sample-one.csv', { type: 'text/csv' }),
      new File(['two'], 'sample-two.csv', { type: 'text/csv' }),
    ];

    const response = await FTIRApiService.analyzeSamples({
      baseline,
      samples,
      scoringMethod: 'hybrid',
      zoneWeights: [],
    });

    expect(api.post).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.post).mock.calls.map(([url]) => url)).toEqual([
      '/analysis/ftir/analyze',
      '/analysis/ftir/analyze',
    ]);

    for (const [url, formData, config] of vi.mocked(api.post).mock.calls) {
      expect(url).toBe('/analysis/ftir/analyze');
      expect(formData).toBeInstanceOf(FormData);
      expect((formData as FormData).get('baseline')).toBe(baseline);
      expect((formData as FormData).get('sample')).toBeInstanceOf(File);
      expect((formData as FormData).get('samples')).toBeNull();
      expect((formData as FormData).get('scoring_method')).toBeNull();
      expect((formData as FormData).get('zone_weights')).toBeNull();
      expect((formData as FormData).get('sample_name')).toBe(
        ((formData as FormData).get('sample') as File).name,
      );
      expect(config).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } });
    }

    expect(response).toMatchObject({
      success: true,
      results: [
        { sample_name: 'sample-one.csv', ai_insights: 'First sample insight' },
        { sample_name: 'sample-two.csv', ai_insights: 'Second sample insight' },
      ],
      metadata: { baseline_filename: 'baseline.csv', sample_count: 2 },
    });
  });
});
