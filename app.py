from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import csv
from scoring_pipeline import ScoringPipeline

app = FastAPI(title="ConvoFacet AI - Diagnostic & Hallucination-Free Scoring Engine")

# Lazy scoring pipeline
pipeline = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        # Load the pipeline using the default Qwen 0.5B model on GPU/CPU
        pipeline = ScoringPipeline(model_id="Qwen/Qwen2.5-0.5B-Instruct", lazy_llm=False)
    return pipeline

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Dashboard HTML not found in templates/index.html</h1>", status_code=404)

@app.post("/api/analyze")
async def analyze_text(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        k = int(data.get("k", 15))
        
        if not text:
            return JSONResponse(content={"error": "Text cannot be empty"}, status_code=400)
            
        print(f"Web Request: Analyzing conversation turn ({len(text)} chars, k={k})...")
        pipe = get_pipeline()
        results = pipe.score_conversation(text, k=k)
        
        return JSONResponse(content={"results": results})
    except Exception as e:
        print(f"Error in web analyze endpoint: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/stats")
async def get_stats():
    """Return database stats for the dashboard counters and charts."""
    csv_path = "enriched_facets.csv"
    if not os.path.exists(csv_path):
        return JSONResponse(content={"error": "Facets database not found. Please run audit.py first."}, status_code=404)
        
    total = 0
    malformed = 0
    observable = 0
    non_observable = 0
    categories = {}
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            cat = row["category"]
            categories[cat] = categories.get(cat, 0) + 1
            
            if cat == "Malformed/Header":
                malformed += 1
            if row["conversation_observable"] == "True":
                observable += 1
            else:
                non_observable += 1
                
    return JSONResponse(content={
        "total_facets": total,
        "observable": observable,
        "non_observable": non_observable,
        "malformed": malformed,
        "categories": categories
    })

if __name__ == "__main__":
    import uvicorn
    # Start web server on localhost port 8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
