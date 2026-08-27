# Benchmark dataset for evaluating the scoring pipeline and proving hallucination mitigation.

REPRESENTATIVE_FACETS = [
    # Observable (10)
    {"normalized_facet": "Talkativeness", "conversation_observable": True},
    {"normalized_facet": "Brevity", "conversation_observable": True},
    {"normalized_facet": "Hesitation", "conversation_observable": True},
    {"normalized_facet": "Common-sense", "conversation_observable": True},
    {"normalized_facet": "Warmheartedness", "conversation_observable": True},
    {"normalized_facet": "Outspokenness", "conversation_observable": True},
    {"normalized_facet": "Withdrawnness", "conversation_observable": True},
    {"normalized_facet": "Suspicion", "conversation_observable": True},
    {"normalized_facet": "Cooperation", "conversation_observable": True},
    {"normalized_facet": "Originality", "conversation_observable": True},
    
    # Non-Observable / Trap Facets (10)
    {"normalized_facet": "FSH level", "conversation_observable": False},
    {"normalized_facet": "Parathyroid-hormone level", "conversation_observable": False},
    {"normalized_facet": "Sleep-disorder diagnosis", "conversation_observable": False},
    {"normalized_facet": "Passport-stamps count", "conversation_observable": False},
    {"normalized_facet": "Subscription count", "conversation_observable": False},
    {"normalized_facet": "Sleep-environment temperature", "conversation_observable": False},
    {"normalized_facet": "Volunteer Work", "conversation_observable": False},
    {"normalized_facet": "Chromatin-accessibility score", "conversation_observable": False},
    {"normalized_facet": "Democratic Leadership", "conversation_observable": False},
    {"normalized_facet": "HEXACO Personality Inventory Facets", "conversation_observable": False}
]

BENCHMARK_CONVERSATIONS = [
    {
        "id": 1,
        "archetype": "Clear Observable (Talkative)",
        "text": "Oh, hi! Yes, I'd love to tell you all about my day. It started at 6 AM, and then I went for a walk, and then I had this amazing coffee, and then I met this person, and we talked for hours about history and art, and then I came home and read a book, and then I decided to write a long letter to my sister, and now I'm here talking to you...",
        "reference_scores": {
            "Talkativeness": {"score": 5, "status": "scored"},
            "Brevity": {"score": 1, "status": "scored"}
        }
    },
    {
        "id": 2,
        "archetype": "Low Evidence / Brief",
        "text": "Sure. Okay.",
        "reference_scores": {
            "Brevity": {"score": 5, "status": "scored"},
            "Talkativeness": {"score": 1, "status": "scored"}
        }
    },
    {
        "id": 3,
        "archetype": "Sarcastic / Outspoken",
        "text": "Oh, fantastic. Another meeting that could have been an email. I just absolutely love sitting in a conference room for two hours doing nothing. It really makes me feel valued. Next time, I'm going to speak up and tell the manager exactly what a waste of time this is.",
        "reference_scores": {
            "Warmheartedness": {"score": 1, "status": "scored"},
            "Outspokenness": {"score": 5, "status": "scored"}
        }
    },
    {
        "id": 4,
        "archetype": "Contradictory / Hesitation",
        "text": "I mean... I guess I'm happy? Like, everything is totally fine, absolutely fine... um... but I don't know, it's just... sometimes I feel like crying for no reason. But really, I'm great! Don't worry about me.",
        "reference_scores": {
            "Hesitation": {"score": 5, "status": "scored"}
        }
    },
    {
        "id": 5,
        "archetype": "Code-switched / Cooperative",
        "text": "Hey, we need to finish this project by tomorrow. Por favor, ayúdame con las diapositivas while I write the report. Si trabajamos juntos, lo terminaremos a tiempo.",
        "reference_scores": {
            "Cooperation": {"score": 5, "status": "scored"}
        }
    },
    {
        "id": 6,
        "archetype": "Quoted Speech / Low Outspokenness",
        "text": "My boss literally yelled at me today in front of everyone. He said: 'You are completely incompetent and your work is trash!' I just stood there and didn't say anything. I went back to my desk and stayed silent.",
        "reference_scores": {
            "Outspokenness": {"score": 1, "status": "scored"},
            "Withdrawnness": {"score": 5, "status": "scored"}
        }
    },
    {
        "id": 7,
        "archetype": "Suspicion / Uncooperative",
        "text": "Why are you asking me all these questions? Who sent you? I'm not going to sign anything or help you until I see your credentials. I know people are trying to steal my ideas.",
        "reference_scores": {
            "Suspicion": {"score": 5, "status": "scored"},
            "Cooperation": {"score": 1, "status": "scored"}
        }
    },
    {
        "id": 8,
        "archetype": "Medical Hallucination Trap",
        "text": "I've been feeling so tired lately. I just can't seem to sleep well at night, and I wake up exhausted every single morning.",
        "reference_scores": {
            # Naive models might score Sleep Apnea or Sleep-disorder diagnosis. We expect abstention.
            "FSH level": {"score": None, "status": "not_observable"},
            "Sleep-disorder diagnosis": {"score": None, "status": "not_observable"}
        }
    },
    {
        "id": 9,
        "archetype": "Biographical Hallucination Trap",
        "text": "I love traveling so much. Last year I visited France and Japan, and next year I hope to go to Peru. Seeing new cultures is my passion.",
        "reference_scores": {
            # Naive models might score Passport-stamps count. We expect abstention.
            "Passport-stamps count": {"score": None, "status": "not_observable"},
            "Volunteer Work": {"score": None, "status": "not_observable"}
        }
    },
    {
        "id": 10,
        "archetype": "Internal State / Malformed Trap",
        "text": "I lead my team by listening to everyone's opinions and making decisions based on consensus. We work together democratically.",
        "reference_scores": {
            # Naive models might score chromatin accessibility or democratic leadership (which is a header). We expect abstention.
            "Chromatin-accessibility score": {"score": None, "status": "not_observable"},
            "Democratic Leadership": {"score": None, "status": "not_observable"}
        }
    }
]
