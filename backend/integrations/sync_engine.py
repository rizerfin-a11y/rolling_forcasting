# backend/integrations/sync_engine.py
# UPGRADE 3 — Background Sync Engine with APScheduler

import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rizer_data.db")


class SyncEngine:
    """
    Background sync engine that:
    - Calls all available ERP/CRM connectors
    - Inserts new data into SQLite financial_data
    - Triggers RollingForecast.run() after each sync
    - Stores sync logs
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_sync_table()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sync_table(self):
        ddl = """
        CREATE TABLE IF NOT EXISTS sync_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            synced_at     TEXT NOT NULL,
            source        TEXT NOT NULL,
            records_added INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'pending',
            error_message TEXT
        );
        """
        with self._conn() as conn:
            conn.executescript(ddl)

    def sync_all(self) -> dict:
        """Manually trigger a full sync of all configured sources."""
        from integrations.erp_connector import ERPConnector
        from integrations.crm_connector import CRMConnector

        erp = ERPConnector()
        crm = CRMConnector()
        now = datetime.now().isoformat()
        results = []

        # ERP sync
        erp_data = erp.fetch_latest(days=30)
        for entry in erp_data:
            records = 0
            status = entry.get("status", "error")
            error_msg = entry.get("message", None)

            if status == "connected" and entry.get("revenue", 0) > 0:
                # Insert into financial_data
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO financial_data (date, metric_name, metric_value) VALUES (?, ?, ?)",
                        (entry.get("period", now[:7]), "revenue", entry.get("revenue", 0)),
                    )
                    if entry.get("expenses", 0) > 0:
                        conn.execute(
                            "INSERT INTO financial_data (date, metric_name, metric_value) VALUES (?, ?, ?)",
                            (entry.get("period", now[:7]), "cost", entry.get("expenses", 0)),
                        )
                    records = 1 + (1 if entry.get("expenses", 0) > 0 else 0)

            # Log sync
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO sync_log (synced_at, source, records_added, status, error_message) VALUES (?, ?, ?, ?, ?)",
                    (now, entry.get("source", "unknown"), records, status, error_msg),
                )

            results.append({
                "source": entry.get("source"),
                "status": status,
                "records_added": records,
                "error": error_msg,
            })

        # CRM sync
        crm_data = crm.fetch_pipeline()
        for entry in crm_data:
            status = entry.get("status", "error")
            error_msg = entry.get("message", None)

            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO sync_log (synced_at, source, records_added, status, error_message) VALUES (?, ?, ?, ?, ?)",
                    (now, entry.get("source", "unknown"), 0, status, error_msg),
                )

            results.append({
                "source": entry.get("source"),
                "status": status,
                "records_added": 0,
                "error": error_msg,
            })

        # Trigger forecast refresh after sync
        try:
            import sys
            sys.path.insert(0, os.path.join(BASE_DIR, "models"))
            from rolling_forecast import EnsembleForecaster
            forecaster = EnsembleForecaster(self.db_path)
            forecaster.run("revenue", 6)
        except Exception:
            pass

        return {"synced_at": now, "results": results}

    def get_status(self) -> dict:
        """Return which integrations are connected and last sync time."""
        from integrations.erp_connector import ERPConnector
        from integrations.crm_connector import CRMConnector

        erp = ERPConnector()
        crm = CRMConnector()

        sources = {
            "tally": {"configured": bool(erp.tally_host), "type": "ERP"},
            "zoho_books": {"configured": bool(erp.zoho_client_id and erp.zoho_client_secret), "type": "ERP"},
            "quickbooks": {"configured": bool(erp.qb_client_id and erp.qb_client_secret), "type": "ERP"},
            "zoho_crm": {"configured": bool(crm.zoho_crm_token), "type": "CRM"},
            "hubspot": {"configured": bool(crm.hubspot_api_key), "type": "CRM"},
            "salesforce": {"configured": bool(crm.sf_client_id and crm.sf_client_secret), "type": "CRM"},
        }

        # Get last sync time for each source
        with self._conn() as conn:
            for source_name in sources:
                row = conn.execute(
                    "SELECT synced_at, status, records_added FROM sync_log WHERE source=? ORDER BY synced_at DESC LIMIT 1",
                    (source_name,),
                ).fetchone()
                if row:
                    sources[source_name]["last_sync"] = row["synced_at"]
                    sources[source_name]["last_status"] = row["status"]
                    sources[source_name]["last_records"] = row["records_added"]
                else:
                    sources[source_name]["last_sync"] = None
                    sources[source_name]["last_status"] = "never"
                    sources[source_name]["last_records"] = 0

        return sources

    def get_log(self, limit: int = 50) -> list:
        """Return last N sync log entries."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, synced_at, source, records_added, status, error_message FROM sync_log ORDER BY synced_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
