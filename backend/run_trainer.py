import sys
import os
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# Redirect prints to log
log_file = open("training_results_log.txt", "w", encoding="utf-8")
import builtins
_original_print = builtins.print

def log(msg=""):
    _original_print(msg, flush=True)
    log_file.write(str(msg) + "\n")
    log_file.flush()

from folder_trainer import FolderDatasetTrainer
from ai_financial_memory import FinancialVectorStore

folder_path = r"F:\report_anayser\tata rooling forcasting"
company_name = "Tata Motors"

log(f"\nTraining AI on folder: {folder_path}")
log(f"Company: {company_name}")

# Intercept prints in FolderDatasetTrainer
def _custom_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    log(msg)
builtins.print = _custom_print

t0 = time.time()
trainer = FolderDatasetTrainer(company_name=company_name)
chunks = trainer.process_folder(folder_path)

if not chunks:
    log("No chunks created. Check your folder path and files.")
    sys.exit(1)

json_path = os.path.join(os.path.dirname(__file__), 'my_knowledge_base.json')
trainer.save_chunks(json_path)
trainer.print_summary()

builtins.print = _original_print

log(f"\n{'='*50}")
log("Loading into ChromaDB vector store...")
log(f"{'='*50}")

chroma_path = os.path.join(os.path.dirname(__file__), 'chroma_db', 'my_company')
vector_store = FinancialVectorStore(
    company_name=company_name,
    persist_dir=chroma_path
)
vector_store.add_chunks(chunks)
t1 = time.time()

log(f"\nTime taken: {t1-t0:.2f} seconds")
log(f"Total chunks in ChromaDB: {vector_store.collection.count()}")

log_file.close()

from dotenv import load_dotenv
load_dotenv('.env')

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

from ai_financial_memory import FinancialAIAdvisor
advisor = FinancialAIAdvisor(
    company_name=company_name,
    vector_store=vector_store,
    groq_api_key=GROQ_API_KEY,
    gemini_api_key=GEMINI_API_KEY,
    anthropic_api_key=ANTHROPIC_API_KEY,
)

result = advisor.ask("what is total revenue in 2024?")
log_test = open("test_question_log.txt", "w", encoding="utf-8")
log_test.write("Answer: " + result.get('answer', '') + "\n")
log_test.write("Level Used: " + str(result.get('level_used', '')) + "\n")
log_test.write("Model Used: " + str(result.get('model_used', '')) + "\n")
log_test.write("Confidence: " + str(result.get('confidence', '')) + "\n")
log_test.write("Sources: " + str(result.get('sources', [])) + "\n")
log_test.close()

if os.path.exists('chat_history.json'):
    with open('chat_history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)
    print(f"chat_history.json updated, now has {len(history)} entries")
