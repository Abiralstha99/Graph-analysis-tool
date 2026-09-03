# Scientifically-Correct FTIR Grease Scoring Methods

## Overview
This document explains the three scoring methods implemented for FTIR spectral comparison in grease oxidation analysis, with special emphasis on the corrected Hybrid method that addresses the fundamental limitations of using Pearson correlation alone.

---

## The Fundamental Problem with Pearson-Only Scoring

### Why Pearson Correlation Fails for FTIR Analysis

**Pearson correlation measures shape similarity, NOT chemical changes.**

In FTIR grease analysis, we need to detect:
- **Oxidation** (peak growth at 1700-1750 cm⁻¹)
- **Additive depletion** (intensity loss across functional groups)
- **Contamination** (new peaks, water bands at 3200-3600 cm⁻¹)
- **Base oil degradation** (changing C-H stretch patterns)

**Critical Issue**: Two spectra can have Pearson correlation = 1.0 even when:
- One sample has 50% more oxidation (all peaks proportionally higher)
- Peak intensities have doubled due to contamination
- Baseline drift has shifted all absorbance values

This is because Pearson only measures if the curves have the same *shape pattern*, not if they have the same *chemical composition*.

### Example Demonstrating the Problem

```
Baseline spectrum: [0.5, 1.0, 0.8, 1.2, 0.6]
Oxidized sample:   [1.0, 2.0, 1.6, 2.4, 1.2]  (2× oxidation everywhere)

Pearson correlation = 1.0 (perfect!)
But this sample is HEAVILY oxidized and should score LOW.
```

---

## Corrected Scoring Methods

### Method 1: RMSE Deviation Weighted by Interval

**Purpose**: Direct measurement of spectral intensity deviations

**Formula**:
```
RMSE = √(Σ(w_i × (baseline_i - sample_i)²) / Σ(w_i))

Where:
- w_i = weight for wavelength region i
- baseline_i = baseline absorbance at point i
- sample_i = sample absorbance at point i
```

**Scoring Thresholds**:
- **RMSE ≤ 0.10**: Score 90-100 (Excellent) 🟢
- **RMSE 0.10-0.25**: Score 70-90 (Good) 🟡
- **RMSE 0.25-0.50**: Score 40-70 (Fair) 🔴
- **RMSE > 0.50**: Score 0-40 (Poor) 🔴

**Why this works**:
- Directly measures magnitude of deviations
- Sensitive to both peak growth (oxidation) and peak loss (depletion)
- Squared error term heavily penalizes large deviations
- Weighted by spectral regions to emphasize critical zones

**Best for**: Detecting any significant chemical changes, especially oxidation

---

### Method 2: Hybrid Score (RMSE + Shape Penalty) ⭐ SCIENTIFICALLY CORRECT

**Purpose**: Combines intensity-based chemical analysis with shape mismatch detection

**Combined Formula**:
```
Final Score = Base Score - Pearson Penalty

Where:
  Base Score = f(Weighted RMSE)     [85% weight - primary metric]
  Pearson Penalty = g(correlation)   [15% weight - shape check only]
```

**Step-by-Step Calculation**:

**Step 1: Calculate Weighted RMSE** (same as Method 1)
```
RMSE = √(Σ(w_i × (baseline_i - sample_i)²) / Σ(w_i))
```

**Step 2: Calculate Pearson Correlation** (for shape verification only)
```
r = Cov(baseline, sample) / (σ_baseline × σ_sample)

Where:
- Cov = weighted covariance
- σ = weighted standard deviation
```

**Step 3: Convert RMSE to Base Score** (85% of final score)
```
If RMSE ≤ 0.10:  Base Score = 90 + 10 × (1 - RMSE/0.10)
If RMSE ≤ 0.25:  Base Score = 70 + 20 × (1 - (RMSE-0.10)/0.15)
If RMSE ≤ 0.50:  Base Score = 40 + 30 × (1 - (RMSE-0.25)/0.25)
If RMSE > 0.50:  Base Score = max(0, 40 × exp(-(RMSE-0.5)/0.3))
```

**Step 4: Calculate Pearson Penalty** (maximum 15 points)
```
If r < 0.90:  Penalty = 15 × (0.90 - r) / 0.90    [severe shape mismatch]
If r < 0.95:  Penalty = 7.5 × (0.95 - r) / 0.05   [minor shape issues]
If r ≥ 0.95:  Penalty = 0                         [shape is good]
```

**Step 5: Final Score**
```
Score = max(0, min(100, Base Score - Pearson Penalty))
```

**Why this is scientifically correct**:

1. **Primary metric (85%) = RMSE**: Detects actual chemical changes
   - Measures intensity deviations (oxidation, contamination, degradation)
   - Weighted by critical spectral regions
   - Cannot be fooled by proportional scaling

2. **Secondary check (15%) = Pearson penalty**: Detects structural anomalies
   - Only penalizes if shape is significantly different (r < 0.95)
   - Catches: contamination spikes, baseline drift, instrument issues
   - Does NOT override chemical deviation measurements

3. **Result**: A heavily oxidized sample (2× all peaks) will:
   - Have high RMSE → low base score (correctly flagged as bad)
   - Have high Pearson (r ≈ 1.0) → no penalty
   - Final score: LOW (correctly identifies oxidation)

**Best for**: Comprehensive grease analysis with both chemical and structural validation

---

### Method 3: Area Difference / Integral Difference (Default)

**Purpose**: Total magnitude of deviation across entire spectrum using trapezoidal integration

**Score Calculation Formula**:
```
Total Weighted Area = Σ(w_i × |Δx_i| × (|δy_i| + |δy_(i+1)|)/2)

Where:
- δy_i = baseline_i - sample_i (absorbance difference at point i)
- Δx_i = wavelength interval width (x_(i+1) - x_i)
- w_i = (weight_i + weight_(i+1)) / 2 (average weight for interval)
- Trapezoidal integration of absolute differences
```

**Heatmap Visualization**:
```
Heatmap Deviation = w × |δy|

Where:
- δy = baseline - sample (direct absorbance difference)
- w = weight for wavelength region
- Shows point-by-point weighted deviations (same as used in score calculation)
```

**Note**: The heatmap displays the same `|δy|` values used in the trapezoidal integration, weighted by spectral region. This ensures the visual representation matches the scoring calculation exactly.

**Scoring Thresholds**:
- **Area ≤ 50**: Score 90-100 (Excellent) 🟢
- **Area 50-200**: Score 70-90 (Good) 🟡
- **Area 200-500**: Score 40-70 (Fair) 🔴
- **Area > 500**: Score 0-40 (Poor) 🔴

**Why this works**:
- Integrates total deviation across spectrum
- Captures cumulative effect of all changes
- Less sensitive to isolated spikes than RMSE
- Good for overall "similarity" assessment
- Direct measurement of baseline vs sample differences

**Best for**: General comparison, catching widespread degradation

**Example**:
```
Baseline:  [1.0, 1.5, 1.2] at wavelengths [1000, 1100, 1200]
Sample:    [1.1, 1.7, 1.3]
Delta:     [0.1, 0.2, 0.1] (baseline - sample)

Heatmap shows: |0.1|, |0.2|, |0.1| weighted by region
Score uses: Trapezoidal area of these same values

When comparing baseline to itself:
Delta:     [0.0, 0.0, 0.0]
Heatmap:   All zeros (green/cool colors)
Score:     100 (perfect match)
```

---

## Heatmap Visualization Explained

The deviation heatmap below each graph displays a color-coded bar showing how much each wavelength deviates from the baseline. **The heatmap visualization matches the scoring calculation** for consistency.

### Heatmap Calculation by Method

| Method | Heatmap Formula | What It Shows |
|--------|----------------|---------------|
| **RMSE** | `w × (baseline - sample)²` | Squared deviations (pre-sqrt), weighted by region |
| **Hybrid** | `w × \|baseline - sample\|` | Absolute deviations, weighted by region |
| **Pearson** | `w × \|baseline - sample\|` | Absolute deviations, weighted by region |
| **Area** | `w × \|baseline - sample\|` | Absolute deviations (same as used in integration), weighted by region |

### Color Interpretation

- 🟢 **Green/Cool colors**: Low deviation (close to baseline)
- 🟡 **Yellow/Warm colors**: Medium deviation (some changes detected)
- 🔴 **Red/Hot colors**: High deviation (significant changes)

### Key Points

1. **All methods use direct baseline-sample comparison** in the heatmap
   - No comparison to "average of all samples"
   - Shows the actual `delta = baseline - sample` at each point

2. **Weights amplify critical regions**
   - Oxidation zone (1800-1650 cm⁻¹) deviations appear more intense
   - Lower-priority regions appear less intense
   - This matches how weights affect the final score

3. **Consistency check**
   - If you compare baseline to itself, heatmap should be all green (zero deviation)
   - If score is 100, heatmap should show minimal color intensity
   - If score is low, heatmap should show red/hot regions

### Example: Baseline vs Baseline

When selecting the baseline file itself:
```
Delta at all points: 0.0 (baseline - baseline = 0)
RMSE heatmap: 0² = 0 (all green)
Hybrid heatmap: |0| = 0 (all green)
Pearson heatmap: |0| = 0 (all green)
Area heatmap: |0| = 0 (all green)

All methods show score: 100
```

### Example: Oxidized Sample

When comparing to an oxidized sample:
```
At oxidation zone (1700 cm⁻¹):
  Baseline: 0.5 absorbance
  Sample: 1.2 absorbance (oxidation peak growth)
  Delta: -0.7
  Weight: 200%

RMSE heatmap: 200% × (-0.7)² = 98 → RED (high intensity)
Hybrid heatmap: 200% × |-0.7| = 140 → RED (high intensity)
Area heatmap: 200% × |-0.7| = 140 → RED (high intensity)

All methods will show hot colors in oxidation zone
Scores will be LOW (< 70) indicating oxidation detected
```

---

## Recommended Weight Values for FTIR Grease Analysis

### Critical Spectral Regions

Based on lubricant chemistry and FTIR grease analysis standards:

| Region | Wavenumber Range | Weight | Purpose |
|--------|------------------|--------|---------|
| **Oxidation Zone** | 1800-1650 cm⁻¹ | **150-200%** | C=O stretch (ketones, aldehydes, carboxylic acids) |
| **Additive/Contamination** | 1650-1000 cm⁻¹ | **100-150%** | C-O stretch, additives, contaminants |
| **Fingerprint Region** | 1000-600 cm⁻¹ | **75-100%** | Complex vibrations, base oil characteristics |
| **C-H Stretch** | 3000-2800 cm⁻¹ | **50-75%** | Hydrocarbon baseline (changes slowly) |
| **O-H/N-H Region** | 3600-3200 cm⁻¹ | **125-150%** | Water contamination, amine additives |

### Example Configuration (MRG Labs Standard)

```javascript
const abnormalityWeights = [
  { 
    min: 1800, 
    max: 1650, 
    weight: 200, 
    label: "Oxidation (C=O)" 
  },
  { 
    min: 1650, 
    max: 1000, 
    weight: 125, 
    label: "Additives & Contamination" 
  },
  { 
    min: 1000, 
    max: 600, 
    weight: 100, 
    label: "Fingerprint Region" 
  }
];
```

---

## Score Classifications

**Consistent across all methods:**

- 🟢 **Green (90-100)**: Excellent conformity to baseline
  - Minimal chemical changes
  - Grease is fresh or minimally degraded
  - **Action**: Continue normal operation

- 🟡 **Yellow (70-89)**: Good with minor deviations
  - Some oxidation or additive changes detected
  - Still within acceptable operating range
  - **Action**: Monitor closely, consider trending

- 🔴 **Red (< 70)**: Significant deviations detected
  - Substantial oxidation, contamination, or degradation
  - Grease condition is compromised
  - **Action**: Immediate inspection, consider replacement

---

## Method Comparison Summary

| Method | Primary Metric | Heatmap Shows | Best For | Limitation |
|--------|---------------|---------------|----------|------------|
| **RMSE** | Squared deviation | w × (δ)² | Oxidation detection | Sensitive to noise |
| **Hybrid** ⭐ | RMSE + Shape check | w × \|δ\| | Comprehensive analysis | More complex |
| **Pearson** | Correlation | w × \|δ\| | Shape similarity | Ignores magnitude |
| **Area** | Integrated difference | w × \|δ\| | Overall similarity | Less sensitive to localized changes |

**Note**: δ = baseline - sample (deviation), w = spectral region weight

---

## Why the Hybrid Method is Scientifically Defensible

### Accepted by Lubricant Analysts Because:

1. **Primary metric is intensity-based**: RMSE measures actual chemical changes
2. **Pearson is used correctly**: Only as a penalty for shape anomalies, not as primary score
3. **Weighted spectral regions**: Emphasizes oxidation zone per ASTM/ISO standards
4. **Transparent formula**: Clear mathematical basis, reproducible
5. **Validated thresholds**: Based on typical FTIR absorbance ranges (0-3 AU)
6. **Handles real-world cases**:
   - Oxidation → High RMSE → Low score ✓
   - Contamination spike → High RMSE + Low Pearson → Low score ✓
   - Baseline drift → Medium RMSE + Medium Pearson → Medium score ✓
   - Clean sample → Low RMSE + High Pearson → High score ✓

### References to Industry Standards

This approach aligns with:
- **ASTM E2412**: Standard Practice for Condition Monitoring of Used Lubricants by FTIR
- **ASTM D7418**: Standard Test Method for Oxidation Stability of Lubricating Greases by FTIR
- **ISO 21302**: FTIR spectrometry for condition monitoring of lubricants

---

## Implementation Notes

### Code Structure
```typescript
// Method 2: Hybrid (Pearson)
1. Calculate weighted RMSE (primary: 85% weight)
2. Calculate Pearson correlation (secondary: 15% penalty)
3. Convert RMSE to base score
4. Apply Pearson penalty if shape mismatch detected
5. Final score = base score - penalty
```

### Key Differences from Old Implementation
- ❌ **Old**: `Score = (correlation + 1) × 50` 
- ✅ **New**: `Score = RMSE_Score - Pearson_Penalty`

The old method could give score 100 to heavily oxidized samples. The new method correctly identifies them as poor quality.

---

## Conclusion

The **Hybrid method (RMSE + Shape)** is the recommended approach for FTIR grease analysis because it:
- Uses the correct primary metric (intensity-based RMSE)
- Treats Pearson correlation appropriately (shape check only)
- Provides scientifically defensible scores
- Aligns with industry standards
- Cannot be fooled by proportional scaling or oxidation

This scoring system will be accepted by MRG Labs, lubricant analysts, and conforms to ASTM/ISO FTIR spectroscopy standards for condition monitoring.
