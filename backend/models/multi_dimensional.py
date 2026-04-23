# backend/models/multi_dimensional.py
import sqlite3
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rizer_data.db")

class MultiDimensionalModel:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def build(self, dimensions: list, metric: str) -> dict:
        """Create pandas pivot table out of dimensions (e.g., ['department', 'region'])."""
        # Validate dimensions to prevent injection
        allowed_dims = {"department", "product", "region"}
        dims = [d for d in dimensions if d in allowed_dims]
        if not dims:
            return {}

        dim_str = ", ".join(dims)
        with self._conn() as conn:
            query = f"SELECT {dim_str}, SUM(metric_value) as value FROM financial_data WHERE metric_name=? GROUP BY {dim_str}"
            df = pd.read_sql_query(query, conn, params=(metric,))
        
        if df.empty:
            return {}

        # Pivot recursively equivalent
        if len(dims) == 1:
            return df.set_index(dims[0])['value'].to_dict()
        elif len(dims) == 2:
            pivot = df.pivot_table(index=dims[0], columns=dims[1], values="value", aggfunc="sum").fillna(0)
            return pivot.to_dict(orient="index")
        else:
            # For 3+ dims, return flattened dict for simplicity in JSON
            return df.to_dict(orient="records")

    def drilldown(self, dimension: str, value: str, metric: str) -> list:
        """Filters to one dimension value and returns time series."""
        allowed_dims = {"department", "product", "region"}
        if dimension not in allowed_dims:
            return []

        with self._conn() as conn:
            query = f"SELECT date, SUM(metric_value) as value FROM financial_data WHERE metric_name=? AND {dimension}=? GROUP BY date ORDER BY date ASC"
            rows = conn.execute(query, (metric, value)).fetchall()

        return [{"date": r["date"], "value": r["value"]} for r in rows]

    def summary(self, metric: str = "revenue") -> dict:
        """Top 3 insights using Groq."""
        # Get raw aggregation logic
        try:
            with self._conn() as conn:
                df = pd.read_sql_query("SELECT department, product, region, SUM(metric_value) as value FROM financial_data WHERE metric_name=? GROUP BY department, product, region", conn, params=(metric,))
            
            top_performers = df.sort_values(by="value", ascending=False).head(5).to_string()
            
            from groq import Groq
            GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
            insights = "No insights generated (Configuration needed)."
            if GROQ_API_KEY:
                client = Groq(api_key=GROQ_API_KEY)
                prompt = f"Analyze this top performer slice data for metric '{metric}':\n{top_performers}\nProvide exactly 3 bullet points with the most critical business insights."
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200
                )
                insights = res.choices[0].message.content.strip()
            return {"insights": insights}
        except Exception as e:
            return {"insights": f"Error generating summary: {str(e)}"}
