import urllib.request
import json
import sys

results = []

def fetch(label, url, data=None):
    results.append(f"\n{'='*60}")
    results.append(f"> {label}")
    results.append(f"{'='*60}")
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
        res = urllib.request.urlopen(req, timeout=30)
        j = json.loads(res.read().decode("utf-8"))
        results.append(json.dumps(j, indent=2))
    except Exception as e:
        results.append(f"ERROR: {e}")

fetch("curl http://localhost:5000/api/health", "http://localhost:5000/api/health")

fetch("curl http://localhost:5000/api/integrations/status", "http://localhost:5000/api/integrations/status")

fetch("curl http://localhost:5000/api/forecast/rolling?metric=revenue&periods=6", "http://localhost:5000/api/forecast/rolling?metric=revenue&periods=6")

fetch("curl -X POST http://localhost:5000/api/drivers/propagate",
      "http://localhost:5000/api/drivers/propagate",
      json.dumps({"driver":"sales_volume","new_value":180000,"current_drivers":{"sales_volume":150000,"average_price":850000,"cost_of_goods_percent":65,"operating_expenses":5000,"tax_rate":25,"total_market_size":4000000}}).encode("utf-8"))

with open("test_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("Done! Results written to test_output.txt")
