import pytest


fastapi = pytest.importorskip("fastapi")
pandas = pytest.importorskip("pandas")

from backend.graph_analysis import analyze_data_statistics


def test_analysis_statistics_helper_preserves_response_keys():
    baseline = pandas.DataFrame({"x": [10.0, 20.0], "y": [1.0, 3.0]})
    sample = pandas.DataFrame({"x": [10.0, 20.0], "y": [2.0, 6.0]})

    stats = analyze_data_statistics(baseline, sample, "sample")

    assert set(stats) == {"sample_name", "baseline_stats", "sample_stats", "differences"}
    assert set(stats["baseline_stats"]) == {
        "count", "mean_y", "std_y", "min_y", "max_y", "range_x"
    }
    assert stats["baseline_stats"]["range_x"] == [10.0, 20.0]
