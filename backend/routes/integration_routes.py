# backend/routes/integration_routes.py
# UPGRADE 3 — Integration endpoints

import os
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv, set_key

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.sync_engine import SyncEngine

integration_bp = Blueprint("integration_bp", __name__)
sync_engine = SyncEngine()

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


@integration_bp.route("/api/integrations/status", methods=["GET"])
def integration_status():
    """Return all connected sources and last sync time."""
    try:
        status = sync_engine.get_status()
        return jsonify({"status": "success", "integrations": status})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@integration_bp.route("/api/integrations/sync", methods=["POST"])
def integration_sync():
    """Manually trigger a full sync of all sources."""
    try:
        result = sync_engine.sync_all()
        return jsonify({"status": "success", "sync": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@integration_bp.route("/api/integrations/connect", methods=["POST"])
def integration_connect():
    """
    Store credentials in .env, test connection, return success/failure.
    Body: {"source": "zoho_books", "client_id": "...", "client_secret": "..."}
    """
    data = request.get_json() or {}
    source = data.get("source", "")

    env_mapping = {
        "zoho_books": {"client_id": "ZOHO_CLIENT_ID", "client_secret": "ZOHO_CLIENT_SECRET"},
        "zoho_crm": {"token": "ZOHO_CRM_TOKEN"},
        "hubspot": {"api_key": "HUBSPOT_API_KEY"},
        "quickbooks": {"client_id": "QB_CLIENT_ID", "client_secret": "QB_CLIENT_SECRET"},
        "salesforce": {"client_id": "SF_CLIENT_ID", "client_secret": "SF_CLIENT_SECRET"},
        "tally": {"host": "TALLY_HOST", "port": "TALLY_PORT"},
    }

    if source not in env_mapping:
        return jsonify({"status": "error", "message": f"Unknown source: {source}"}), 400

    try:
        # Store credentials in .env
        mapping = env_mapping[source]
        for field, env_key in mapping.items():
            value = data.get(field, "")
            if value:
                os.environ[env_key] = value
                try:
                    set_key(ENV_PATH, env_key, value)
                except Exception:
                    pass  # .env write is best-effort

        # Test connection
        test_result = _test_connection(source)

        return jsonify({
            "status": "success",
            "source": source,
            "connection_test": test_result,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def _test_connection(source: str) -> dict:
    """Quick test of a specific integration."""
    try:
        if source in ["tally", "zoho_books", "quickbooks"]:
            from integrations.erp_connector import ERPConnector
            erp = ERPConnector()
            if source == "tally":
                return erp.fetch_tally(days=1)
            elif source == "zoho_books":
                return erp.fetch_zoho_books(days=1)
            elif source == "quickbooks":
                return erp.fetch_quickbooks(days=1)
        elif source in ["zoho_crm", "hubspot", "salesforce"]:
            from integrations.crm_connector import CRMConnector
            crm = CRMConnector()
            if source == "zoho_crm":
                return crm.fetch_zoho_crm()
            elif source == "hubspot":
                return crm.fetch_hubspot()
            elif source == "salesforce":
                return crm.fetch_salesforce()
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {"status": "unknown"}


@integration_bp.route("/api/integrations/log", methods=["GET"])
def integration_log():
    """Return last 50 sync log entries."""
    try:
        log = sync_engine.get_log(50)
        return jsonify({"status": "success", "log": log})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
