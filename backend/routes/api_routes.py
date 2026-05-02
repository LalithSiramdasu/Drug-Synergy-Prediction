from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from backend import config
from backend.services.batch_service import BatchPredictionError, run_batch_prediction
from backend.services.data_loader import build_health_report, get_available_cell_lines, get_available_drugs
from backend.services.demo_service import DemoCaseError, get_demo_cases
from backend.services.model_loader import ModelLoaderError, get_model_info
from backend.services.molecule_service import MoleculeError, get_molecule, get_molecule_pair, get_two_molecules
from backend.services.prediction_service import PredictionError, predict_single
from backend.services.shap_service import ShapExplanationError, explain_prediction
from backend.services.system_summary_service import build_system_summary


api_bp = Blueprint("api", __name__)


@api_bp.get("/")
def index():
    return render_template("index.html")


@api_bp.get("/api/health")
def health():
    report = build_health_report()
    status_code = 200 if report["status"] == "success" else 503
    return jsonify(report), status_code


@api_bp.get("/api/system-summary")
def system_summary():
    summary = build_system_summary()
    status_code = 200 if summary["status"] == "success" else 503
    return jsonify(summary), status_code


@api_bp.get("/api/cell-lines")
def cell_lines():
    try:
        values = get_available_cell_lines()
        return jsonify({"status": "success", "count": len(values), "cell_lines": values})
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@api_bp.get("/api/drugs")
def drugs():
    try:
        values = get_available_drugs()
        query = request.args.get("q", "").strip()
        if query:
            normalized_query = query.lower().replace("nsc", "").strip()
            values = [
                value
                for value in values
                if normalized_query in str(value).lower()
            ][:20]
        return jsonify({"status": "success", "count": len(values), "drugs": values})
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@api_bp.get("/api/model-info/<path:cell_line>")
def model_info(cell_line):
    try:
        info = get_model_info(cell_line)
        return jsonify(
            {
                "status": "success",
                "cell_line": info["cell_line"],
                "safe_cell_line": info["safe_cell_line"],
                "model_name": info["model_name"],
                "model_path": info["model_path"],
                "model_file_exists": info["model_file_exists"],
            }
        )
    except ModelLoaderError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 404


@api_bp.post("/api/predict")
def predict():
    payload = request.get_json(silent=True)
    try:
        result = predict_single(payload)
        result["molecule_1_url"] = f"/api/molecule/{result['input']['NSC1']}"
        result["molecule_2_url"] = f"/api/molecule/{result['input']['NSC2']}"
        return jsonify(result)
    except PredictionError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@api_bp.post("/api/batch-predict")
def batch_predict():
    uploaded_file = request.files.get("file")
    if uploaded_file is None and request.files:
        uploaded_file = next(iter(request.files.values()))

    try:
        result = run_batch_prediction(uploaded_file)
        return jsonify(result)
    except BatchPredictionError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@api_bp.get("/api/molecule/<nsc>")
def molecule(nsc):
    try:
        result = get_molecule(nsc)
        status_code = 200 if result["status"] == "success" else 404
        return jsonify(result), status_code
    except MoleculeError as exc:
        return jsonify(
            {
                "status": "error",
                "requested_nsc": nsc,
                "molecule_found": False,
                "found": False,
                "error": str(exc),
            }
        ), 400


@api_bp.post("/api/molecules")
def molecules():
    payload = request.get_json(silent=True)
    try:
        result = get_two_molecules(payload)
        status_code = 200 if result["status"] == "success" else 404
        return jsonify(result), status_code
    except MoleculeError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@api_bp.post("/api/molecule-pair")
def molecule_pair():
    payload = request.get_json(silent=True)
    try:
        result = get_molecule_pair(payload)
        status_code = 200 if result["status"] == "success" else 404
        return jsonify(result), status_code
    except MoleculeError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@api_bp.get("/api/demo-cases")
def demo_cases():
    try:
        return jsonify(get_demo_cases())
    except DemoCaseError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@api_bp.post("/api/explain")
def explain():
    payload = request.get_json(silent=True)
    try:
        return jsonify(explain_prediction(payload))
    except PredictionError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400
    except ShapExplanationError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@api_bp.get("/api/download/<path:filename>")
def download_output(filename):
    requested_name = Path(filename).name
    if requested_name != filename or not requested_name:
        return jsonify({"status": "error", "error": "Invalid output filename."}), 400

    output_path = config.OUTPUTS_DIR / requested_name
    try:
        resolved_output_dir = config.OUTPUTS_DIR.resolve()
        resolved_output_path = output_path.resolve()
        if resolved_output_dir not in resolved_output_path.parents:
            return jsonify({"status": "error", "error": "Invalid output filename."}), 400
    except OSError:
        return jsonify({"status": "error", "error": "Invalid output filename."}), 400

    if not output_path.is_file():
        return jsonify({"status": "error", "error": "Output file not found."}), 404

    return send_from_directory(config.OUTPUTS_DIR, requested_name, as_attachment=True)
