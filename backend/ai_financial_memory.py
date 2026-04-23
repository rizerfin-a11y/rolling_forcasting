# backend/ai_financial_memory.py
# ═══════════════════════════════════════════════════════════════════════════════
# AI Financial Advisor with Fallback System
# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK ORDER:
#   1. ChromaDB vector search → Groq (llama-3.3-70b-versatile)
#   2. If Groq fails/low quality → Gemini (gemini-1.5-flash)
#   3. If Gemini fails/low quality → Anthropic Claude (claude-haiku-4-5)
#   4. If ALL fail → return best available answer (never empty)
#
# FEATURES:
#   - 6-turn conversation memory for follow-up questions
#   - Persistent chat history in chat_history.json
#   - Financial advisor personality (explanations, not raw data)
#   - Auto-loads previous chat history on startup
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from datetime import datetime
from typing import Optional, List, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── Vector Store ─────────────────────────────────────────────────────────────

class FinancialVectorStore:
    """ChromaDB-backed vector store for financial document chunks."""

    def __init__(self, company_name: str, persist_dir: str = "./chroma_db"):
        self.company_name = company_name
        self.persist_dir = persist_dir
        self.collection = None
        self._init_store()

    def _init_store(self):
        import chromadb
        from chromadb.utils import embedding_functions

        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        collection_name = f"financial_{self.company_name.lower().replace(' ', '_')}"
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"✓ Vector store initialized: {collection_name}")
        print(f"  Existing chunks: {self.collection.count()}")

    def add_chunks(self, chunks: list, batch_size: int = 50):
        """Add document chunks to the vector store, skipping duplicates."""
        if not chunks:
            return

        existing_ids = set()
        if self.collection.count() > 0:
            existing = self.collection.get()
            existing_ids = set(existing['ids'])

        new_chunks = [c for c in chunks if c['id'] not in existing_ids]
        if not new_chunks:
            print("  All chunks already exist in store — skipping")
            return

        print(f"  Adding {len(new_chunks)} new chunks...")
        for i in range(0, len(new_chunks), batch_size):
            batch = new_chunks[i:i + batch_size]
            self.collection.add(
                ids=[c['id'] for c in batch],
                documents=[c['text'] for c in batch],
                metadatas=[c.get('metadata', {}) for c in batch],
            )
            print(f"  Batch {i // batch_size + 1}: added {len(batch)} chunks")
        print(f"✓ Total chunks in store: {self.collection.count()}")

    def retrieve(self, query: str, n_results: int = 5) -> list:
        """Search the vector store for relevant chunks."""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count()),
        )
        if not results['documents'][0]:
            return []

        retrieved = []
        for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ):
            retrieved.append({
                "text": doc,
                "metadata": meta,
                "relevance_score": round(1 - dist, 3),
            })
        retrieved.sort(key=lambda x: x['relevance_score'], reverse=True)
        return retrieved


# ─── Fallback AI Advisor ──────────────────────────────────────────────────────

class FallbackAIAdvisor:
    """
    Multi-model fallback AI financial advisor.

    Fallback chain:
        Level 1: ChromaDB context + Groq (llama-3.3-70b-versatile)
        Level 2: ChromaDB context + Gemini (gemini-1.5-flash)
        Level 3: ChromaDB context + Anthropic Claude (claude-haiku-4-5)
        Level 4: Best available answer (never returns empty)

    Features:
        - 6-turn conversation memory for contextual follow-ups
        - Persistent chat history saved to chat_history.json
        - Financial advisor personality with analysis and explanations
    """

    CONFIDENCE_THRESHOLD = 0.55
    MAX_HISTORY_TURNS = 6
    CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

    # Phrases that indicate low-quality / cop-out answers
    LOW_QUALITY_PHRASES = [
        "not in the records",
        "not in my records",
        "not available",
        "cannot find",
        "no information",
        "not provided",
        "don't have",
        "do not have",
        "i don't know",
        "i do not know",
        "unable to find",
        "no data",
        "not mentioned",
        "not specified",
        "i cannot",
        "i'm unable",
        "unfortunately, i don't",
        "unfortunately, i do not",
        "data is not in",
        "no specific data",
        "not in the provided",
        "not included in",
    ]

    def __init__(self, company_name: str, vector_store: FinancialVectorStore,
                 groq_api_key: str = "",
                 gemini_api_key: str = "",
                 anthropic_api_key: str = "",
                 language: str = "english"):
        self.company_name = company_name
        self.vector_store = vector_store
        self.language = language

        # In-memory conversation history (last N turns for prompt context)
        self.conversation_history: List[Dict] = []
        self.context_memory = {
            "year": None,
            "month": None,
            "metric": None,
            "segment": None
        }

        # Persistent chat history (saved to JSON)
        self.persistent_chat_history: List[Dict] = []
        self._load_chat_history()

        # ── Initialize AI clients ─────────────────────────────────────────
        self.groq_client = None
        self.gemini_client = None
        self.gemini_model = None
        self.anthropic_client = None

        if groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_api_key)
                print("✓ Level 1: Groq llama-3.3-70b-versatile ready")
            except Exception as e:
                print(f"✗ Groq init failed: {e}")

        if gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_api_key)
                self.gemini_model = 'gemini-1.5-flash'
                print("✓ Level 2: Gemini 1.5-flash ready")
            except Exception as e:
                print(f"✗ Gemini init failed: {e}")

        if anthropic_api_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
                print("✓ Level 3: Anthropic Claude (claude-haiku-4-5) ready")
            except Exception as e:
                print(f"✗ Anthropic init failed: {e}")

        if not any([self.groq_client, self.gemini_model, self.anthropic_client]):
            print("⚠ WARNING: No AI models available — add API keys to .env")

    # ── Chat History Persistence ──────────────────────────────────────────

    def _load_chat_history(self):
        """Load existing chat history from JSON file on startup."""
        if os.path.exists(self.CHAT_HISTORY_FILE):
            try:
                with open(self.CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.persistent_chat_history = json.load(f)
                count = len(self.persistent_chat_history)
                print(f"✓ Loaded {count} previous chat entries from chat_history.json")

                # Restore last N turns into in-memory conversation history
                recent = self.persistent_chat_history[-self.MAX_HISTORY_TURNS:]
                for entry in recent:
                    self.conversation_history.append({
                        "question": entry.get("question", ""),
                        "answer": entry.get("answer", ""),
                    })
            except Exception as e:
                print(f"⚠ Could not load chat_history.json: {e}")
                self.persistent_chat_history = []
        else:
            print("ℹ No previous chat_history.json found — starting fresh")

    def _save_chat_entry(self, question: str, answer: str, model_used: str,
                         confidence: str, sources: list):
        """Append a single Q&A entry to the persistent chat history JSON."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "model_used": model_used,
            "confidence": confidence,
            "sources": sources,
        }
        self.persistent_chat_history.append(entry)
        try:
            with open(self.CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.persistent_chat_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠ Could not save chat_history.json: {e}")

    # ── System Prompt Builder ─────────────────────────────────────────────

    def _build_system_prompt(self, retrieved_context: str, learn_mode: bool = False) -> str:
        """Build the system prompt with context, history, and personality."""

        # Language instruction
        lang_instruction = ""
        if self.language == "tamil":
            lang_instruction = "\nIMPORTANT: Respond entirely in Tamil."
        elif self.language == "hindi":
            lang_instruction = "\nIMPORTANT: Respond entirely in Hindi."

        learn_instruction = ""
        if learn_mode:
            learn_instruction = """
[LEARN MODE ACTIVATED]
For every answer, you MUST strictly include the following sections exactly formatted:
1. A plain English explanation (absolutely no complex finance jargon).
2. An analogy using an everyday Indian context (e.g., comparing revenue to a monthly salary).
3. A distinct 'Why does this matter?' section in exactly 1 clear sentence at the end.
"""

        # Build conversation history text (last 6 turns)
        history_text = ""
        for turn in self.conversation_history[-self.MAX_HISTORY_TURNS:]:
            history_text += f"User: {turn['question']}\nAdvisor: {turn['answer']}\n\n"

        return f"""You are a senior financial advisor and analyst specializing in {self.company_name}.

YOUR PERSONALITY:
- You are a knowledgeable, experienced financial advisor — NOT a search engine.
- You provide explanations, context, trends, and analysis — not just raw numbers.
- When presenting data, explain what it means, compare periods, and highlight trends.
- If the user asks a vague or follow-up question (like "what about 2022?" or "why?"), 
  use the conversation history below to understand what they're referring to.
- NEVER say "I don't know" or "data not available". Always give the BEST possible 
  answer from the data you have. If exact data isn't available, provide related 
  insights, trends, or estimates based on available information.
- Be confident, professional, and helpful at all times.
{learn_instruction}


FINANCIAL DATA FROM COMPANY DOCUMENTS:
{retrieved_context}

RECENT CONVERSATION HISTORY:
{history_text if history_text else "No previous conversation."}

RESPONSE GUIDELINES:
1. Use the financial data above as your primary source.
2. Always mention specific time periods, quarters, or fiscal years when citing figures.
3. Present amounts in Crores (₹) format where applicable.
4. Provide analysis and context — explain what the numbers mean.
5. If the user's question is a follow-up, connect it to the previous conversation.
6. If exact data is missing, provide the closest available data with explanation.
7. Structure your response clearly with key points.
8. Be conversational but professional.{lang_instruction}"""

    # ── Model Callers ─────────────────────────────────────────────────────

    def _try_groq(self, question: str, system_prompt: str) -> tuple:
        """Try Groq llama-3.3-70b-versatile. Returns (answer, success)."""
        if not self.groq_client:
            return None, False
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1200,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            )
            answer = response.choices[0].message.content.strip()
            return answer, True
        except Exception as e:
            print(f"  ✗ Groq error: {e}")
            return None, False

    def _try_gemini(self, question: str, system_prompt: str) -> tuple:
        """Try Gemini 1.5-flash. Returns (answer, success)."""
        if not self.gemini_client:
            return None, False
        try:
            prompt = f"{system_prompt}\n\nUser question: {question}"
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
            )
            answer = response.text.strip()
            return answer, True
        except Exception as e:
            print(f"  ✗ Gemini error: {e}")
            return None, False

    def _try_anthropic(self, question: str, system_prompt: str) -> tuple:
        """Try Anthropic Claude (claude-haiku-4-5). Returns (answer, success)."""
        if not self.anthropic_client:
            return None, False
        try:
            response = self.anthropic_client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1200,
                system=system_prompt,
                messages=[{"role": "user", "content": question}]
            )
            answer = response.content[0].text.strip()
            return answer, True
        except Exception as e:
            print(f"  ✗ Anthropic error: {e}")
            return None, False

    # ── Quality Check ─────────────────────────────────────────────────────

    def _is_low_quality(self, answer: str) -> bool:
        """Check if an answer is a cop-out / low quality and needs escalation."""
        if not answer:
            return True
        if len(answer.strip()) < 20:
            return True
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in self.LOW_QUALITY_PHRASES)

    def _resolve_question(self, question: str) -> str:
        """Resolve a vague follow-up question into a standalone question using context memory."""
        if not self.conversation_history or not self.groq_client:
            return question

        history_text = "\n".join([
            f"User: {turn['question']}\nAI: {turn['answer'][:150]}..."
            for turn in self.conversation_history[-3:]
        ])

        system_prompt = f"""You are a query resolution engine.
Your task is to take a user's potentially vague follow-up question and rewrite it into a fully complete, standalone question about Tata Motors.
Use the conversation history and current context memory to fill in missing entities (year, month, metric, company segment).

Current Context Memory:
{json.dumps(self.context_memory)}

Recent Conversation History:
{history_text}

Analyze the user's latest question. If it is vague (e.g., "what about January?", "why did it drop?", "compare with last year"), rewrite it using the current context. If it introduces new entities, extract them to update the context memory.
Respond ONLY with a JSON object in this exact format, with no other text:
{{
    "resolved_question": "the rewritten standalone question",
    "context_memory": {{
        "year": "extract or keep previous",
        "month": "extract or keep previous",
        "metric": "extract or keep previous",
        "segment": "extract or keep previous"
    }}
}}"""
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=300,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            )
            content = response.choices[0].message.content.strip()
            
            # Extract JSON if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            
            if "context_memory" in data:
                # Update memory without overwriting valid states needlessly
                for k, v in data["context_memory"].items():
                    if v is not None and str(v).lower() not in ['none', 'null', '']:
                        self.context_memory[k] = v
            
            return data.get("resolved_question", question)
        except Exception as e:
            print(f"  ⚠ Failed to resolve question context: {e}")
            return question

    # ── Main Ask Method ───────────────────────────────────────────────────

    def ask(self, question: str, learn_mode: bool = False) -> dict:
        """
        Ask a question with full fallback chain.
        Returns dict with: answer, model_used, level_used, relevance_score,
                          confidence, sources
        """
        print(f"\n{'─'*60}")
        print(f"  Raw Question: {question}")
        
        resolved_question = self._resolve_question(question)
        if resolved_question != question:
            print(f"  Resolved:     {resolved_question}")
        print(f"{'─'*60}")

        # ── Step 1: Retrieve context from ChromaDB ────────────────────────
        retrieved = self.vector_store.retrieve(resolved_question, n_results=5)

        avg_relevance = 0.0
        sources = []
        if retrieved:
            avg_relevance = sum(r['relevance_score'] for r in retrieved) / len(retrieved)
            retrieved_context = "\n\n---\n\n".join([
                f"[Source: {r['metadata'].get('source_file', 'document')}]\n{r['text'][:800]}"
                for r in retrieved
            ])
            sources = list(set(
                r['metadata'].get('source_file', '') for r in retrieved
            ))
            print(f"  📚 Retrieved {len(retrieved)} chunks (avg relevance: {avg_relevance:.3f})")
            print(f"  📄 Sources: {sources}")
        else:
            retrieved_context = "No specific data found in trained documents."
            print("  📚 No relevant chunks found in vector store")

        system_prompt = self._build_system_prompt(retrieved_context, learn_mode=learn_mode)

        # ── Step 2: Fallback chain ────────────────────────────────────────
        answer = None
        model_used = "None"
        level_used = 0
        all_answers = {}  # Collect all answers for "best available" fallback

        # Level 1: Groq
        print(f"  [L1] Trying Groq llama-3.3-70b...", end=" ", flush=True)
        groq_answer, groq_ok = self._try_groq(resolved_question, system_prompt)
        if groq_ok:
            all_answers["Groq llama-3.3-70b"] = groq_answer
        if groq_ok and not self._is_low_quality(groq_answer):
            answer = groq_answer
            model_used = "Groq llama-3.3-70b"
            level_used = 1
            print("✓ GOOD ANSWER")
        else:
            reason = "low quality" if groq_ok else "failed"
            print(f"⚠ ({reason}) → escalating to Gemini")

            # Level 2: Gemini
            print(f"  [L2] Trying Gemini 1.5-flash...", end=" ", flush=True)
            gemini_answer, gemini_ok = self._try_gemini(resolved_question, system_prompt)
            if gemini_ok:
                all_answers["Gemini 1.5-flash"] = gemini_answer
            if gemini_ok and not self._is_low_quality(gemini_answer):
                answer = gemini_answer
                model_used = "Gemini 1.5-flash"
                level_used = 2
                print("✓ GOOD ANSWER")
            else:
                reason = "low quality" if gemini_ok else "failed"
                print(f"⚠ ({reason}) → escalating to Anthropic")

                # Level 3: Anthropic
                print(f"  [L3] Trying Anthropic Claude...", end=" ", flush=True)
                anthropic_answer, anthropic_ok = self._try_anthropic(resolved_question, system_prompt)
                if anthropic_ok:
                    all_answers["Anthropic Claude"] = anthropic_answer
                if anthropic_ok and not self._is_low_quality(anthropic_answer):
                    answer = anthropic_answer
                    model_used = "Anthropic Claude"
                    level_used = 3
                    print("✓ GOOD ANSWER")
                else:
                    reason = "low quality" if anthropic_ok else "failed"
                    print(f"⚠ ({reason})")

                    # Level 4: Best available — NEVER return empty
                    print(f"  [L4] Using best available answer...")
                    level_used = 4
                    if all_answers:
                        # Pick the longest answer (likely most informative)
                        best_model = max(all_answers, key=lambda k: len(all_answers[k]))
                        answer = all_answers[best_model]
                        model_used = f"{best_model} (best available)"
                        print(f"  → Using {model_used}")
                    else:
                        # Absolute last resort — construct helpful response from chunks
                        if retrieved:
                            chunk_summary = "\n".join([
                                f"• {r['text'][:200]}..."
                                for r in retrieved[:3]
                            ])
                            answer = (
                                f"Based on the available financial documents for "
                                f"{self.company_name}, here is what I found relevant "
                                f"to your query:\n\n{chunk_summary}\n\n"
                                f"For more specific details, please refine your question "
                                f"or ensure the relevant documents have been uploaded."
                            )
                        else:
                            answer = (
                                f"I'm currently working with the financial data available "
                                f"for {self.company_name}. While I couldn't find an exact "
                                f"match for your specific query, I recommend:\n\n"
                                f"1. Trying a more specific question with dates or metrics\n"
                                f"2. Checking if the relevant financial documents have been "
                                f"uploaded and trained\n"
                                f"3. Asking about specific quarters or fiscal years\n\n"
                                f"I'm here to help analyze any financial data you provide!"
                            )
                        model_used = "System (no AI available)"
                        print(f"  → Using system fallback response")

        # ── Step 3: Determine confidence ──────────────────────────────────
        if avg_relevance > 0.7:
            confidence = "high"
        elif avg_relevance > 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        # ── Step 4: Save to conversation memory (in-session) ──────────────
        self.conversation_history.append({
            "question": question,
            "answer": answer,
        })
        # Keep only the last MAX_HISTORY_TURNS * 2 to prevent memory bloat
        if len(self.conversation_history) > self.MAX_HISTORY_TURNS * 2:
            self.conversation_history = self.conversation_history[-self.MAX_HISTORY_TURNS:]

        # ── Step 5: Save to persistent chat history (JSON) ────────────────
        self._save_chat_entry(
            question=question,
            answer=answer,
            model_used=model_used,
            confidence=confidence,
            sources=sources,
        )

        # ── Step 6: Build result ──────────────────────────────────────────
        result = {
            "answer": answer,
            "model_used": model_used,
            "level_used": level_used,
            "relevance_score": round(avg_relevance, 3),
            "confidence": confidence,
            "sources": sources,
        }

        print(f"\n  ✅ Answered by: {model_used} (Level {level_used})")
        print(f"  📊 Confidence: {confidence} | Relevance: {avg_relevance:.3f}")
        print(f"  💾 Saved to chat_history.json")
        print(f"{'─'*60}")

        return result

    # ── Conversation Management ───────────────────────────────────────────

    def reset_conversation(self):
        """Clear in-memory conversation history (persistent history is kept)."""
        self.conversation_history = []
        self.context_memory = {
            "year": None,
            "month": None,
            "metric": None,
            "segment": None
        }
        print("✓ Conversation memory & context cleared (chat_history.json preserved)")

    def set_language(self, language: str):
        """Set the response language (english, tamil, hindi)."""
        self.language = language
        print(f"✓ Language set to: {language}")

    def get_chat_history(self) -> list:
        """Return the full persistent chat history."""
        return self.persistent_chat_history

    def get_conversation_context(self) -> list:
        """Return the current in-memory conversation turns."""
        return self.conversation_history[-self.MAX_HISTORY_TURNS:]


# ─── Backward Compatibility ──────────────────────────────────────────────────

class FinancialAIAdvisor(FallbackAIAdvisor):
    """Alias for FallbackAIAdvisor to maintain backward compatibility."""

    def __init__(self, company_name, vector_store,
                 groq_api_key="", gemini_api_key="",
                 anthropic_api_key="", language="english"):
        super().__init__(
            company_name=company_name,
            vector_store=vector_store,
            groq_api_key=groq_api_key,
            gemini_api_key=gemini_api_key,
            anthropic_api_key=anthropic_api_key,
            language=language,
        )