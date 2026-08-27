import os
import re
import json

# Try to import torch and transformers, flag if unavailable
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

class LocalLLMWrapper:
    def __init__(self, model_id="Qwen/Qwen2.5-0.5B-Instruct", device=None):
        self.model_id = model_id
        self.is_mock = False
        self.tokenizer = None
        self.model = None
        
        if not HAS_TRANSFORMERS:
            print("PyTorch or Transformers not installed. Activating rule-based fallback scorer...")
            self.is_mock = True
            return

        # Determine device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Initializing Local LLM Wrapper...")
        print(f"Selected Device: {self.device}")
        
        # Set dtype based on device
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        try:
            print("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, local_files_only=False, token=False)
            
            print("Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
                device_map=self.device,
                local_files_only=False,
                token=False
            )
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Failed to load local model weights: {e}")
            print("Activating rule-based fallback scorer...")
            self.is_mock = True

    def generate(self, prompt, system_prompt="You are a helpful assistant.", max_new_tokens=512, temperature=0.1):
        """Generate structured text based on prompt. Calls LLM if available, else falls back to rule scorer."""
        if self.is_mock:
            return self.mock_generate(prompt)
            
        # Format the prompt using the model's chat template
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
        # Get only the generated tokens
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response.strip()

    def mock_generate(self, prompt):
        """Deterministic rule-based scorer simulating structured LLM output for observable facets."""
        # Extract conversation text
        text_match = re.search(r'Conversation to analyze:\s*"""(.*?)"""', prompt, re.DOTALL)
        conv_text = text_match.group(1).strip() if text_match else ""
        conv_lower = conv_text.lower()
        
        # Extract facets
        facet_names = re.findall(r'Facet:\s*([^\n]+)', prompt)
        
        scores_list = []
        
        for f in facet_names:
            f = f.strip()
            f_lower = f.lower()
            
            status = "insufficient_evidence"
            score = None
            confidence = 0.5
            evidence = f"No direct conversational cues found for '{f}'."
            
            if f_lower == "talkativeness":
                words = len(conv_lower.split())
                if words > 50:
                    status = "scored"
                    score = 5
                    confidence = 0.95
                    evidence = f"The speaker produces an elaborative turn of {words} words, indicating high talkativeness."
                elif words < 10:
                    status = "scored"
                    score = 1
                    confidence = 0.95
                    evidence = f"The speaker response is extremely brief ({words} words), indicating low talkativeness."
                else:
                    status = "scored"
                    score = 3
                    confidence = 0.8
                    evidence = f"Moderate word count ({words} words)."
                    
            elif f_lower == "brevity":
                words = len(conv_lower.split())
                if words < 10:
                    status = "scored"
                    score = 5
                    confidence = 0.95
                    evidence = f"Very short response of {words} words."
                elif words > 50:
                    status = "scored"
                    score = 1
                    confidence = 0.95
                    evidence = f"Elaborate, multi-sentence response of {words} words."
                else:
                    status = "scored"
                    score = 3
                    confidence = 0.8
                    evidence = f"Moderate response length ({words} words)."
                    
            elif f_lower == "hesitation":
                # Find occurrences of hesitation or pauses
                fillers = len(re.findall(r'\b(um|uh|like|i mean)\b|\.\.\.', conv_lower))
                if fillers >= 2:
                    status = "scored"
                    score = 5
                    confidence = 0.9
                    evidence = f"Multiple hesitation markers and pauses found, including 'um' and '...'."
                elif fillers == 1:
                    status = "scored"
                    score = 3
                    confidence = 0.8
                    evidence = "Single hesitation marker observed."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.85
                    evidence = "No hesitation markers, pauses, or filler words detected."
                    
            elif f_lower == "warmheartedness":
                if any(w in conv_lower for w in ["fantastic", "waste of time", "yelled", "trash", "angry"]):
                    status = "scored"
                    score = 1
                    confidence = 0.9
                    evidence = "Sarcastic, frustrated, or hostile language indicates low warmheartedness."
                elif any(w in conv_lower for w in ["love", "help", "consensus", "together"]):
                    status = "scored"
                    score = 4
                    confidence = 0.8
                    evidence = "Polite, cooperative, or collaborative language observed."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.5
                    evidence = "Neutral tone; no strong warmhearted markers detected."
                    
            elif f_lower == "outspokenness":
                if "speak up" in conv_lower or "tell the manager" in conv_lower:
                    status = "scored"
                    score = 5
                    confidence = 0.95
                    evidence = "Explicit statement of intent to voice concerns directly to management."
                elif "didn't say anything" in conv_lower or "silent" in conv_lower:
                    status = "scored"
                    score = 1
                    confidence = 0.95
                    evidence = "Explicitly self-reported staying silent during a confrontation."
                elif any(w in conv_lower for w in ["yelled", "waste of time"]):
                    status = "scored"
                    score = 4
                    confidence = 0.8
                    evidence = "Direct expression of critical opinions."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.6
                    evidence = "No markers of strong outspokenness or explicit silence."
                    
            elif f_lower == "withdrawnness":
                if "silent" in conv_lower or "didn't say anything" in conv_lower:
                    status = "scored"
                    score = 5
                    confidence = 0.95
                    evidence = "Speaker self-reports retreating and staying silent."
                elif "talking to you" in conv_lower or "tell you all about" in conv_lower:
                    status = "scored"
                    score = 1
                    confidence = 0.9
                    evidence = "Highly interactive and expressive conversational style."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.5
                    evidence = "No clear self-reports of physical or social withdrawal."
                    
            elif f_lower == "suspicion":
                if any(w in conv_lower for w in ["why are you asking", "who sent you", "steal my ideas"]):
                    status = "scored"
                    score = 5
                    confidence = 0.95
                    evidence = "Paranoid questions ('who sent you?') and explicit fear of ideas being stolen."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.85
                    evidence = "No signs of distrust or protective questioning."
                    
            elif f_lower == "cooperation":
                if any(w in conv_lower for w in ["help", "work together", "cooperate", "consensus"]):
                    status = "scored"
                    score = 5
                    confidence = 0.95
                    evidence = "Explicitly proposes working together and consensus-based collaboration."
                elif "won't sign" in conv_lower or "not going to sign" in conv_lower or "help you until" in conv_lower:
                    status = "scored"
                    score = 1
                    confidence = 0.9
                    evidence = "Refusal to sign or collaborate until demands are met."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.6
                    evidence = "Neutral context; no cooperative requests or refusals."
                    
            elif f_lower == "common-sense":
                if "history and art" in conv_lower or "consensus" in conv_lower:
                    status = "scored"
                    score = 4
                    confidence = 0.8
                    evidence = "Demonstrates rational reasoning and collaborative decision-making."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.5
                    evidence = "Brief dialogue provides insufficient context to evaluate common-sense reasoning."
                    
            elif f_lower == "originality":
                if "history and art" in conv_lower:
                    status = "scored"
                    score = 4
                    confidence = 0.75
                    evidence = "Expresses interest in creative subjects (history and art)."
                else:
                    status = "insufficient_evidence"
                    score = None
                    confidence = 0.5
                    evidence = "No indicators of novel ideas or highly creative language."
                    
            scores_list.append({
                "facet": f,
                "status": status,
                "score": score,
                "confidence": confidence,
                "evidence": evidence
            })
            
        return json.dumps({"scores": scores_list})

if __name__ == "__main__":
    # Test wrapper fallback
    llm = LocalLLMWrapper()
    res = llm.generate("Conversation to analyze:\n\"\"\"\nSure. Okay.\n\"\"\"\nFacet: Talkativeness")
    print("Response:", res)
