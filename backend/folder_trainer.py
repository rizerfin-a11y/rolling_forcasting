# backend/folder_trainer.py
# Trains AI on a folder of PDF and Excel files
# Run: python folder_trainer.py "F:/your/folder/path"

import sys
import os
import json
import pandas as pd
import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))


class FolderDatasetTrainer:
    def __init__(self, company_name: str = "My Company"):
        self.company_name = company_name
        self.chunks = []
        self.processed_files = []
        self.failed_files = []

    def read_pdf(self, filepath: str) -> str:
        """Extract all text from a PDF file using PyMuPDF."""
        text = ""
        try:
            doc = fitz.open(filepath)
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text:
                    text += f"\n--- Page {page_num+1} ---\n{page_text}"
                
                # Extract tables using PyMuPDF's built-in table finder
                if hasattr(page, "find_tables"):
                    tables = page.find_tables()
                    for table in tables:
                        extracted = table.extract()
                        for row in extracted:
                            if row:
                                clean_row = [str(cell).strip() if cell else "" for cell in row]
                                text += "\n" + " | ".join(clean_row)
            doc.close()
        except Exception as e:
            print(f"  ✗ PDF read error: {e}")
        return text.strip()

    def read_excel(self, filepath: str) -> str:
        """Extract all data from Excel/CSV file."""
        text = ""
        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
                sheets = {"Sheet1": df}
            else:
                xl = pd.ExcelFile(filepath)
                sheets = {sheet: pd.read_excel(filepath, sheet_name=sheet)
                         for sheet in xl.sheet_names}

            for sheet_name, df in sheets.items():
                if df.empty:
                    continue
                df = df.fillna("")
                text += f"\n--- Sheet: {sheet_name} ---\n"
                text += f"Columns: {', '.join(str(c) for c in df.columns)}\n"
                text += df.to_string(index=False)
                text += "\n"
        except Exception as e:
            print(f"  ✗ Excel read error: {e}")
        return text.strip()

    def text_to_chunks(self, text: str, filename: str,
                        chunk_size: int = 1000) -> list:
        """Split large text into overlapping chunks."""
        chunks = []
        words = text.split()
        
        if not words:
            return chunks

        # Split into chunks of ~chunk_size words with 100 word overlap
        overlap = 100
        step = chunk_size - overlap

        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)

            if len(chunk_text.strip()) < 50:
                continue

            chunk_id = f"{filename.replace('.', '_')}_{i//step}"
            chunks.append({
                "id": chunk_id,
                "type": "document_chunk",
                "text": f"[Source: {filename}]\n{chunk_text}",
                "metadata": {
                    "company": self.company_name,
                    "source_file": filename,
                    "data_type": "document_chunk",
                    "chunk_index": i // step,
                }
            })

        return chunks

    def process_folder(self, folder_path: str) -> list:
        """Process all PDF and Excel files in a folder."""
        if not os.path.exists(folder_path):
            print(f"✗ Folder not found: {folder_path}")
            return []

        # Find all supported files
        supported = ('.pdf', '.xlsx', '.xls', '.csv')
        files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(supported) and not f.startswith('~')
        ]

        if not files:
            print(f"✗ No PDF/Excel/CSV files found in {folder_path}")
            return []

        print(f"\nFound {len(files)} files to process:")
        for f in files:
            print(f"  - {f}")

        all_chunks = []

        for filename in files:
            filepath = os.path.join(folder_path, filename)
            print(f"\nProcessing: {filename}")

            try:
                ext = filename.lower()
                if ext.endswith('.pdf'):
                    text = self.read_pdf(filepath)
                    file_type = "PDF"
                elif ext.endswith(('.xlsx', '.xls', '.csv')):
                    text = self.read_excel(filepath)
                    file_type = "Excel/CSV"
                else:
                    continue

                if not text:
                    print(f"  ✗ No text extracted from {filename}")
                    self.failed_files.append(filename)
                    continue

                word_count = len(text.split())
                print(f"  ✓ Extracted {word_count} words from {file_type}")

                chunks = self.text_to_chunks(text, filename)
                print(f"  ✓ Created {len(chunks)} chunks")

                all_chunks.extend(chunks)
                self.processed_files.append(filename)

            except Exception as e:
                print(f"  ✗ Failed to process {filename}: {e}")
                self.failed_files.append(filename)

        self.chunks = all_chunks
        return all_chunks

    def save_chunks(self, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {len(self.chunks)} chunks to {output_path}")

    def print_summary(self):
        print(f"\n{'='*50}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"✓ Processed: {len(self.processed_files)} files")
        print(f"✗ Failed:    {len(self.failed_files)} files")
        print(f"Total chunks created: {len(self.chunks)}")
        if self.failed_files:
            print(f"\nFailed files:")
            for f in self.failed_files:
                print(f"  - {f}")


def main():
    # Get folder path from command line or ask
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = input("Enter the full path to your dataset folder: ").strip().strip('"')

    company_name = input("Enter company name (or press Enter for 'My Company'): ").strip()
    if not company_name:
        company_name = "My Company"

    print(f"\nTraining AI on folder: {folder_path}")
    print(f"Company: {company_name}")

    # Step 1: Process all files
    trainer = FolderDatasetTrainer(company_name=company_name)
    chunks = trainer.process_folder(folder_path)

    if not chunks:
        print("No chunks created. Check your folder path and files.")
        sys.exit(1)

    # Step 2: Save chunks to JSON
    json_path = os.path.join(BASE_DIR, 'my_knowledge_base.json')
    trainer.save_chunks(json_path)
    trainer.print_summary()

    # Step 3: Load into ChromaDB
    print(f"\n{'='*50}")
    print("Loading into ChromaDB vector store...")
    print(f"{'='*50}")

    from ai_financial_memory import FinancialVectorStore
    chroma_path = os.path.join(BASE_DIR, 'chroma_db', 'my_company')
    vector_store = FinancialVectorStore(
        company_name=company_name,
        persist_dir=chroma_path
    )
    vector_store.add_chunks(chunks)

    # Step 4: Test with Groq
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    if not GROQ_API_KEY:
        print("\n✓ Data loaded! Add GROQ_API_KEY to .env to enable AI chat.")
        sys.exit(0)

    print(f"\n{'='*50}")
    print("Testing AI on your data...")
    print(f"{'='*50}")

    from ai_financial_memory import FinancialAIAdvisor
    advisor = FinancialAIAdvisor(
        company_name=company_name,
        vector_store=vector_store,
        groq_api_key=GROQ_API_KEY,
    )

    print("\nCHAT MODE — ask questions about your documents")
    print("Commands: 'quit' to exit | 'reset' to clear history")
    print("="*50)

    while True:
        try:
            q = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q:
            continue
        if q.lower() == 'quit':
            break
        if q.lower() == 'reset':
            advisor.reset_conversation()
            print("Conversation cleared")
            continue

        result = advisor.ask(q)
        print(f"\nAI: {result['answer']}")
        print(f"[Confidence: {result['confidence']} | Sources: {result['sources'][:2]}]")

    print("\nDone! Your data is permanently stored in ChromaDB.")


if __name__ == '__main__':
    main()