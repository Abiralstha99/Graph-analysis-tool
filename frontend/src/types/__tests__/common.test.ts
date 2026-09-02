import { getSampleStatus } from '../common';

describe('getSampleStatus', () => {
  it('classifies scores at the good, warning, and critical boundaries', () => {
    expect(getSampleStatus(85)).toBe('good');
    expect(getSampleStatus(70)).toBe('warning');
    expect(getSampleStatus(69)).toBe('critical');
  });
});
