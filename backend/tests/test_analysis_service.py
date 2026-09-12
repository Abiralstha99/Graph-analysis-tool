import json

import pytest

from backend.services.analysis_service import AnalysisError, AnalysisService


def csv_bytes(rows: list[tuple[float, float]]) -> bytes:
    return ("metadata\n" + "x,y\n" + "\n".join(f"{x},{y}" for x, y in rows)).encode()


@pytest.mark.parametrize("method", ["rmse", "pearson", "area", "hybrid"])
def test_calculate_returns_exact_score_for_supported_method(method):
    result = AnalysisService().calculate(
        csv_bytes([(3, 1), (2, 2), (1, 3)]),
        "baseline.csv",
        [(csv_bytes([(3, 1), (2, 2), (1, 3)]), "same.csv")],
        scoring_method=method,
    )

    assert result["scores"]["same.csv"] == pytest.approx(100.0)
    assert result["summary"] == {"totalSamples": 1, "good": 1, "warning": 0, "critical": 0}


def test_calculate_uses_tolerance_weights_and_aggregate_deviation():
    result = AnalysisService().calculate(
        csv_bytes([(4000, 1), (3999, 2), (3998, 3)]),
        "baseline.csv",
        [
            (csv_bytes([(4000.0005, 2), (3999, 4), (3998, 2)]), "one.csv"),
            (csv_bytes([(4000, 0), (3999.0009, 3), (3998, 4)]), "two.csv"),
        ],
        zone_weights=[{"min": 4000, "max": 3999, "weight": 50, "label": "zone", "key": "z"}],
    )

    assert result["deviationData"]["x"] == [4000.0, 3999.0, 3998.0]
    assert result["deviationData"]["deviation"] == pytest.approx([0.0, 0.75, 0.0])
    assert result["deviationData"]["maxDeviation"] == pytest.approx(0.75)
    assert result["deviationData"]["avgDeviation"] == pytest.approx(0.25)


def test_calculate_returns_neutral_score_for_insufficient_overlap_and_constant_pearson():
    service = AnalysisService()
    insufficient = service.calculate(
        csv_bytes([(1, 1), (2, 2)]), "b.csv", [(csv_bytes([(9, 1)]), "s.csv")]
    )
    constant = service.calculate(
        csv_bytes([(1, 1), (2, 1), (3, 1)]),
        "b.csv",
        [(csv_bytes([(1, 1), (2, 1), (3, 1)]), "s.csv")],
        scoring_method="pearson",
    )

    assert insufficient["scores"] == {"s.csv": 50.0}
    assert constant["scores"] == {"s.csv": 50.0}


def test_calculate_rejects_invalid_csv_and_method():
    service = AnalysisService()
    with pytest.raises(ValueError, match="scoring method"):
        service.calculate(csv_bytes([(1, 1)]), "b.csv", [], scoring_method="bad")
    with pytest.raises(ValueError, match="finite numeric"):
        service.calculate(b"metadata\nx,y\nNaN,1\n", "b.csv", [])


class PersistingCursor:
    def __init__(self):
        self.sql = None
        self.params = None

    def execute(self, sql, params):
        self.sql = sql
        self.params = params


class PersistingDB:
    def __init__(self):
        self.cursor_instance = PersistingCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


def test_run_calculates_and_persists_analysis_result():
    db = PersistingDB()

    AnalysisService().run(
        csv_bytes([(1, 1), (2, 2), (3, 3)]),
        "baseline.csv",
        [(csv_bytes([(1, 1), (2, 2), (3, 3)]), "sample.csv")],
        "hybrid",
        [{"min": 1, "max": 3, "weight": 50, "label": "all", "key": "all"}],
        "analysis-id",
        db,
    )

    assert "UPDATE analyses" in db.cursor_instance.sql
    scores, deviation_data, summary, baseline_name, sample_names, method, analysis_id = (
        db.cursor_instance.params
    )
    assert json.loads(scores) == {"sample.csv": 100.0}
    assert json.loads(deviation_data)["maxDeviation"] == 0.0
    assert json.loads(summary) == {"totalSamples": 1, "good": 1, "warning": 0, "critical": 0}
    assert baseline_name == "baseline.csv"
    assert json.loads(sample_names) == ["sample.csv"]
    assert method == "hybrid"
    assert analysis_id == "analysis-id"
    assert db.commits == 1


def test_run_wraps_invalid_input_as_non_retryable_analysis_error():
    with pytest.raises(AnalysisError, match="finite numeric"):
        AnalysisService().run(
            b"metadata\nx,y\nNaN,1\n",
            "baseline.csv",
            [(csv_bytes([(1, 1), (2, 2)]), "sample.csv")],
            "hybrid",
            None,
            "analysis-id",
            PersistingDB(),
        )
