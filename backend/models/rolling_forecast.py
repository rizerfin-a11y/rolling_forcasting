# backend/models/rolling_forecast.py
# UPGRADE 1 — ML Ensemble Forecasting Engine
import sqlite3
import os
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rizer_data.db")


class EnsembleForecaster:
    """ML Ensemble Forecaster: Prophet + XGBoost + Linear Regression."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Data Loading ──────────────────────────────────────────────────
    def _load_data(self, metric: str) -> pd.DataFrame:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT date, SUM(metric_value) as value "
                "FROM financial_data WHERE metric_name=? "
                "GROUP BY date ORDER BY date ASC",
                (metric,),
            ).fetchall()

        if len(rows) < 3:
            # Generate mock data for demo
            values = np.linspace(100, 150, 24) + np.random.normal(0, 5, 24)
            # Add festival quarter boost (Oct-Dec)
            for i in range(24):
                month_idx = (datetime.today().month - 24 + i) % 12
                if month_idx in [9, 10, 11]:  # Oct, Nov, Dec
                    values[i] *= 1.20
            dates = [
                (datetime.today() - relativedelta(months=24 - i)).replace(day=1)
                for i in range(24)
            ]
            return pd.DataFrame({"date": dates, "value": values})

        df = pd.DataFrame([dict(r) for r in rows])
        df["date"] = pd.to_datetime(df["date"])
        return df

    # ── Model 1: Prophet ──────────────────────────────────────────────
    def _run_prophet(self, df: pd.DataFrame, periods: int) -> dict:
        try:
            from prophet import Prophet

            prophet_df = df.rename(columns={"date": "ds", "value": "y"})
            model = Prophet(
                seasonality_mode="multiplicative",
                yearly_seasonality=True,
                weekly_seasonality=False,
            )
            model.add_seasonality(name="quarterly", period=91.25, fourier_order=5)
            model.fit(prophet_df)
            future = model.make_future_dataframe(periods=periods, freq="MS")
            forecast = model.predict(future)

            preds = forecast.tail(periods)
            return {
                "values": preds["yhat"].tolist(),
                "ci_lower": preds["yhat_lower"].tolist(),
                "ci_upper": preds["yhat_upper"].tolist(),
                "available": True,
            }
        except Exception as e:
            return {"values": [], "available": False, "error": str(e)}

    # ── Model 2: XGBoost ──────────────────────────────────────────────
    def _run_xgboost(self, df: pd.DataFrame, periods: int) -> dict:
        try:
            from xgboost import XGBRegressor

            feature_df = df.copy()
            feature_df["month"] = feature_df["date"].dt.month
            feature_df["quarter"] = feature_df["date"].dt.quarter
            feature_df["year"] = feature_df["date"].dt.year
            feature_df["is_festival_quarter"] = feature_df["month"].isin(
                [10, 11, 12]
            ).astype(int)

            # Lag features
            for lag in [1, 2, 3, 6, 12]:
                feature_df[f"lag_{lag}"] = feature_df["value"].shift(lag)
            feature_df = feature_df.dropna()

            feature_cols = [
                "month", "quarter", "year", "is_festival_quarter",
                "lag_1", "lag_2", "lag_3", "lag_6", "lag_12",
            ]
            X = feature_df[feature_cols].values
            y = feature_df["value"].values

            model = XGBRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=4, verbosity=0
            )
            model.fit(X, y)

            # Predict forward
            preds = []
            last_values = list(df["value"].values)
            last_date = df["date"].iloc[-1]

            for i in range(periods):
                next_date = last_date + relativedelta(months=i + 1)
                m = next_date.month
                q = (m - 1) // 3 + 1
                yr = next_date.year
                is_fest = 1 if m in [10, 11, 12] else 0
                lag1 = last_values[-1] if len(last_values) >= 1 else 0
                lag2 = last_values[-2] if len(last_values) >= 2 else 0
                lag3 = last_values[-3] if len(last_values) >= 3 else 0
                lag6 = last_values[-6] if len(last_values) >= 6 else 0
                lag12 = last_values[-12] if len(last_values) >= 12 else 0

                features = np.array(
                    [[m, q, yr, is_fest, lag1, lag2, lag3, lag6, lag12]]
                )
                pred = float(model.predict(features)[0])
                preds.append(pred)
                last_values.append(pred)

            return {"values": preds, "available": True}
        except Exception as e:
            return {"values": [], "available": False, "error": str(e)}

    # ── Model 3: Linear Regression ────────────────────────────────────
    def _run_linear(self, df: pd.DataFrame, periods: int) -> dict:
        X = np.arange(len(df)).reshape(-1, 1)
        y = df["value"].values
        model = LinearRegression().fit(X, y)
        future_X = np.arange(len(df), len(df) + periods).reshape(-1, 1)
        preds = model.predict(future_X)
        residuals = y - model.predict(X)
        std_err = float(np.std(residuals))
        r2 = float(r2_score(y, model.predict(X)))
        return {
            "values": preds.tolist(),
            "std_err": std_err,
            "r2": r2,
            "available": True,
        }

    # ── Festival Impact Analysis ──────────────────────────────────────
    def _analyze_festival_impact(self, df: pd.DataFrame) -> str:
        df_copy = df.copy()
        df_copy["month"] = df_copy["date"].dt.month
        df_copy["quarter"] = df_copy["date"].dt.quarter
        overall_avg = df_copy["value"].mean()

        q4_data = df_copy[df_copy["month"].isin([10, 11, 12])]
        if len(q4_data) > 0:
            q4_avg = q4_data["value"].mean()
            pct_above = round(((q4_avg - overall_avg) / overall_avg) * 100, 1)
            if pct_above > 5:
                return f"Q3 (Oct-Dec) shows {pct_above}% above average — Diwali effect detected"
            elif pct_above < -5:
                return f"Q3 (Oct-Dec) shows {abs(pct_above)}% below average — seasonal dip"
        return "No significant festival impact detected in available data"

    # ── Main Forecast Engine ──────────────────────────────────────────
    def run(self, metric: str, periods: int = 6) -> dict:
        df = self._load_data(metric)
        n = len(df)

        # Run all models
        linear_res = self._run_linear(df, periods)
        prophet_res = self._run_prophet(df, periods)
        xgb_res = self._run_xgboost(df, periods)

        # Auto-select ensemble weights based on data size
        if n < 12:
            weights = {"prophet": 0, "xgboost": 0, "linear": 1.0}
            model_label = "Linear only (limited data)"
        elif n < 24:
            if prophet_res["available"]:
                weights = {"prophet": 0.6, "xgboost": 0, "linear": 0.4}
                model_label = "Prophet 60% + Linear 40%"
            else:
                weights = {"prophet": 0, "xgboost": 0, "linear": 1.0}
                model_label = "Linear only (Prophet unavailable)"
        else:
            w_prophet = 0.50 if prophet_res["available"] else 0
            w_xgb = 0.35 if xgb_res["available"] else 0
            w_linear = 1.0 - w_prophet - w_xgb
            weights = {"prophet": w_prophet, "xgboost": w_xgb, "linear": w_linear}
            parts = []
            if w_prophet > 0:
                parts.append(f"Prophet {int(w_prophet*100)}%")
            if w_xgb > 0:
                parts.append(f"XGBoost {int(w_xgb*100)}%")
            parts.append(f"Linear {int(w_linear*100)}%")
            model_label = " + ".join(parts) + " ensemble"

        # Blend predictions
        predictions = []
        last_date = df["date"].iloc[-1]
        now_str = datetime.now().isoformat()
        std_err = linear_res.get("std_err", 5.0)

        with self._conn() as conn:
            for i in range(periods):
                next_date = last_date + relativedelta(months=i + 1)
                period_str = next_date.strftime("%Y-%m")

                val = 0.0
                if weights["linear"] > 0 and len(linear_res["values"]) > i:
                    val += weights["linear"] * linear_res["values"][i]
                if weights["prophet"] > 0 and len(prophet_res.get("values", [])) > i:
                    val += weights["prophet"] * prophet_res["values"][i]
                if weights["xgboost"] > 0 and len(xgb_res.get("values", [])) > i:
                    val += weights["xgboost"] * xgb_res["values"][i]

                ci_l = val - 1.96 * std_err
                ci_u = val + 1.96 * std_err
                ci_95_l = val - 2.576 * std_err
                ci_95_u = val + 2.576 * std_err

                # Use Prophet's CI if available
                if prophet_res["available"] and len(prophet_res.get("ci_lower", [])) > i:
                    ci_l = prophet_res["ci_lower"][i]
                    ci_u = prophet_res["ci_upper"][i]

                predictions.append({
                    "period": period_str,
                    "value": round(val, 2),
                    "ci_lower": round(ci_l, 2),
                    "ci_upper": round(ci_u, 2),
                    "ci_95_lower": round(ci_95_l, 2),
                    "ci_95_upper": round(ci_95_u, 2),
                })

                conn.execute(
                    "INSERT INTO forecast_history (run_at, metric_name, period, predicted_value) VALUES (?, ?, ?, ?)",
                    (now_str, metric, period_str, round(val, 2)),
                )

        # Growth rate
        last_val = df["value"].iloc[-1]
        growth_rate = (
            ((predictions[-1]["value"] - last_val) / last_val) * 100
            if last_val != 0
            else 0
        )

        # Accuracy metrics
        acc = self.accuracy()
        rmse_val = acc.get("rmse", 0)
        r2_val = linear_res.get("r2", 0)

        # Festival impact
        festival_impact = self._analyze_festival_impact(df)

        return {
            "predictions": predictions,
            "model_used": model_label,
            "data_points_used": n,
            "accuracy": {
                "mape": acc.get("mape", 0),
                "rmse": round(rmse_val, 2),
                "r2": round(r2_val, 2),
            },
            "growth_rate": round(growth_rate, 2),
            "festival_impact": festival_impact,
        }

    def accuracy(self) -> dict:
        """Compare predicted vs actuals using MAPE, RMSE."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT fh.period, fh.predicted_value, SUM(fd.metric_value) as actual_value "
                "FROM forecast_history fh "
                "JOIN financial_data fd ON strftime('%Y-%m', fd.date) = fh.period AND fh.metric_name = fd.metric_name "
                "WHERE fh.predicted_value IS NOT NULL "
                "GROUP BY fh.period, fh.predicted_value"
            ).fetchall()

        if not rows:
            return {"mape": 0, "rmse": 0, "predicted": [], "actual": []}

        preds, actuals = [], []
        for r in rows:
            preds.append(r["predicted_value"])
            actuals.append(r["actual_value"])

        mape = (
            mean_absolute_percentage_error(actuals, preds) * 100
            if actuals
            else 0
        )
        rmse = float(np.sqrt(mean_squared_error(actuals, preds))) if actuals else 0

        return {
            "mape": round(mape, 2),
            "rmse": round(rmse, 2),
            "predicted": [{"value": p} for p in preds],
            "actual": [{"value": a} for a in actuals],
        }


# Keep backward-compatible alias
RollingForecast = EnsembleForecaster
