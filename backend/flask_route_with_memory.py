import os
from flask import Blueprint, request, jsonify
from ai_financial_memory import FinancialVectorStore, FinancialAIAdvisor
from dotenv import load_dotenv

load_dotenv('.env')
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

memory_bp = Blueprint('memory_bp', __name__)

vector_store_cache = None
advisor_cache = None

def get_advisor(company_name="Tata Motors"):
    global vector_store_cache, advisor_cache
    if advisor_cache:
        return advisor_cache

    chroma_path = os.path.join(os.path.dirname(__file__), 'chroma_db', 'tata_motors')
    try:
        vector_store_cache = FinancialVectorStore(company_name, persist_dir=chroma_path)
    except:
        vector_store_cache = None

    advisor_cache = FinancialAIAdvisor(
        company_name=company_name,
        vector_store=vector_store_cache,
        groq_api_key=GROQ_API_KEY,
        gemini_api_key=GEMINI_API_KEY,
        anthropic_api_key=ANTHROPIC_API_KEY,
    )
    return advisor_cache

@memory_bp.route('/api/ai/ask', methods=['POST'])
def chat():
    data = request.get_json() or {}
    question = data.get('question', '')
    learn_mode = data.get('learn_mode', False)
    
    if not question:
        return jsonify({"status": "error", "message": "No question provided"}), 400

    advisor = get_advisor()
    try:
        result = advisor.ask(question, learn_mode=learn_mode)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@memory_bp.route('/api/chat/reset', methods=['POST'])
def reset_chat():
    advisor = get_advisor()
    advisor.reset_conversation()
    return jsonify({"status": "success", "message": "Conversation history cleared"})
