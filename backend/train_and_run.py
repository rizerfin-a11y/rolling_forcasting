import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

print("START", flush=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

from data_processor import FinancialDataProcessor
processor = FinancialDataProcessor("Tata Motors")
df = processor.load_tata_annual_data()
chunks = processor.create_knowledge_chunks(df)
json_path = os.path.join(BASE_DIR, 'tata_knowledge_base.json')
processor.save_chunks_as_json(json_path)
processor.print_summary()

from ai_financial_memory import FinancialVectorStore, FinancialAIAdvisor
chroma_path = os.path.join(BASE_DIR, 'chroma_db', 'tata_motors')
vector_store = FinancialVectorStore("Tata Motors", persist_dir=chroma_path)
vector_store.add_chunks(chunks)

if not GROQ_API_KEY:
    print("Add GROQ_API_KEY to .env file", flush=True)
    sys.exit(0)

advisor = FinancialAIAdvisor(
    company_name="Tata Motors",
    vector_store=vector_store,
    groq_api_key=GROQ_API_KEY,
)
result = advisor.ask("What was Tata Motors revenue in FY 2022-23?")
print(f"\nAI Answer: {result['answer']}", flush=True)
print(f"Confidence: {result['confidence']}", flush=True)

if "--chat" in sys.argv:
    print("\nCHAT MODE — type questions, 'quit' to exit", flush=True)
    lang = "english"
    while True:
        q = input(f"\n[{lang}] You: ").strip()
        if q.lower() == 'quit': break
        if q.lower() in ['tamil','hindi','english']:
            advisor.set_language(q.lower())
            lang = q.lower()
            continue
        if q.lower() == 'reset':
            advisor.reset_conversation()
            print("Cleared")
            continue
        result = advisor.ask(q)
        print(f"\nAI: {result['answer']}")
        print(f"[Confidence: {result['confidence']}]")