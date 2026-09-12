"""Pure FTIR parsing and scoring service."""

from __future__ import annotations

import io
import json
import math

import numpy as np
import pandas as pd


SUPPORTED_METHODS = frozenset(("hybrid", "rmse", "pearson", "area"))


class AnalysisError(Exception):
    """A user-actionable analysis failure that should not be retried."""

    code = "ANALYSIS_ERROR"


class AnalysisService:
    def run(
        self,
        baseline_bytes: bytes,
        baseline_name: str,
        samples: list[tuple[bytes, str]],
        scoring_method: str,
        zone_weights: list[dict] | None,
        analysis_id: str,
        db,
    ) -> None:
        try:
            result = self.calculate(
                baseline_bytes,
                baseline_name,
                samples,
                scoring_method=scoring_method,
                zone_weights=zone_weights,
            )
        except (ValueError, UnicodeError) as exc:
            raise AnalysisError(str(exc)) from exc

        sample_filenames = [name for _, name in samples]
        cursor = db.cursor()
        cursor.execute(
            """
            UPDATE analyses
            SET scores = %s,
                deviation_data = %s,
                summary = %s,
                baseline_filename = %s,
                sample_filenames = %s,
                scoring_method = %s,
                error_message = NULL
            WHERE id = %s
              AND status <> 'cancelled'
            """,
            (
                json.dumps(result["scores"]),
                json.dumps(result["deviationData"]),
                json.dumps(result["summary"]),
                baseline_name,
                json.dumps(sample_filenames),
                scoring_method,
                analysis_id,
            ),
        )
        db.commit()

    def calculate(
        self,
        baseline_bytes: bytes,
        baseline_name: str,
        samples: list[tuple[bytes, str]],
        scoring_method: str = "hybrid",
        zone_weights: list[dict] | None = None,
    ) -> dict:
        if scoring_method not in SUPPORTED_METHODS:
            raise ValueError(f"Unsupported scoring method: {scoring_method}")
        baseline = self._parse(baseline_bytes, baseline_name)
        if not samples:
            raise ValueError("At least one sample is required")
        parsed_samples = [(self._parse(data, name), name) for data, name in samples]
        weights = zone_weights or []

        scores = {
            name: self._score(baseline, sample, scoring_method, weights)
            for sample, name in parsed_samples
        }
        deviation_x: list[float] = []
        deviation: list[float] = []
        for index, baseline_x in enumerate(baseline[0]):
            deltas = []
            for sample, _ in parsed_samples:
                match = self._matching_index(sample[0], baseline_x)
                if match is not None:
                    deltas.append(sample[1][match] - baseline[1][index])
            if deltas:
                deviation_x.append(float(baseline_x))
                deviation.append(abs(float(np.mean(deltas))) * self._weight(baseline_x, weights))

        finite_deviation = [value for value in deviation if math.isfinite(value)]
        max_deviation = max(finite_deviation, default=0.0)
        avg_deviation = float(np.mean(finite_deviation)) if finite_deviation else 0.0
        summary = {"totalSamples": len(scores), "good": 0, "warning": 0, "critical": 0}
        for score in scores.values():
            band = "good" if score >= 90 else "warning" if score >= 70 else "critical"
            summary[band] += 1
        return {
            "scores": scores,
            "deviationData": {
                "x": deviation_x,
                "deviation": finite_deviation,
                "maxDeviation": max_deviation,
                "avgDeviation": avg_deviation,
            },
            "summary": summary,
        }

    @staticmethod
    def _parse(data: bytes, name: str) -> tuple[np.ndarray, np.ndarray]:
        try:
            frame = pd.read_csv(io.BytesIO(data), header=1)
            values = frame.iloc[:, :2].apply(pd.to_numeric, errors="coerce")
        except (pd.errors.EmptyDataError, pd.errors.ParserError, IndexError, ValueError) as exc:
            raise ValueError(f"Invalid numeric data in {name}") from exc
        if values.empty or values.shape[1] < 2 or values.isna().any().any():
            raise ValueError(f"Invalid numeric data in {name}: finite numeric x/y data is required")
        x = values.iloc[:, 0].to_numpy(dtype=float)
        y = values.iloc[:, 1].to_numpy(dtype=float)
        if not (np.isfinite(x).all() and np.isfinite(y).all()):
            raise ValueError(f"Invalid numeric data in {name}: finite numeric x/y data is required")
        return x, y

    @staticmethod
    def _matching_index(x_values: np.ndarray, target: float) -> int | None:
        matches = np.flatnonzero(np.abs(x_values - target) < 0.001)
        return int(matches[0]) if matches.size else None

    @classmethod
    def _weight(cls, wavelength: float, zones: list[dict]) -> float:
        for zone in zones:
            try:
                low = float(zone["min"])
                high = float(zone["max"])
                weight = float(zone["weight"]) / 100.0
            except (KeyError, TypeError, ValueError):
                continue
            if all(math.isfinite(value) for value in (low, high, weight)):
                if min(low, high) <= wavelength <= max(low, high):
                    return weight
        return 1.0

    @classmethod
    def _aligned(cls, baseline: tuple[np.ndarray, np.ndarray], sample: tuple[np.ndarray, np.ndarray]):
        bx, by = baseline
        sx, sy = sample
        pairs = [(i, match) for i, x in enumerate(bx) if (match := cls._matching_index(sx, x)) is not None]
        if not pairs:
            return np.array([]), np.array([]), np.array([])
        indices, sample_indices = zip(*pairs)
        return bx[list(indices)], by[list(indices)], sy[list(sample_indices)]

    @classmethod
    def _score(cls, baseline, sample, method: str, zones: list[dict]) -> float:
        x, base_y, sample_y = cls._aligned(baseline, sample)
        if len(x) < 2:
            return 50.0
        weights = np.array([cls._weight(value, zones) for value in x], dtype=float)
        deltas = sample_y - base_y
        weight_sum = float(weights.sum())
        rmse = math.sqrt(float(np.sum(weights * deltas**2)) / weight_sum) if weight_sum else 0.0
        rmse_score = float(np.clip(100.0 - rmse * 100.0, 0.0, 100.0))

        if np.ptp(base_y) == 0 or np.ptp(sample_y) == 0 or not weight_sum:
            correlation = 0.0
        else:
            base_mean = float(np.sum(weights * base_y) / weight_sum)
            sample_mean = float(np.sum(weights * sample_y) / weight_sum)
            covariance = float(np.sum(weights * (base_y - base_mean) * (sample_y - sample_mean)) / weight_sum)
            base_std = math.sqrt(float(np.sum(weights * (base_y - base_mean) ** 2) / weight_sum))
            sample_std = math.sqrt(float(np.sum(weights * (sample_y - sample_mean) ** 2) / weight_sum))
            correlation = covariance / (base_std * sample_std) if base_std and sample_std else 0.0
            correlation = float(np.clip(correlation, -1.0, 1.0))
        pearson_score = float(np.clip(((correlation + 1.0) / 2.0) * 100.0, 0.0, 100.0))

        if method == "rmse":
            return rmse_score
        if method == "pearson":
            return pearson_score
        if method == "area":
            distances = np.abs(np.diff(x))
            trapezoid_weights = (weights[:-1] + weights[1:]) / 2
            difference_area = float(np.sum(distances * (np.abs(deltas[:-1]) + np.abs(deltas[1:])) / 2 * trapezoid_weights))
            baseline_area = float(np.sum(distances * (np.abs(base_y[:-1]) + np.abs(base_y[1:])) / 2 * trapezoid_weights))
            normalized = difference_area / baseline_area if baseline_area else 0.0
            return float(np.clip(100.0 - normalized * 100.0, 0.0, 100.0))
        return rmse_score * 0.6 + pearson_score * 0.4
