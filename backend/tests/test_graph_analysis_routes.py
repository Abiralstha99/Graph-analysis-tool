from inspect import signature

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.graph_analysis import generate_graph_insights, router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_ftir_analyze_route_replaces_legacy_route():
    paths = {route.path for route in app.routes}

    assert "/analysis/ftir/analyze" in paths
    assert "/analysis/generate_insights" not in paths


def test_ftir_analyze_preserves_upload_and_sample_name_contract():
    parameters = signature(generate_graph_insights).parameters

    assert list(parameters) == ["baseline", "sample", "sample_name"]
    assert parameters["sample_name"].default.default is None


def csv_file(values="1,2\n2,3\n3,4\n"):
    return "metadata\nx,y\n" + values


def test_ftir_deviation_route_returns_server_calculation():
    response = client.post("/analysis/ftir/deviation", files={
        "baseline": ("baseline.csv", csv_file(), "text/csv"),
        "sample": ("sample.csv", csv_file(), "text/csv"),
    })

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["deviationData"]["deviation"] == [0.0, 0.0, 0.0]
    assert response.json()["sampleInfo"]["filename"] == "sample.csv"


def test_ftir_scores_route_accepts_repeated_samples_and_weights():
    response = client.post("/analysis/ftir/scores", data={
        "scoring_method": "rmse",
        "zone_weights": '[{"min": 1, "max": 3, "weight": 50, "label": "all", "key": "all"}]',
    }, files=[
        ("baseline", ("baseline.csv", csv_file(), "text/csv")),
        ("samples", ("one.csv", csv_file(), "text/csv")),
        ("samples", ("two.csv", csv_file("1,2\n2,4\n3,4\n"), "text/csv")),
    ])

    assert response.status_code == 200
    body = response.json()
    assert set(body["scores"]) == {"one.csv", "two.csv"}
    assert "deviationData" in body
    assert body["summary"]["totalSamples"] == 2


def test_ftir_scores_route_returns_canonical_validation_error():
    response = client.post("/analysis/ftir/scores", data={"scoring_method": "invalid"}, files={
        "baseline": ("baseline.csv", csv_file(), "text/csv"),
        "samples": ("sample.csv", csv_file(), "text/csv"),
    })

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_ftir_session_save_route_is_not_implemented():
    response = client.post("/analysis/ftir/sessions/save")

    assert response.status_code == 501
    assert response.json() == {"error": "FTIR session save is not implemented yet"}


def test_ftir_session_history_route_is_not_implemented():
    response = client.get("/analysis/ftir/sessions/history")

    assert response.status_code == 501
    assert response.json() == {"error": "FTIR session history is not implemented yet"}
