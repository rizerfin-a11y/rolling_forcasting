import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Redirect prints to log
log_file = open("test_context_log.txt", "w", encoding="utf-8")
import builtins
_original_print = builtins.print

def log(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    _original_print(msg, flush=True)
    log_file.write(msg + "\n")
    log_file.flush()

builtins.print = log

from dotenv import load_dotenv
load_dotenv('.env')

from ai_financial_memory import FinancialVectorStore, FinancialAIAdvisor

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

chroma_path = os.path.join(os.path.dirname(__file__), 'chroma_db', 'my_company')
# Note: we need to use 'my_company' or 'tata_motors' as used in earlier run
# Wait, since the user retraining was with company_name="Tata Motors", the path might be:
chroma_path = os.path.join(os.path.dirname(__file__), 'chroma_db', 'tata_motors')
vector_store = FinancialVectorStore(
    company_name="Tata Motors",
    persist_dir=chroma_path
)

advisor = FinancialAIAdvisor(
    company_name="Tata Motors",
    vector_store=vector_store,
    groq_api_key=GROQ_API_KEY,
    gemini_api_key=GEMINI_API_KEY,
    anthropic_api_key=ANTHROPIC_API_KEY,
)

advisor.reset_conversation()

questions = [
    "what is revenue in 2024?",
    "what about January in the same year?",
    "how does that compare to 2023?",
    "what about profit?",
    "why did it change?"
]

for q in questions:
    result = advisor.ask(q)
    log(f"\nFinal Answer: {result['answer']}")

builtins.print = _original_print
log_file.close()

