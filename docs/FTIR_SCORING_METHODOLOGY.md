# FTIR Scoring Methodology

The backend compares a baseline FTIR series with one or more sample series and
returns a similarity score from 0 to 100. A higher score means the sample is
closer to the baseline under the selected metric; it is not a calibrated
oxidation percentage or a substitute for a validated laboratory method.

## Input and alignment

Each upload must:

- use `.csv`, `.txt`, or `.dat` (case-insensitive);
- be no larger than 10 MB;
- contain at least two data rows; and
- contain finite numeric values in its first two columns.

The parser reads files with `header=1`, so the first row is treated as
metadata. The first column is the wavenumber (`x`), and the second is
absorbance (`y`).

Baseline and sample points align when their wavenumbers differ by less than
`0.001` cm⁻¹. Only aligned points participate in scoring. Fewer than two
aligned points produces a neutral score of `50.0`.

## Zone weights

An optional list of zones can emphasize spectral regions:

```json
[
  {
    "min": 1800,
    "max": 1650,
    "weight": 200,
    "label": "Oxidation (C=O)",
    "key": "oxidation"
  }
]
```

The first zone that includes a wavenumber supplies its multiplier. The
percentage is converted to a multiplier (`200` becomes `2.0`); points outside
all configured zones use `1.0`. Boundaries are inclusive, so overlapping zones
are order-dependent.

Let `bᵢ` be baseline absorbance, `sᵢ` be sample absorbance,
`δᵢ = sᵢ - bᵢ`, and `wᵢ` be the zone multiplier.

## RMSE deviation

Weighted root mean square error is:

```text
RMSE = √(Σ(wᵢ × δᵢ²) / Σ(wᵢ))
```

The implementation maps it directly to a similarity score:

```text
RMSE score = clip(100 - 100 × RMSE, 0, 100)
```

RMSE measures the magnitude of absorbance change, regardless of whether peaks
grow or shrink. Squaring makes larger deviations contribute more strongly.

## Pearson correlation

The service calculates weighted Pearson correlation:

```text
r = Σ(wᵢ × (bᵢ - b̄) × (sᵢ - s̄))
    / √(Σ(wᵢ × (bᵢ - b̄)²) × Σ(wᵢ × (sᵢ - s̄)²))
```

It maps correlation to a score as follows:

```text
Pearson score = clip(((r + 1) / 2) × 100, 0, 100)
```

If either aligned series is constant, or the weight sum is zero, correlation is
set to `0`, producing a neutral Pearson score of `50.0`. Pearson measures
shape similarity rather than absolute intensity. A sample that is exactly
`2 ×` the baseline can score `100` by Pearson alone despite a large intensity
change.

## Area difference

The area method integrates absolute difference using weighted trapezoids:

```text
Δxᵢ = |xᵢ₊₁ - xᵢ|
ŵᵢ = (wᵢ + wᵢ₊₁) / 2

difference_area = Σ(Δxᵢ × (|δᵢ| + |δᵢ₊₁|) / 2 × ŵᵢ)
baseline_area   = Σ(Δxᵢ × (|bᵢ| + |bᵢ₊₁|) / 2 × ŵᵢ)
```

The score is normalized by the weighted baseline area:

```text
normalized_difference = difference_area / baseline_area
area score = clip(100 - 100 × normalized_difference, 0, 100)
```

If the weighted baseline area is zero, `normalized_difference` is set to zero,
so the area score is `100.0`.

## Hybrid score (default)

The default method blends the already-mapped RMSE and Pearson scores:

```text
Hybrid score = 0.6 × RMSE score + 0.4 × Pearson score
```

This is a direct 60/40 blend, not an RMSE base score minus a Pearson penalty.
It retains shape information while giving the larger contribution to intensity
deviation.

## Aggregate deviation data

For every baseline wavenumber, the service gathers the deltas from matching
samples, averages them, takes the absolute value, and applies the weight:

```text
deviation(x) = |mean(sᵢ - bᵢ across matching samples)| × w(x)
```

The result contains:

- `x`: baseline wavenumbers with at least one matching sample;
- `deviation`: weighted aggregate deviation at each returned wavenumber;
- `maxDeviation`: the maximum finite deviation; and
- `avgDeviation`: the arithmetic mean of finite deviations.

Direct FTIR routes use camelCase (`maxDeviation`, `avgDeviation`). Persisted
analysis responses use snake_case (`max_deviation`, `avg_deviation`).

## Score bands

| Score | Classification |
|---:|---|
| `90–100` | Good |
| `70–<90` | Warning |
| `<70` | Critical |

These are application display categories, not universal pass/fail limits for a
lubricant, machine, or laboratory method.

## Examples

For identical, non-constant aligned series, all four methods return `100`, and
the aggregate deviation is zero. An identical constant series produces a
neutral Pearson score of `50.0` because correlation is undefined; RMSE and
area still score the zero intensity difference.

For a proportional change such as `sample = 2 × baseline`, Pearson can remain
at `100` because the shape is unchanged. RMSE and area decrease as the
intensity difference grows; the hybrid score reflects that decrease through
its 60% RMSE component.

## Implementation reference

The authoritative implementation is
`backend/services/analysis_service.py`. Server-backed clients should render the
returned scores and deviation data without applying a second scoring formula.
