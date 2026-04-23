import os
from flask import Blueprint, request, jsonify
import json
from forecast import FinancialForecaster

forecast_bp = Blueprint('forecast', __name__)
forecaster = FinancialForecaster()

@forecast_bp.route('/api/forecast', methods=['POST'])
def run_forecast():
    """
    POST /api/forecast — accepts {"metric": "revenue", "periods": 6}
    """
    data = request.get_json() or {}
    metric = data.get('metric', 'revenue')
    periods = int(data.get('periods', 6))
    
    try:
        result = forecaster.forecast(metric=metric, periods=periods)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@forecast_bp.route('/api/scenario', methods=['POST'])
def run_scenario():
    """
    POST /api/scenario — accepts {"scenarios": {...}}
    """
    data = request.get_json() or {}
    params = data.get('scenarios', {})
    
    try:
        result = forecaster.scenario_analysis(params)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@forecast_bp.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    """
    GET /api/anomalies
    """
    try:
        result = forecaster.detect_anomalies()
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@forecast_bp.route('/api/variance', methods=['POST'])
def get_variance():
    """
    POST /api/variance — accepts {"period1": "Q3 2024", "period2": "Q3 2023", "metric": "revenue"}
    """
    data = request.get_json() or {}
    period1 = data.get('period1', 'Q3 2024')
    period2 = data.get('period2', 'Q3 2023')
    metric = data.get('metric', 'revenue')
    
    try:
        result = forecaster.variance_analysis(period1, period2, metric)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@forecast_bp.route('/api/market-context', methods=['GET'])
def get_market_context():
    company = request.args.get('company', 'tata-motors')
    ticker_map = {"tata-motors": "TATAMOTORS.NS"}
    ticker = ticker_map.get(company.lower(), "TATAMOTORS.NS")
    
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty:
            return jsonify({"status": "error", "message": "No stock data found"}), 404
            
        current_price = float(hist['Close'].iloc[-1])
        start_price = float(hist['Close'].iloc[0])
        change_pct = ((current_price - start_price) / start_price) * 100
        chart_data = hist['Close'].tolist()
        
        # Retrieve context from ChromaDB
        from ai_financial_memory import FinancialVectorStore, GROQ_API_KEY
        chroma_path = os.path.join(os.path.dirname(__file__), '..', 'chroma_db', 'tata_motors')
        try:
            vs = FinancialVectorStore("Tata Motors", persist_dir=chroma_path)
            retrieved = vs.retrieve("revenue profit growth performance", n_results=3)
            context = "\n".join([r['text'] for r in retrieved])
        except:
            context = "No detailed database context, use general knowledge."
            
        prompt = f"Financial Context:\n{context}\n\nThe stock price of {company} changed by {change_pct:.2f}% over the last 30 days. Based on this financial data and the stock trend, generate a short 2-sentence insight like 'Revenue grew 12% in 2023 but stock dropped 8% — this suggests the market expected higher margins'."
        
        from groq import Groq
        ai_insight = "Stock moved along with market expectations."
        if GROQ_API_KEY:
            groq_client = Groq(api_key=GROQ_API_KEY)
            try:
                res = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=80
                )
                ai_insight = res.choices[0].message.content.strip()
            except:
                pass
                
        return jsonify({
            "status": "success",
            "data": {
                "price": round(current_price, 2),
                "change_percent": round(change_pct, 2),
                "ai_insight": ai_insight,
                "chart_data": [round(x, 2) for x in chart_data]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@forecast_bp.route('/api/simple-report', methods=['GET'])
def get_simple_report():
    company = request.args.get('company', 'Tata Motors')
    try:
        from ai_financial_memory import FinancialVectorStore, GROQ_API_KEY
        chroma_path = os.path.join(os.path.dirname(__file__), '..', 'chroma_db', 'tata_motors')
        try:
            vs = FinancialVectorStore(company, persist_dir=chroma_path)
            retrieved = vs.retrieve("total revenue net profit sales summary", n_results=5)
            context = "\n".join([r['text'] for r in retrieved])
        except:
            context = "No detailed database context."

        prompt = f"Financial Context:\n{context}\n\nGenerate a WhatsApp-forward style financial summary for {company}. Make it short, simple, emoji-rich, and in a mix of easy Hindi and English (Hinglish). Follow a structure like:\n📊 {company} FY2024 में कैसा रहा?\n✅ Revenue: ...\n⚠️ Profit: ...\n🚗 Key driver: ...\nMake it super casual, easy to read, and plain text."
        
        from groq import Groq
        report = "Analysis taking longer than expected. Please try again later."
        if GROQ_API_KEY:
            groq_client = Groq(api_key=GROQ_API_KEY)
            res = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250
            )
            report = res.choices[0].message.content.strip()
            
        return jsonify({"status": "success", "report": report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
