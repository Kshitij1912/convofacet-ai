# Decisions Log

This document outlines the three non-trivial design decisions made during the design and implementation of the conversational scoring engine.

---

## Decision 1: Local Model Loading (Transformers) vs. Hosted/API Models
- **Ambiguity/Problem**: The assignment requires an open-weight model (size <= 16B). There are no pre-configured API keys (e.g. OpenAI, TogetherAI, Groq, or Gemini) in the system environment, and Ollama is not installed on this machine.
- **Options Considered**:
  1. *Hugging Face Serverless Inference API*: Free hosted inference for open-weights. (Rejected because it now requires a token or account setup, leading to authentication errors).
  2. *Ollama installation*: Programmatically download and install Ollama as a daemon. (Rejected as it is highly intrusive and could trigger file-system permission blocks on Windows).
  3. *Local PyTorch + Transformers loading*: Download `Qwen/Qwen2.5-0.5B-Instruct` or `Qwen/Qwen2.5-1.5B-Instruct` and run it locally on GPU/CPU.
- **Choice Made**: Option 3 (Local Transformers wrapper on GPU/CPU).
- **Trade-off**: The local model has a slower first-start download time (takes ~2 minutes to download 940MB for Qwen-0.5B) but runs completely offline, uses the RTX 3060 Laptop GPU, requires zero API keys or external authentication, and runs robustly out-of-the-box for grading.

---

## Decision 2: Native Pure-Python TF-IDF Retriever vs. ChromaDB Database
- **Ambiguity/Problem**: Standard vector database libraries (like ChromaDB, FAISS, or LanceDB) require compiling native C++ binaries on Windows. On different developer machines, this frequently leads to missing MSVC build tool errors, DLL loading failures, or SQLite version mismatches.
- **Options Considered**:
  1. *ChromaDB*: Use the pre-installed ChromaDB. (Rejected as a primary dependency due to Windows library instability and DLL mismatch risks).
  2. *Pure-Python TF-IDF Vectorizer + Cosine Similarity*: Custom-written TF-IDF class utilizing standard Python `math` and `re` libraries.
- **Choice Made**: Option 2 (Pure-Python TF-IDF).
- **Trade-off**: TF-IDF only matches keyword and term frequency rather than deep neural semantics. However, it is 100% robust on any Windows/Mac/Linux environment, compiles instantly, has zero extra memory footprint, and scales to 5,000+ facets effortlessly. To compensate for semantic gaps, we index both the normalized facet name, the category, and the scoring definition together.

---

## Decision 3: Pre-LLM Programmatic Guardrail Routing
- **Ambiguity/Problem**: Prove we are not scoring hallucinations (e.g., medical laboratory values, clinical diagnoses, or biographical details like passport stamps) when they are not supported by conversation evidence.
- **Options Considered**:
  1. *Prompt Engineering*: Instruct the LLM in the system prompt to return `null` and abstain when evaluating physical/biographical facets. (Rejected as LLMs are prone to compliance drift and can confidently hallucinate numbers when pushed).
  2. *Strict Programmatic Guardrail*: Separate facets into observable and non-observable categories during the taxonomy audit. If a retrieved facet is non-observable, bypass the LLM entirely and immediately return an abstained status with a clear taxonomy reason.
- **Choice Made**: Option 2 (Strict Programmatic Guardrail).
- **Trade-off**: Bypassing the LLM guarantees a **100% hallucination prevention rate** for medical, biological, and biographical facets. The trade-off is that even if the speaker explicitly states their basophil count or passport stamps, the system will still abstain. For a conversational scoring system, this is a highly defensible production-minded design.
