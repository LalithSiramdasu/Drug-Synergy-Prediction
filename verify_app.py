import io
import json
import math
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"


def _maybe_reexec_project_venv():
    """Use the project virtualenv when available so `python verify_app.py` is reliable."""
    if os.environ.get("VERIFY_APP_REEXECED") == "1":
        return
    if not VENV_PYTHON.is_file():
        return

    current_python = Path(sys.executable).resolve()
    target_python = VENV_PYTHON.resolve()
    if current_python == target_python:
        return

    child_env = os.environ.copy()
    child_env["VERIFY_APP_REEXECED"] = "1"
    completed = subprocess.run(
        [str(target_python), str(Path(__file__).resolve())],
        env=child_env,
        check=False,
    )
    raise SystemExit(completed.returncode)


_maybe_reexec_project_venv()
os.chdir(ROOT_DIR)


class VerificationFailure(Exception):
    pass


class VerificationRunner:
    def __init__(self):
        self.failures = []
        self.passes = 0

    def check(self, name, callback):
        try:
            detail = callback()
        except Exception as exc:
            self.failures.append((name, str(exc)))
            print(f"FAIL {name} - {exc}")
            return

        self.passes += 1
        suffix = f" - {detail}" if detail else ""
        print(f"PASS {name}{suffix}")

    def finish(self):
        print()
        print(f"Passed: {self.passes}")
        print(f"Failed: {len(self.failures)}")

        if self.failures:
            print()
            print("FAILURE DETAILS")
            for name, reason in self.failures:
                print(f"- {name}: {reason}")
            raise SystemExit(1)

        print("ALL VERIFICATION TESTS PASSED")


def _json_response(response, endpoint_name):
    data = response.get_json(silent=True)
    if not isinstance(data, dict):
        body = response.get_data(as_text=True)[:400]
        raise VerificationFailure(
            f"{endpoint_name} did not return a JSON object. HTTP {response.status_code}. Body: {body}"
        )
    return data


def _require_http_ok(response, endpoint_name):
    if response.status_code < 200 or response.status_code >= 300:
        data = _json_response(response, endpoint_name)
        raise VerificationFailure(
            f"{endpoint_name} returned HTTP {response.status_code}: {data}"
        )


def _require_status_success(data, endpoint_name):
    if data.get("status") != "success":
        raise VerificationFailure(f"{endpoint_name} status was not success: {data}")


def _request_json(client, method, path, endpoint_name, **kwargs):
    response = getattr(client, method)(path, **kwargs)
    _require_http_ok(response, endpoint_name)
    data = _json_response(response, endpoint_name)
    _require_status_success(data, endpoint_name)
    return data


def _score_from_prediction(data):
    score = data.get("final_predicted_COMBOSCORE")
    if not isinstance(score, (int, float)) or not math.isfinite(score):
        raise VerificationFailure(f"Invalid final_predicted_COMBOSCORE: {score}")
    return float(score)


def _label_from_prediction(data):
    label = str(data.get("label") or data.get("prediction_label") or "").strip().lower()
    if not label:
        raise VerificationFailure(f"Missing prediction label in response: {data}")
    return label


def _assert_label(data, expected_label):
    actual_label = _label_from_prediction(data)
    if actual_label != expected_label:
        raise VerificationFailure(f"Expected label {expected_label}, got {actual_label}.")


def _assert_prediction_case(data, expected_label, score_rule):
    score = _score_from_prediction(data)
    _assert_label(data, expected_label)
    if not score_rule(score):
        raise VerificationFailure(
            f"Score {score:.6f} did not match expected rule for {expected_label}."
        )
    return score


def _snapshot_directory(directory):
    directory.mkdir(parents=True, exist_ok=True)
    return {path.name for path in directory.iterdir()}


def _cleanup_new_files(directory, before_names):
    if not directory.exists():
        return

    resolved_directory = directory.resolve()
    for path in directory.iterdir():
        if path.name in before_names or not path.is_file():
            continue

        resolved_path = path.resolve()
        if resolved_path.parent != resolved_directory:
            continue
        path.unlink()


def _find_demo_case(demo_cases, case_type):
    matches = [case for case in demo_cases if case.get("case_type") == case_type]
    if len(matches) != 1:
        raise VerificationFailure(f"Expected one {case_type} demo case, found {len(matches)}.")
    return matches[0]


def build_checks(client, config):
    neutral_payload = {"NSC1": 740, "NSC2": 750, "CELLNAME": "786-0"}
    synergy_payload = {"NSC1": 761431, "NSC2": 761432, "CELLNAME": "SK-MEL-5"}
    antagonism_payload = {"NSC1": 92859, "NSC2": 141540, "CELLNAME": "HL-60(TB)"}

    def check_health():
        data = _request_json(client, "get", "/api/health", "GET /api/health")
        expectations = {
            "available_drugs": 100,
            "available_cell_lines": 60,
            "feature_column_count": 526,
            "model_count": 60,
        }
        for key, expected in expectations.items():
            actual = data.get(key)
            if actual != expected:
                raise VerificationFailure(f"Expected {key}={expected}, got {actual}.")
        return "100 drugs, 60 cell lines, 526 features, 60 models"

    def check_drugs():
        data = _request_json(client, "get", "/api/drugs", "GET /api/drugs")
        drugs = data.get("drugs")
        if not isinstance(drugs, list):
            raise VerificationFailure("/api/drugs did not return a drugs list.")
        if data.get("count") != 100 or len(drugs) != 100:
            raise VerificationFailure(
                f"Expected 100 drugs, got count={data.get('count')} len={len(drugs)}."
            )
        for required_nsc in (740, 750, 761431, 761432, 92859, 141540):
            if required_nsc not in drugs:
                raise VerificationFailure(f"Required demo drug NSC {required_nsc} missing.")
        return "100 valid NSC IDs"

    def check_cell_lines():
        data = _request_json(client, "get", "/api/cell-lines", "GET /api/cell-lines")
        cell_lines = data.get("cell_lines")
        if not isinstance(cell_lines, list):
            raise VerificationFailure("/api/cell-lines did not return a cell_lines list.")
        if data.get("count") != 60 or len(cell_lines) != 60:
            raise VerificationFailure(
                f"Expected 60 cell lines, got count={data.get('count')} len={len(cell_lines)}."
            )
        for required_cell_line in ("786-0", "SK-MEL-5", "HL-60(TB)"):
            if required_cell_line not in cell_lines:
                raise VerificationFailure(f"Required demo cell line {required_cell_line} missing.")
        return "60 valid cell lines"

    def check_demo_cases():
        data = _request_json(client, "get", "/api/demo-cases", "GET /api/demo-cases")
        demo_cases = data.get("demo_cases")
        if data.get("count") != 3 or not isinstance(demo_cases, list) or len(demo_cases) != 3:
            raise VerificationFailure(f"Expected exactly 3 demo cases, got {data}.")

        strong_synergy = _find_demo_case(demo_cases, "strong_synergy")
        neutral = _find_demo_case(demo_cases, "neutral")
        antagonism = _find_demo_case(demo_cases, "antagonism")

        synergy_score = float(strong_synergy["predicted_comboscore"])
        neutral_score = float(neutral["predicted_comboscore"])
        antagonism_score = float(antagonism["predicted_comboscore"])

        if synergy_score <= 0:
            raise VerificationFailure(f"Strong synergy demo is not positive: {synergy_score}.")
        if abs(neutral_score) >= 20:
            raise VerificationFailure(f"Neutral demo is not within neutral band: {neutral_score}.")
        if antagonism_score >= 0:
            raise VerificationFailure(f"Antagonism demo is not negative: {antagonism_score}.")
        if str(strong_synergy.get("label")).lower() != "synergistic":
            raise VerificationFailure("Strong synergy demo label is not synergistic.")
        if str(neutral.get("label")).lower() != "neutral":
            raise VerificationFailure("Neutral demo label is not neutral.")
        if str(antagonism.get("label")).lower() != "antagonistic":
            raise VerificationFailure("Antagonism demo label is not antagonistic.")

        return (
            f"strong_synergy={synergy_score:.3f}, "
            f"neutral={neutral_score:.3f}, antagonism={antagonism_score:.3f}"
        )

    def check_predict_neutral():
        data = _request_json(
            client,
            "post",
            "/api/predict",
            "POST /api/predict neutral",
            json=neutral_payload,
        )
        score = _assert_prediction_case(data, "neutral", lambda value: -20 < value < 20)
        return f"score={score:.3f}, label=neutral"

    def check_predict_synergy():
        data = _request_json(
            client,
            "post",
            "/api/predict",
            "POST /api/predict synergy",
            json=synergy_payload,
        )
        score = _assert_prediction_case(data, "synergistic", lambda value: value > 0)
        return f"score={score:.3f}, label=synergistic"

    def check_predict_antagonism():
        data = _request_json(
            client,
            "post",
            "/api/predict",
            "POST /api/predict antagonism",
            json=antagonism_payload,
        )
        score = _assert_prediction_case(data, "antagonistic", lambda value: value < 0)
        return f"score={score:.3f}, label=antagonistic"

    def check_explain():
        data = _request_json(
            client,
            "post",
            "/api/explain",
            "POST /api/explain",
            json=neutral_payload,
        )
        summary_text = json.dumps(data, ensure_ascii=True).lower()
        required_phrases = [
            "upward toward synergy",
            "downward toward antagonism",
        ]
        for phrase in required_phrases:
            if phrase not in summary_text:
                raise VerificationFailure(f"SHAP response missing wording: {phrase}.")
        if not isinstance(data.get("top_positive_contributors"), list):
            raise VerificationFailure("Missing top_positive_contributors list.")
        if not isinstance(data.get("top_negative_contributors"), list):
            raise VerificationFailure("Missing top_negative_contributors list.")
        return "SHAP response uses corrected direction wording"

    def check_molecule_pair():
        data = _request_json(
            client,
            "post",
            "/api/molecule-pair",
            "POST /api/molecule-pair",
            json={"NSC1": 92859, "NSC2": 141540},
        )
        for key in ("NSC1", "NSC2"):
            molecule = data.get(key)
            if not isinstance(molecule, dict) or molecule.get("status") != "success":
                raise VerificationFailure(f"{key} molecule did not load successfully: {molecule}")
            if not molecule.get("molecule_found") or not molecule.get("svg"):
                raise VerificationFailure(f"{key} molecule response missing SVG structure.")
        return "both molecule SVGs loaded"

    def check_batch_predict():
        uploads_before = _snapshot_directory(config.UPLOADS_DIR)
        outputs_before = _snapshot_directory(config.OUTPUTS_DIR)
        csv_content = (
            "NSC1,NSC2,CELLNAME\n"
            "740,750,786-0\n"
            "740,752,A498\n"
            "750,755,A549/ATCC\n"
        )
        try:
            response = client.post(
                "/api/batch-predict",
                data={
                    "file": (
                        io.BytesIO(csv_content.encode("utf-8")),
                        "verify_batch_input.csv",
                    )
                },
                content_type="multipart/form-data",
            )
            _require_http_ok(response, "POST /api/batch-predict")
            data = _json_response(response, "POST /api/batch-predict")
            _require_status_success(data, "POST /api/batch-predict")

            expectations = {
                "total_rows": 3,
                "successful_rows": 3,
                "failed_rows": 0,
            }
            for key, expected in expectations.items():
                actual = data.get(key)
                if actual != expected:
                    raise VerificationFailure(f"Expected {key}={expected}, got {actual}.")

            preview = data.get("preview")
            if not isinstance(preview, list) or len(preview) != 3:
                raise VerificationFailure("Batch preview should contain the 3 sample rows.")

            return "3 rows processed successfully"
        finally:
            _cleanup_new_files(config.UPLOADS_DIR, uploads_before)
            _cleanup_new_files(config.OUTPUTS_DIR, outputs_before)

    return [
        ("GET /api/health", check_health),
        ("GET /api/drugs", check_drugs),
        ("GET /api/cell-lines", check_cell_lines),
        ("GET /api/demo-cases", check_demo_cases),
        ("POST /api/predict neutral", check_predict_neutral),
        ("POST /api/predict positive synergy", check_predict_synergy),
        ("POST /api/predict negative antagonism", check_predict_antagonism),
        ("POST /api/explain", check_explain),
        ("POST /api/molecule-pair", check_molecule_pair),
        ("POST /api/batch-predict", check_batch_predict),
    ]


def main():
    print("SynergyLens full app verification")
    print("Using Flask test_client; no running server is required.")
    print()

    try:
        from app import create_app
        from backend import config
    except Exception as exc:
        print(f"FAIL import Flask app - {exc}")
        raise SystemExit(1)

    app = create_app()
    client = app.test_client()

    runner = VerificationRunner()
    for name, callback in build_checks(client, config):
        runner.check(name, callback)
    runner.finish()


if __name__ == "__main__":
    main()
