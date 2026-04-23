"""
backend/routes/data_routes.py
Flask Blueprint for data upload, live market data, and source listing.
"""

import os
import json
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from data_connector import DataConnector, UPLOADS_DIR

data_bp = Blueprint("data_bp", __name__)
connector = DataConnector()

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def _allowed(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ── POST /api/data/upload ─────────────────────────────────────────────────────
@data_bp.route("/api/data/upload", methods=["POST"])
def upload_file():
    """
    Accepts multipart/form-data with file field named 'file'.
    Saves to backend/uploads/, ingests into SQLite, returns summary.
    """
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file field in request"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"status": "error", "message": "Empty filename"}), 400

    if not _allowed(f.filename):
        return jsonify({
            "status": "error",
            "message": f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    filename = secure_filename(f.filename)
    dest = os.path.join(UPLOADS_DIR, filename)
    f.save(dest)

    try:
        result = connector.ingest_file(dest, filename)
        connector.log_alert(
            alert_type="upload",
            message=f"Ingested '{filename}': {result['rows']} rows, columns: {result['columns']}",
            severity="info"
        )
        return jsonify({
            "status": "success",
            "filename": filename,
            "upload_id": result["upload_id"],
            "rows_ingested": result["rows"],
            "columns_detected": result["columns"]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── GET /api/data/live?ticker=TATAMOTORS.NS ───────────────────────────────────
@data_bp.route("/api/data/live", methods=["GET"])
def live_data():
    """
    Returns real-time market data from yfinance for the given ticker.
    """
    ticker = request.args.get("ticker", "TATAMOTORS.NS")
    try:
        data = connector.get_live_data(ticker)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── GET /api/data/sources ─────────────────────────────────────────────────────
@data_bp.route("/api/data/sources", methods=["GET"])
def data_sources():
    """
    Returns all uploaded file records from the uploads table.
    """
    try:
        uploads = connector.get_all_uploads()
        # Deserialise columns JSON string
        for u in uploads:
            if isinstance(u.get("columns"), str):
                try:
                    u["columns"] = json.loads(u["columns"])
                except Exception:
                    pass
        return jsonify({"status": "success", "uploads": uploads, "total": len(uploads)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── GET /api/data/series?metric=revenue ───────────────────────────────────────
@data_bp.route("/api/data/series", methods=["GET"])
def financial_series():
    """
    Returns time-series for a given metric from SQLite.
    Optional filters: department, product, region
    """
    metric = request.args.get("metric", "revenue")
    department = request.args.get("department")
    product = request.args.get("product")
    region = request.args.get("region")

    try:
        series = connector.get_financial_series(metric, department, product, region)
        return jsonify({"status": "success", "metric": metric, "series": series})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
