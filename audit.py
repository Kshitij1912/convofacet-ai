import csv
import re
import os

def normalize_facet(facet):
    """Clean and normalize a facet name."""
    cleaned = facet.strip()
    # Remove leading numbers and dots (e.g., '800. Sufi practice: ...' -> 'Sufi practice: ...')
    cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
    # Remove trailing colons
    cleaned = re.sub(r':$', '', cleaned)
    # Normalize double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def classify_facet(raw_name, normalized_name):
    """Classify facet into taxonomy and determine observability and sensitivity."""
    # 1. Malformed / Header check
    if raw_name.endswith(':'):
        return {
            "category": "Malformed/Header",
            "conversation_observable": False,
            "sensitivity": "Low",
            "abstention_reason": "Header or structural category marker, not a concrete facet."
        }
    
    normalized_lower = normalized_name.lower()
    
    # 2. Spiritual / Cultural check
    spiritual_keywords = [
        'spirit', 'relig', 'quran', 'bible', 'torah', 'buddha', 'zen', 'meditat', 
        'mantra', 'yoga', 'kabal', 'kabbalah', 'hindu', 'islam', 'muslim', 'church', 
        'sikh', 'reiki', 'astrology', 'scorpio', 'horoscope', 'gnostic', 'archon', 
        'sephira', 'tiferet', 'sufi', 'kirtan', 'shabbat', 'seerah', 'zohar', 'vrata', 
        'ridván', 'iching', 'i ching', 'hexagram', 'holiness', 'dhikr', 'khatam', 'pilgrimage'
    ]
    if any(kw in normalized_lower for kw in spiritual_keywords) or re.match(r'^\d+\.', raw_name):
        # Even if they talk about spirituality, tracking specific quantitative counts or indices (e.g., 'Quran khatam cycles per year')
        # requires biographical history or external logs, hence not directly observable.
        is_observable = False
        abstention_reason = "Spiritual metrics and practice counts require biographical history or external logs."
        if "virtue" in normalized_lower or "adherence" in normalized_lower or "compassion" in normalized_lower:
            # Trait-like spiritual values could conceptually be observed if discussed
            is_observable = True
            abstention_reason = ""
            
        return {
            "category": "Spiritual/Cultural",
            "conversation_observable": is_observable,
            "sensitivity": "Medium",
            "abstention_reason": abstention_reason
        }
        
    # 3. Medical / Physiological check
    medical_keywords = [
        'fsh', 'basophil', 'hormone', 'blood', 'serotonin', 'chromatin', 'apnea', 
        'pain', 'metabolic', 'immune', 'cardiovascular', 'disease', 'gene', 
        'diagnostic', 'clinical', 'depression', 'burnout', 'sleep-disorder', 
        'hypomania', 'hysteria', 'psychoticism', 'neuroticism'
    ]
    # Note: Neuroticism is a Big Five trait, but let's see. If it is Neuroticism itself, it is observable as personality.
    if any(kw in normalized_lower for kw in medical_keywords):
        if normalized_lower == "neuroticism":
            return {
                "category": "Personality/Cognitive",
                "conversation_observable": True,
                "sensitivity": "Low",
                "abstention_reason": ""
            }
        return {
            "category": "Medical/Physiological",
            "conversation_observable": False,
            "sensitivity": "High",
            "abstention_reason": "Requires physiological testing, laboratory analysis, or clinical diagnostic tools not available in conversation."
        }

    # 4. Biographical / External check
    biographical_keywords = [
        'years', 'months', 'count', 'frequency', 'km/week', 'usage', 'subscriber', 
        'contributions', 'trips', 'visits', 'commute', 'temperature', 'presence', 
        'food sourcing', 'dietary', 'habits', 'snacking', 'breakfast', 'caffeine intake', 
        'home-security', 'passport-stamps', 'volunteer', 'choir', 'nomad', 'museum', 
        'travel-companions', 'soft-skill training hours', 'hours/week', 'rate', 'history',
        'consent level', 'check frequency', 'exposure', 'learning style', 'subscription count'
    ]
    if any(kw in normalized_lower for kw in biographical_keywords):
        return {
            "category": "Biographical/External",
            "conversation_observable": False,
            "sensitivity": "Medium",
            "abstention_reason": "Requires access to objective external records, biographical history, or quantitative tracking outside the conversation."
        }
        
    # 5. Default to Personality/Cognitive/Communication (Observable)
    return {
        "category": "Personality/Cognitive",
        "conversation_observable": True,
        "sensitivity": "Low",
        "abstention_reason": ""
    }

def get_scoring_definition(normalized_name, is_observable):
    """Generate a placeholder/rule-based scoring definition for observable facets."""
    if not is_observable:
        return "N/A - Non-observable in conversation."
        
    name = normalized_name.lower()
    if 'talk' in name or 'brevity' in name:
        return "Scores from 1 (very brief/quiet) to 5 (extremely talkative/elaborative) based on sentence length and text volume."
    elif 'sarcasm' in name or 'quirk' in name:
        return "Scores from 1 (very literal/conventional) to 5 (highly sarcastic, quirky, or eccentric language)."
    elif 'anger' in name or 'hostility' in name or 'disagree' in name:
        return "Scores from 1 (exceptionally polite/calm) to 5 (highly argumentative, hostile, or angry tone)."
    elif 'sad' in name or 'sadness' in name or 'depression' in name:
        return "Scores from 1 (cheerful/optimistic) to 5 (expressing severe sadness, hopelessness, or low mood)."
    else:
        return f"Measures the degree of '{normalized_name}' expressed in the conversational style, word choice, or self-reported statements. Scale: 1 (Very Low/Absent) to 5 (Very High/Dominant)."

def run_audit(input_path, output_path):
    print(f"Starting audit of: {input_path}")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    facets = []
    with open(input_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader) # Read header
        for row in reader:
            if not row:
                continue
            raw_facet = row[0]
            if not raw_facet.strip():
                continue
            facets.append(raw_facet)
            
    print(f"Loaded {len(facets)} facets. Processing...")
    
    enriched_rows = []
    malformed_count = 0
    observable_count = 0
    non_observable_count = 0
    
    for raw_facet in facets:
        normalized = normalize_facet(raw_facet)
        classification = classify_facet(raw_facet, normalized)
        
        # Add scoring definition
        scoring_def = get_scoring_definition(normalized, classification["conversation_observable"])
        
        row_data = {
            "raw_facet": raw_facet,
            "normalized_facet": normalized,
            "category": classification["category"],
            "conversation_observable": str(classification["conversation_observable"]),
            "sensitivity": classification["sensitivity"],
            "scoring_definition": scoring_def,
            "abstention_reason": classification["abstention_reason"]
        }
        
        enriched_rows.append(row_data)
        
        # Statistics
        if classification["category"] == "Malformed/Header":
            malformed_count += 1
        if classification["conversation_observable"]:
            observable_count += 1
        else:
            non_observable_count += 1
            
    # Write output CSV
    fieldnames = ["raw_facet", "normalized_facet", "category", "conversation_observable", "sensitivity", "scoring_definition", "abstention_reason"]
    with open(output_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)
        
    print(f"Audit completed successfully!")
    print(f"Enriched facets written to: {output_path}")
    print(f"Total facets: {len(enriched_rows)}")
    print(f"  - Malformed/Headers detected: {malformed_count}")
    print(f"  - Conversation-Observable: {observable_count}")
    print(f"  - Non-Observable (requires external evidence): {non_observable_count}")
    
if __name__ == "__main__":
    run_audit("Facets Assignment.csv", "enriched_facets.csv")
