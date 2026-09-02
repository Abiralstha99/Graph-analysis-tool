"""Pure-Python statistical summaries for graph comparisons."""

from collections.abc import Sequence
from math import isnan, nan, sqrt
from typing import TypedDict


class SeriesStats(TypedDict):
    count: int
    mean_y: float
    std_y: float
    min_y: float
    max_y: float


class Differences(TypedDict):
    mean_diff: float
    std_diff: float
    range_diff: float


class StatisticsSummary(TypedDict):
    baseline_stats: SeriesStats
    sample_stats: SeriesStats
    differences: Differences


def _series_stats(values: Sequence[float]) -> SeriesStats:
    """Return the statistics previously produced by the graph-analysis router."""
    # Match pandas Series reductions with the default skipna=True: NaN values
    # are omitted, while +/-Inf remain valid observations.
    raw_count = len(values)
    numeric_values = [float(value) for value in values if not isnan(float(value))]
    value_count = len(numeric_values)
    mean = sum(numeric_values) / value_count if value_count else nan
    variance = (
        sum((value - mean) ** 2 for value in numeric_values) / (value_count - 1)
        if value_count > 1
        else nan
    )

    return {
        "count": raw_count,
        "mean_y": mean,
        "std_y": sqrt(variance),
        "min_y": min(numeric_values) if numeric_values else nan,
        "max_y": max(numeric_values) if numeric_values else nan,
    }


def summarize_series(
    baseline: Sequence[float], sample: Sequence[float]
) -> StatisticsSummary:
    """Summarize baseline and sample y-values and their statistical differences."""
    baseline_stats = _series_stats(baseline)
    sample_stats = _series_stats(sample)

    baseline_range = baseline_stats["max_y"] - baseline_stats["min_y"]
    sample_range = sample_stats["max_y"] - sample_stats["min_y"]

    return {
        "baseline_stats": baseline_stats,
        "sample_stats": sample_stats,
        "differences": {
            "mean_diff": sample_stats["mean_y"] - baseline_stats["mean_y"],
            "std_diff": sample_stats["std_y"] - baseline_stats["std_y"],
            "range_diff": sample_range - baseline_range,
        },
    }
