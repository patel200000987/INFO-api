import json
import httpx
from fastapi import FastAPI, Query, Response
import gradio as gr

# ── Config ──────────────────────────────────────────────────────────────
app = FastAPI(title="850MindData API")

# Hugging Face Datasets Server API
HF_API = "https://datasets-server.huggingface.co/rows"
DATASET = "bronx-ultra/850MindData-bucket"
CONFIG = "default"
SPLIT = "train"

# ── Search Function ────────────────────────────────────────────────────
def search_hf(q: str, limit: int = 10):
    """Search using Hugging Face Datasets Server API"""
    q = q.strip().lower()
    if not q:
        return {"query": q, "count": 0, "results": []}
    
    try:
        results = []
        offset = 0
        
        # Scan pages until we have enough results
        while len(results) < limit and offset < 1000:
            resp = httpx.get(
                HF_API,
                params={
                    "dataset": DATASET,
                    "config": CONFIG,
                    "split": SPLIT,
                    "offset": offset,
                    "length": 100
                },
                timeout=30
            )
            
            if resp.status_code != 200:
                break
                
            data = resp.json()
            rows = data.get("rows", [])
            
            if not rows:
                break
            
            # Check each row for the query
            for row in rows:
                row_data = row.get("row", {})
                # Search in all fields
                search_str = json.dumps(row_data).lower()
                if q in search_str:
                    results.append(row_data)
                    if len(results) >= limit:
                        break
            
            offset += 100
            if data.get("partial", False):
                break
        
        return {
            "query": q,
            "count": len(results),
            "results": results[:limit]
        }
        
    except Exception as e:
        return {
            "query": q,
            "count": 0,
            "results": [],
            "error": str(e)
        }

# ── FastAPI Endpoints ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": "850MindData API",
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel",
        "dataset": DATASET,
        "status": "active",
        "method": "Hugging Face API Proxy"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
async def search(
    q: str = Query(..., description="Search query (name, mobile, email, etc.)"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
):
    data = search_hf(q, limit)
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json"
    )

# ── Gradio UI ──────────────────────────────────────────────────────────
def search_ui(query, limit):
    if not query:
        return "⚠️ Kuch search karo!"
    
    data = search_hf(query, int(limit))
    
    if "error" in data:
        return f"❌ Error: {data['error']}"
    
    if not data.get("results"):
        return f"🔍 **{query}**\n\n❌ No results found"
    
    out = f"🔍 **{query}** - {data['count']} results\n\n"
    
    for i, row in enumerate(data["results"], 1):
        out += f"**Result {i}:**\n"
        for key, value in row.items():
            if value:
                out += f"  - **{key}:** {value}\n"
        out += "\n"
    
    return out

# ── Gradio Interface ──────────────────────────────────────────────────
demo = gr.Interface(
    fn=search_ui,
    inputs=[
        gr.Textbox(
            label="🔍 Search",
            placeholder="Name, mobile, email, address...",
            lines=1
        ),
        gr.Slider(
            minimum=1,
            maximum=50,
            value=10,
            step=1,
            label="Max Results"
        )
    ],
    outputs=gr.Markdown(),
    title="📡 850MindData Search API",
    description="Search 77.1 GB dataset (853 files) | Built by @SOCIALBANNERR"
)

# ── Mount Gradio on FastAPI ────────────────────────────────────────────
app = gr.mount_gradio_app(app, demo, path="/")

# ── Run ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
