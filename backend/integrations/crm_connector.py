# backend/integrations/crm_connector.py
# UPGRADE 3 — CRM Connectors: Zoho CRM, HubSpot, Salesforce

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class CRMConnector:
    """Unified CRM connector for Zoho CRM, HubSpot, and Salesforce."""

    def __init__(self):
        self.zoho_crm_token = os.environ.get("ZOHO_CRM_TOKEN", "")
        self.hubspot_api_key = os.environ.get("HUBSPOT_API_KEY", "")
        self.sf_client_id = os.environ.get("SF_CLIENT_ID", "")
        self.sf_client_secret = os.environ.get("SF_CLIENT_SECRET", "")

    def _available_sources(self) -> list:
        sources = []
        if self.zoho_crm_token:
            sources.append("zoho_crm")
        if self.hubspot_api_key:
            sources.append("hubspot")
        if self.sf_client_id and self.sf_client_secret:
            sources.append("salesforce")
        return sources

    # ── Zoho CRM ──────────────────────────────────────────────────────
    def fetch_zoho_crm(self) -> dict:
        """Fetch deals from Zoho CRM API."""
        if not self.zoho_crm_token:
            return {"source": "zoho_crm", "status": "not_configured", "message": "Missing ZOHO_CRM_TOKEN"}

        try:
            headers = {"Authorization": f"Zoho-oauthtoken {self.zoho_crm_token}"}
            deals_resp = requests.get(
                "https://www.zohoapis.in/crm/v3/Deals",
                headers=headers,
                timeout=10,
            )
            if deals_resp.status_code == 200:
                deals = deals_resp.json().get("data", [])
                closed_deals = [d for d in deals if d.get("Stage") == "Closed Won"]
                total_value = sum(d.get("Amount", 0) for d in deals)
                closed_value = sum(d.get("Amount", 0) for d in closed_deals)

                return {
                    "source": "zoho_crm",
                    "pipeline_value": total_value,
                    "deals_closed": len(closed_deals),
                    "conversion_rate": round(len(closed_deals) / max(len(deals), 1) * 100, 1),
                    "avg_deal_size": round(closed_value / max(len(closed_deals), 1), 0),
                    "status": "connected",
                }
            return {"source": "zoho_crm", "status": "auth_failed", "message": f"HTTP {deals_resp.status_code}"}
        except Exception as e:
            return {"source": "zoho_crm", "status": "error", "message": str(e)}

    # ── HubSpot ───────────────────────────────────────────────────────
    def fetch_hubspot(self) -> dict:
        """Fetch contacts and deals from HubSpot API."""
        if not self.hubspot_api_key:
            return {"source": "hubspot", "status": "not_configured", "message": "Missing HUBSPOT_API_KEY"}

        try:
            headers = {"Authorization": f"Bearer {self.hubspot_api_key}"}

            deals_resp = requests.get(
                "https://api.hubapi.com/crm/v3/objects/deals",
                headers=headers,
                timeout=10,
            )
            contacts_resp = requests.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                timeout=10,
            )

            deals = deals_resp.json().get("results", []) if deals_resp.status_code == 200 else []
            contacts = contacts_resp.json().get("results", []) if contacts_resp.status_code == 200 else []

            pipeline_value = sum(float(d.get("properties", {}).get("amount", 0) or 0) for d in deals)
            closed_deals = [d for d in deals if d.get("properties", {}).get("dealstage") == "closedwon"]

            return {
                "source": "hubspot",
                "pipeline_value": pipeline_value,
                "deals_closed": len(closed_deals),
                "total_contacts": len(contacts),
                "conversion_rate": round(len(closed_deals) / max(len(deals), 1) * 100, 1),
                "avg_deal_size": round(pipeline_value / max(len(deals), 1), 0),
                "status": "connected",
            }
        except Exception as e:
            return {"source": "hubspot", "status": "error", "message": str(e)}

    # ── Salesforce ────────────────────────────────────────────────────
    def fetch_salesforce(self) -> dict:
        """Fetch opportunities from Salesforce API."""
        if not self.sf_client_id or not self.sf_client_secret:
            return {"source": "salesforce", "status": "not_configured", "message": "Missing SF_CLIENT_ID/SECRET"}

        try:
            token_resp = requests.post(
                "https://login.salesforce.com/services/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.sf_client_id,
                    "client_secret": self.sf_client_secret,
                },
                timeout=10,
            )

            if token_resp.status_code == 200:
                token_data = token_resp.json()
                access_token = token_data["access_token"]
                instance_url = token_data["instance_url"]

                headers = {"Authorization": f"Bearer {access_token}"}
                query = "SELECT Id, Amount, StageName FROM Opportunity WHERE IsClosed=true LIMIT 100"
                resp = requests.get(
                    f"{instance_url}/services/data/v58.0/query?q={query}",
                    headers=headers,
                    timeout=10,
                )

                if resp.status_code == 200:
                    records = resp.json().get("records", [])
                    won = [r for r in records if r.get("StageName") == "Closed Won"]
                    return {
                        "source": "salesforce",
                        "pipeline_value": sum(r.get("Amount", 0) or 0 for r in records),
                        "deals_closed": len(won),
                        "conversion_rate": round(len(won) / max(len(records), 1) * 100, 1),
                        "avg_deal_size": round(sum(r.get("Amount", 0) or 0 for r in won) / max(len(won), 1), 0),
                        "status": "connected",
                    }

            return {"source": "salesforce", "status": "auth_failed", "message": "OAuth failed"}
        except Exception as e:
            return {"source": "salesforce", "status": "error", "message": str(e)}

    # ── Unified pipeline fetch ────────────────────────────────────────
    def fetch_pipeline(self) -> list:
        """Fetch from all available CRM sources."""
        results = []
        if self.zoho_crm_token:
            results.append(self.fetch_zoho_crm())
        if self.hubspot_api_key:
            results.append(self.fetch_hubspot())
        if self.sf_client_id:
            results.append(self.fetch_salesforce())
        return results
