import io
import math

import pytest

from backend.services.analysis_service import AnalysisService


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
