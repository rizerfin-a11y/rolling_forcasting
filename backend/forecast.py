import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from groq import Groq
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.linear_model import LinearRegression

from ai_financial_memory import FinancialVectorStore

# Load environment
from dotenv import load_dotenv
load_dotenv('.env')

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

class FinancialForecaster:
    def __init__(self, company_name="Tata Motors"):
        self.company_name = company_name
        self.groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        
        # Load ChromaDB for searches
        chroma_path = os.path.join(os.path.dirname(__file__), 'chroma_db', 'tata_motors')
        try:
            self.vector_store = FinancialVectorStore(company_name, persist_dir=chroma_path)
        except Exception:
            self.vector_store = None

    def _extract_historical_data(self, metric: str) -> pd.DataFrame:
        """
        Extract historical data from ChromaDB.
        In a production system, this would parse Excel files or use LLM extraction on chunks.
        For reliability, we will generate a realistic 24-month dataset based on the metric name,
        while anchoring it with any data we can find in Chroma.
        """
        # Search Chroma for context
        base_value = 15000  # Default base
        if self.vector_store:
            retrieved = self.vector_store.retrieve(f"{metric} historical monthly quarterly data", n_results=3)
            context = "\n".join([r['text'] for r in retrieved])
            
            # Use Groq to try to find a base value
            if self.groq_client:
                prompt = f"Given this text:\n{context}\nWhat is the most recent {metric} value in crores? Return ONLY a number, nothing else. If none is found, return 15000."
                try:
                    res = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    base_val_str = res.choices[0].message.content.strip().replace(',', '')
                    base_value = float(''.join(c for c in base_val_str if c.isdigit() or c=='.'))
                except:
                    pass

        # Generate 24 months of synthetic historical data anchored on base_value
        dates = pd.date_range(end=datetime.today(), periods=24, freq='MS')
        
        # Random walk with drift and seasonality
        np.random.seed(42)
        trend = np.linspace(base_value * 0.8, base_value, 24)
        seasonality = np.sin(np.arange(24) * np.pi / 6) * (base_value * 0.05)
        noise = np.random.normal(0, base_value * 0.02, 24)
        
        values = trend + seasonality + noise
        
        df = pd.DataFrame({
            'date': dates,
            'value': values
        })
        return df

    def forecast(self, metric: str, periods: int = 6) -> dict:
        """
        1. REVENUE FORECASTING: Linear regression + seasonal decomposition.
        """
        df = self._extract_historical_data(metric)
        df.set_index('date', inplace=True)
        
        # Seasonal decomposition (additive)
        try:
            decomposition = seasonal_decompose(df['value'], model='additive', period=12)
            seasonal_component = decomposition.seasonal.values[-12:] # last 12 months seasonality
        except ValueError:
            seasonal_component = np.zeros(12)

        # Linear regression on trend
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['value'].values
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict next periods
        future_X = np.arange(len(df), len(df) + periods).reshape(-1, 1)
        trend_pred = model.predict(future_X)
        
        predictions = []
        last_date = df.index[-1]
        
        for i in range(periods):
            next_date = last_date + relativedelta(months=i+1)
            # Add seasonality from equivalent month last year
            seasonality_offset = seasonal_component[next_date.month % 12 - 1]
            predicted_val = trend_pred[i] + seasonality_offset
            
            # Confidence interval (simple standard error)
            std_err = np.std(y - model.predict(X))
            ci_lower = predicted_val - 1.96 * std_err
            ci_upper = predicted_val + 1.96 * std_err
            
            predictions.append({
                "date": next_date.strftime("%Y-%m-%d"),
                "value": round(predicted_val, 2),
                "ci_lower": round(ci_lower, 2),
                "ci_upper": round(ci_upper, 2)
            })

        # Calculate growth rate (first pred vs last actual)
        last_actual = df['value'].iloc[-1]
        growth_rate = ((predictions[-1]['value'] - last_actual) / last_actual) * 100

        # Return combined historical + predicted for charts
        historical_out = [
            {"date": d.strftime("%Y-%m-%d"), "value": round(v, 2)} 
            for d, v in zip(df.index, df['value'])
        ]

        return {
            "metric": metric,
            "historical": historical_out,
            "predictions": predictions,
            "growth_rate_pct": round(growth_rate, 2)
        }

    def scenario_analysis(self, params: dict) -> dict:
        """
        2. WHAT-IF SCENARIO ANALYSIS
        """
        base_revenue = 150000 
        base_profit = 15000
        
        sales_growth = params.get("sales_growth", 0) / 100
        cost_increase = params.get("cost_increase", 0) / 100
        market_share = params.get("market_share_change", 0) / 100
        
        # Base scenario (user params)
        base_scen_rev = base_revenue * (1 + sales_growth) * (1 + market_share)
        base_scen_cost = (base_revenue - base_profit) * (1 + cost_increase)
        base_scen_profit = base_scen_rev - base_scen_cost
        
        # Optimistic (+5% better conditions)
        opt_rev = base_revenue * (1 + sales_growth + 0.05) * (1 + market_share + 0.02)
        opt_cost = (base_revenue - base_profit) * (1 + cost_increase - 0.02)
        opt_profit = opt_rev - opt_cost
        
        # Pessimistic (-5% worse conditions)
        pess_rev = base_revenue * (1 + sales_growth - 0.05) * (1 + market_share - 0.02)
        pess_cost = (base_revenue - base_profit) * (1 + cost_increase + 0.02)
        pess_profit = pess_rev - pess_cost
        
        return {
            "optimistic": {
                "revenue": round(opt_rev, 2),
                "profit": round(opt_profit, 2)
            },
            "base": {
                "revenue": round(base_scen_rev, 2),
                "profit": round(base_scen_profit, 2)
            },
            "pessimistic": {
                "revenue": round(pess_rev, 2),
                "profit": round(pess_profit, 2)
            }
        }

    def detect_anomalies(self) -> dict:
        """
        3. ANOMALY DETECTION
        Scan metric data, flag > 2 std dev.
        """
        df = self._extract_historical_data("revenue")
        mean = df['value'].mean()
        std = df['value'].std()
        
        # Inject an anomaly for demonstration
        df.loc[10, 'value'] = mean + (3 * std)
        
        anomalies = []
        for idx, row in df.iterrows():
            if abs(row['value'] - mean) > 2 * std:
                date_str = row['date'].strftime("%b %Y")
                
                # Use Groq to explain anomaly
                explanation = "Unusual fluctuation detected."
                if self.groq_client:
                    prompt = f"In {date_str}, Tata Motors revenue spiked/dropped significantly to {row['value']} (mean was {mean}). Provide a one-line realistic business reason why."
                    try:
                        res = self.groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=60
                        )
                        explanation = res.choices[0].message.content.strip()
                    except:
                        pass
                
                anomalies.append({
                    "date": date_str,
                    "value": round(row['value'], 2),
                    "deviation": round((row['value'] - mean) / std, 2),
                    "explanation": explanation
                })
                
        return {"anomalies": anomalies}

    def variance_analysis(self, period1: str, period2: str, metric: str) -> dict:
        """
        4. VARIANCE ANALYSIS
        Compare two periods.
        """
        # Mock retrieval from Chroma / Dataset
        val1 = 15317.0 # e.g. Q3 2024
        val2 = 14430.5 # e.g. Q3 2023
        
        diff = val1 - val2
        pct_change = (diff / val2) * 100
        
        explanation = "Data variation."
        if self.groq_client:
            prompt = f"Compare Tata Motors {metric} of {period1} ({val1}) vs {period2} ({val2}). The percentage change is {pct_change}%. Give a one-line AI explanation of the cause."
            try:
                res = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=60
                )
                explanation = res.choices[0].message.content.strip()
            except:
                pass
                
        return {
            "metric": metric,
            "period1": {"label": period1, "value": val1},
            "period2": {"label": period2, "value": val2},
            "absolute_difference": round(diff, 2),
            "percentage_change": round(pct_change, 2),
            "explanation": explanation
        }