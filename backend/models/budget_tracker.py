# backend/models/budget_tracker.py
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rizer_data.db")

class BudgetTracker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def set_budget(self, year: int, month: int, metric: str, target: float):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO budget_targets (year, month, metric_name, target_value) VALUES (?, ?, ?, ?)",
                (year, month, metric, target)
            )

    def record_actual(self, year: int, month: int, metric: str, actual: float):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO budget_actuals (year, month, metric_name, actual_value) VALUES (?, ?, ?, ?)",
                (year, month, metric, actual)
            )

    def compare(self, year: int, month: int, metric: str) -> dict:
        with self._conn() as conn:
            target_row = conn.execute(
                "SELECT SUM(target_value) as target FROM budget_targets WHERE year=? AND month=? AND metric_name=?",
                (year, month, metric)
            ).fetchone()
            actual_row = conn.execute(
                "SELECT SUM(actual_value) as actual FROM budget_actuals WHERE year=? AND month=? AND metric_name=?",
                (year, month, metric)
            ).fetchone()

        target = target_row["target"] if target_row and target_row["target"] else 0
        actual = actual_row["actual"] if actual_row and actual_row["actual"] else 0
        variance = actual - target
        variance_pct = (variance / target * 100) if target else 0

        rag = "green"
        if variance_pct < -15:
            rag = "red"
        elif variance_pct < -5:
            rag = "yellow"
        elif variance_pct > 5:
            rag = "green"

        return {
            "target": target,
            "actual": actual,
            "variance": variance,
            "variance_pct": round(variance_pct, 2),
            "rag": rag
        }

    def monthly_report(self, year: int) -> dict:
        metrics = ["revenue", "profit", "cost", "sales"]
        report_data = {}
        analysis_text = ""
        
        for m in metrics:
            report_data[m] = []
            for month in range(1, 13):
                comp = self.compare(year, month, m)
                report_data[m].append(comp)
                if abs(comp["variance_pct"]) > 15:
                    dir_str = "below" if comp["variance"] < 0 else "above"
                    analysis_text += f"{m} in month {month} was {abs(comp['variance_pct'])}% {dir_str} target. "
                    
        summary = "No major variances detected."
        if analysis_text:
            try:
                from groq import Groq
                GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
                if GROQ_API_KEY:
                    client = Groq(api_key=GROQ_API_KEY)
                    prompt = f"Summarize these budget variances into a 3-sentence executive summary:\n{analysis_text}"
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150
                    )
                    summary = res.choices[0].message.content.strip()
            except Exception:
                summary = "Variance detected: " + analysis_text[:100] + "..."

        return {
            "year": year,
            "data": report_data,
            "summary": summary
        }
