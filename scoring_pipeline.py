import json
import re
from retriever import SimpleTFIDFRetriever
from local_llm import LocalLLMWrapper

SYSTEM_PROMPT = """You are a highly precise conversational analyst. Your task is to evaluate the provided conversation text against a list of psychological or communication facets.

For each facet, you must decide if there is conversational evidence to score it.
- If there is sufficient evidence, set status to "scored", choose an integer score from 1 to 5, set confidence from 0.0 to 1.0, and write a short sentence of evidence.
- If there is insufficient evidence or the facet is not applicable, set status to "insufficient_evidence", set score to null, set confidence, and explain why there is no evidence.

Score Scale:
1: Very Low (Trait is absent or completely opposite)
2: Low (Trait is rarely or weakly shown)
3: Moderate (Trait is moderately present or balanced)
4: High (Trait is clearly and frequently shown)
5: Very High (Trait is extremely pronounced or dominant)

You MUST respond ONLY with a valid JSON object matching this schema:
{
  "scores": [
    {
      "facet": "<Normalized Facet Name>",
      "status": "scored" | "insufficient_evidence",
      "score": 1 | 2 | 3 | 4 | 5 | null,
      "confidence": <float between 0.0 and 1.0>,
      "evidence": "<short reason or direct quote from the conversation>"
    }
  ]
}
Do not include any pre-text, post-text, or markdown formatting blocks (like ```json). Respond with the raw JSON string."""

class ScoringPipeline:
    def __init__(self, facets_csv_path="enriched_facets.csv", model_id="Qwen/Qwen2.5-0.5B-Instruct", device=None, lazy_llm=True):
        self.retriever = SimpleTFIDFRetriever(facets_csv_path)
        self.model_id = model_id
        self.device = device
        self.llm = None
        
        # If not lazy loading, initialize the LLM immediately
        if not lazy_llm:
            self._init_llm()

    def _init_llm(self):
        if self.llm is None:
            self.llm = LocalLLMWrapper(model_id=self.model_id, device=self.device)

    def clean_json_string(self, text):
        """Clean markdown blocks or wrapping from JSON string."""
        text = text.strip()
        # Remove ```json ... ``` or ``` ... ```
        text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return text.strip()

    def parse_scores_robustly(self, raw_output, requested_facets):
        """Parse LLM output as JSON, with regex-based fallbacks if it is malformed."""
        cleaned = self.clean_json_string(raw_output)
        
        # Try standard JSON parsing
        try:
            data = json.loads(cleaned)
            if "scores" in data and isinstance(data["scores"], list):
                # Build lookup to verify all requested facets are present
                parsed_scores = {item["facet"].lower(): item for item in data["scores"] if "facet" in item}
                
                results = []
                for f in requested_facets:
                    name = f["normalized_facet"]
                    if name.lower() in parsed_scores:
                        item = parsed_scores[name.lower()]
                        results.append({
                            "facet": name,
                            "status": item.get("status", "insufficient_evidence"),
                            "score": item.get("score"),
                            "confidence": item.get("confidence", 0.5),
                            "evidence": item.get("evidence", "No evidence provided.")
                        })
                    else:
                        # Fallback for missing facet in JSON
                        results.append({
                            "facet": name,
                            "status": "insufficient_evidence",
                            "score": None,
                            "confidence": 0.0,
                            "evidence": "Facet was not scored by the model."
                        })
                return results
        except Exception as e:
            print(f"Standard JSON parsing failed: {e}. Attempting regex fallback...")

        # Regex fallback parser
        results = []
        for f in requested_facets:
            name = f["normalized_facet"]
            # Look for block containing the facet name
            # Pattern matches: "facet": "<name>", ... "score": <num/null>, ... "status": "<status>", ... "confidence": <num>, ... "evidence": "<text>"
            pattern = rf'{{\s*"facet"\s*:\s*"{re.escape(name)}".*?}}'
            match = re.search(pattern, cleaned, re.DOTALL | re.IGNORECASE)
            
            if match:
                block = match.group(0)
                # Extract fields
                status_match = re.search(r'"status"\s*:\s*"([^"]+)"', block)
                score_match = re.search(r'"score"\s*:\s*(null|\d)', block)
                confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', block)
                evidence_match = re.search(r'"evidence"\s*:\s*"([^"]*)"', block)
                
                status = status_match.group(1) if status_match else "insufficient_evidence"
                score_val = score_match.group(1) if score_match else "null"
                score = int(score_val) if score_val.isdigit() else None
                confidence = float(confidence_match.group(1)) if confidence_match else 0.5
                evidence = evidence_match.group(1) if evidence_match else "Extracted via regex fallback."
                
                results.append({
                    "facet": name,
                    "status": status,
                    "score": score,
                    "confidence": confidence,
                    "evidence": evidence
                })
            else:
                # Default abstention for failed regex
                results.append({
                    "facet": name,
                    "status": "insufficient_evidence",
                    "score": None,
                    "confidence": 0.0,
                    "evidence": "Failed to parse model output for this facet."
                })
        return results

    def score_conversation(self, conversation_text, k=15):
        """Full pipeline: Retrieve Top-K, filter observable vs non-observable, score observable."""
        # Ensure LLM is loaded
        self._init_llm()

        # 1. Retrieve Top-K facets
        retrieved_facets = self.retriever.retrieve(conversation_text, k=k)
        
        observable_to_score = []
        final_results = {}

        # 2. Split and handle non-observable facets immediately
        for facet in retrieved_facets:
            name = facet["normalized_facet"]
            is_observable = facet["conversation_observable"] == "True"
            
            if not is_observable:
                # Immediate abstention
                final_results[name] = {
                    "facet": name,
                    "category": facet["category"],
                    "conversation_observable": False,
                    "status": "not_observable",
                    "score": None,
                    "confidence": 1.0,
                    "evidence": facet["abstention_reason"]
                }
            else:
                observable_to_score.append(facet)

        # 3. Score observable facets in batches
        if observable_to_score:
            # Construct user prompt
            facets_str = ""
            for idx, f in enumerate(observable_to_score):
                facets_str += f"{idx+1}. Facet: {f['normalized_facet']}\n   Definition: {f['scoring_definition']}\n\n"
                
            prompt = f"""Conversation to analyze:
\"\"\"
{conversation_text}
\"\"\"

Facets to evaluate:
{facets_str}
Evaluate each of these facets and produce the JSON output:"""
            
            try:
                # Call LLM
                raw_response = self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=1024)
                
                # Parse scores robustly
                parsed_scores = self.parse_scores_robustly(raw_response, observable_to_score)
                
                # Populate final results
                for idx, score_data in enumerate(parsed_scores):
                    name = score_data["facet"]
                    orig_facet = observable_to_score[idx]
                    
                    final_results[name] = {
                        "facet": name,
                        "category": orig_facet["category"],
                        "conversation_observable": True,
                        "status": score_data["status"],
                        "score": score_data["score"],
                        "confidence": score_data["confidence"],
                        "evidence": score_data["evidence"]
                    }
            except Exception as e:
                print(f"Error during LLM generation or parsing: {e}")
                # Fallback: Abstain from all observable facets in this batch
                for f in observable_to_score:
                    name = f["normalized_facet"]
                    final_results[name] = {
                        "facet": name,
                        "category": f["category"],
                        "conversation_observable": True,
                        "status": "insufficient_evidence",
                        "score": None,
                        "confidence": 0.0,
                        "evidence": f"Scoring engine encountered an error: {str(e)}"
                    }

        # Keep original retrieval order for final list
        ordered_results = []
        for facet in retrieved_facets:
            name = facet["normalized_facet"]
            if name in final_results:
                ordered_results.append(final_results[name])
                
        return ordered_results

    def score_specific_facets(self, conversation_text, facet_names):
        """Evaluate a conversation specifically for a list of facet names."""
        # Ensure LLM is loaded
        self._init_llm()
        
        # Build lookups from retriever facets
        facets_by_name = {f["normalized_facet"].lower(): f for f in self.retriever.facets}
        
        selected_facets = []
        final_results = {}
        
        for name in facet_names:
            name_lower = name.lower()
            if name_lower in facets_by_name:
                facet = facets_by_name[name_lower]
                is_observable = facet["conversation_observable"] == "True"
                
                if not is_observable:
                    final_results[facet["normalized_facet"]] = {
                        "facet": facet["normalized_facet"],
                        "category": facet["category"],
                        "conversation_observable": False,
                        "status": "not_observable",
                        "score": None,
                        "confidence": 1.0,
                        "evidence": facet["abstention_reason"]
                    }
                else:
                    selected_facets.append(facet)
            else:
                # Facet not in taxonomy
                final_results[name] = {
                    "facet": name,
                    "category": "Unknown",
                    "conversation_observable": False,
                    "status": "not_observable",
                    "score": None,
                    "confidence": 0.0,
                    "evidence": "Facet not found in taxonomy."
                }
                
        # Score observable
        if selected_facets:
            # Construct user prompt
            facets_str = ""
            for idx, f in enumerate(selected_facets):
                facets_str += f"{idx+1}. Facet: {f['normalized_facet']}\n   Definition: {f['scoring_definition']}\n\n"
                
            prompt = f"""Conversation to analyze:
\"\"\"
{conversation_text}
\"\"\"

Facets to evaluate:
{facets_str}
Evaluate each of these facets and produce the JSON output:"""
            
            try:
                raw_response = self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=1024)
                parsed_scores = self.parse_scores_robustly(raw_response, selected_facets)
                
                for idx, score_data in enumerate(parsed_scores):
                    name = score_data["facet"]
                    orig_facet = selected_facets[idx]
                    
                    final_results[name] = {
                        "facet": name,
                        "category": orig_facet["category"],
                        "conversation_observable": True,
                        "status": score_data["status"],
                        "score": score_data["score"],
                        "confidence": score_data["confidence"],
                        "evidence": score_data["evidence"]
                    }
            except Exception as e:
                print(f"Error during LLM generation/parsing: {e}")
                for f in selected_facets:
                    name = f["normalized_facet"]
                    final_results[name] = {
                        "facet": name,
                        "category": f["category"],
                        "conversation_observable": True,
                        "status": "insufficient_evidence",
                        "score": None,
                        "confidence": 0.0,
                        "evidence": f"Scoring engine error: {str(e)}"
                    }
                    
        # Return results in the requested order
        return [final_results[name] for name in facet_names if name in final_results]

if __name__ == "__main__":
    # Test pipeline (will download model if it's the first run)
    try:
        pipeline = ScoringPipeline(lazy_llm=False)
        test_text = "I am extremely angry about this service! You guys have been delaying my project for weeks."
        print("\nRunning Scoring Pipeline Test...")
        results = pipeline.score_conversation(test_text, k=5)
        print("\nPipeline Results:")
        for r in results:
            print(f"Facet: {r['facet']}")
            print(f"  Category: {r['category']}")
            print(f"  Observable: {r['conversation_observable']}")
            print(f"  Status: {r['status']}")
            print(f"  Score: {r['score']}")
            print(f"  Confidence: {r['confidence']}")
            print(f"  Evidence/Reason: {r['evidence']}")
            print("-" * 40)
    except Exception as e:
        print("Pipeline test skipped (model/libraries not fully installed yet):", str(e))
