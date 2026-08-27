# Prompt Log

This document records the material AI prompts used during development, the reasoning, verification, and what was corrected.

## Material AI Prompts & Tool Calls

### 1. Environment Check & Capability Search
- **Tool/Model**: `Gemini 3.5 Flash (High)` via Antigravity `run_command`
- **Prompt/Query**: `python --version; pip list; ollama list; env`
- **Purpose**: Understand what model resources (local Ollama or PyTorch/CUDA) and libraries are available.
- **Verification**: Output showed Python 3.11.9, no Ollama command found, and a 6GB VRAM NVIDIA RTX 3060 GPU.
- **Decision**: Run a local transformer model using `transformers` on GPU/CPU rather than calling external APIs (no keys in env).

### 2. Facet Taxonomy & Audit Construction
- **Tool/Model**: `Gemini 3.5 Flash (High)` via Antigravity `write_to_file`
- **Prompt/Query**: Writing `audit.py` to classify facets.
- **Verification**: Verified that 30 headers, 127 non-observables, and 272 observables were correctly identified out of 399 total entries.
- **Decision**: Malformed entries (ending in `:`) and counts/biographical details are flagged programmatically.

### 3. Native TF-IDF Search Implementation
- **Tool/Model**: `Gemini 3.5 Flash (High)` via Antigravity `write_to_file`
- **Prompt/Query**: Implementing a pure-Python TF-IDF class for semantic retrieval.
- **Verification**: Ran test queries matching "depression sadness" to ensure the three depression-related facets were retrieved first.
- **Decision**: Avoid ChromaDB binary load errors on Windows.

---

## What AI Got Wrong / What I Corrected

### Example 1: Project File Creation using Artifact Metadata
- **Symptom**: When trying to create the project file `audit.py` in the workspace directory, the tool returned a validation error: `model output error: invalid tool call error (invalid_args) audit.py is not a valid artifact path; artifacts must be in ...`
- **Diagnosis & Root Cause**: The AI generated `ArtifactMetadata` inside the arguments of the `write_to_file` call for a file residing in the workspace directory. Under Antigravity's rules, `ArtifactMetadata` is reserved strictly for files inside the `.gemini/antigravity/brain/<id>/` artifact directory.
- **Fix**: The call was re-run with `ArtifactMetadata` omitted, successfully writing `audit.py` to the workspace.
- **Verification**: Re-run command executed successfully and `audit.py` was created.

### Example 2: PowerShell Backslash Escaping in Inline Python Commands
- **Symptom**: Executing `python -c "from retriever import SimpleTFIDFRetriever; ... print(f'{res[\"normalized_facet\"]}') ..."` returned:
  `SyntaxError: f-string expression part cannot include a backslash`
- **Diagnosis & Root Cause**: When attempting to escape double quotes inside a PowerShell string for an inline python command, the backslash was passed literally to Python, causing an invalid f-string backslash syntax error inside Python.
- **Fix**: Changed the quotes to use single quotes inside the double quotes (`res['normalized_facet']`) to avoid needing any backslashes in the inline code.
- **Verification**: The command executed successfully and printed retrieved facets.
