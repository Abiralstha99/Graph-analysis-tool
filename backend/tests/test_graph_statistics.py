import math

from backend.services.graph_statistics import summarize_series


def test_summarize_series_reports_mean_difference_and_baseline_count():
    stats = summarize_series([1.0, 3.0], [2.0, 6.0])

    assert stats["differences"]["mean_diff"] == 2.0
    assert stats["baseline_stats"]["count"] == 2


def test_summarize_series_ignores_nan_but_preserves_infinity():
    stats = summarize_series([1.0, math.nan, math.inf], [2.0, 6.0])

    assert stats["baseline_stats"]["count"] == 3
    assert math.isinf(stats["baseline_stats"]["mean_y"])
    assert stats["baseline_stats"]["min_y"] == 1.0
    assert math.isinf(stats["baseline_stats"]["max_y"])
    assert math.isnan(stats["baseline_stats"]["std_y"])


def test_summarize_series_uses_nan_std_for_singleton_series():
    stats = summarize_series([1.0], [2.0])

    assert math.isnan(stats["baseline_stats"]["std_y"])
    assert math.isnan(stats["sample_stats"]["std_y"])
