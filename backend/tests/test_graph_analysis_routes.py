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


def test_ftir_deviation_route_is_not_implemented():
    response = client.post("/analysis/ftir/deviation")

    assert response.status_code == 501
    assert response.json() == {"error": "FTIR deviation analysis is not implemented yet"}


def test_ftir_scores_route_is_not_implemented():
    response = client.post("/analysis/ftir/scores")

    assert response.status_code == 501
    assert response.json() == {"error": "FTIR scores analysis is not implemented yet"}


def test_ftir_session_save_route_is_not_implemented():
    response = client.post("/analysis/ftir/sessions/save")

    assert response.status_code == 501
    assert response.json() == {"error": "FTIR session save is not implemented yet"}


def test_ftir_session_history_route_is_not_implemented():
    response = client.get("/analysis/ftir/sessions/history")

    assert response.status_code == 501
    assert response.json() == {"error": "FTIR session history is not implemented yet"}
