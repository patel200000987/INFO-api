import json
import os
import httpx
from fastapi import FastAPI, Query, Response
import gradio as gr

# ── Config ──────────────────────────────────────────────────────────────
app = FastAPI(title="Indian Database Search API")

# Hugging Face Datasets Server API (Proxy)
HF_API = "https://datasets-server.huggingface.co/rows"
DATASET = "sauravsingh2111/Inddatainonefile"

# ── Search Function ────────────────────────────────────────────────────
def search_hf(q: str, limit: int = 10):
    """Search in name, mobile, email fields using HF API"""
    q = q.strip().lower()
    if not q:
        return {"query": q, "count": 0, "results": []}
    
    try:
        results = []
        offset = 0
        
        # Scan up to 1000 rows (adjustable)
        while len(results) < limit and offset < 1000:
            resp = httpx.get(
                HF_API,
                params={
                    "dataset": DATASET,
                    "config": "default",
                    "split": "train",
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
                
            # Filter rows where q matches name, mobile, or email
            for row in rows:
                row_data = row.get("row", {})
                # Check in name, mobile, email only
                name = (row_data.get("name") or "").lower()
                mobile = (row_data.get("mobile") or "").lower()
                email = (row_data.get("email") or "").lower()
                
                if q in name or q in mobile or q in email:
                    # Return only required fields
                    filtered = {
                        "name": row_data.get("name", ""),
                        "mobile": row_data.get("mobile", ""),
                        "email": row_data.get("email", "")
                    }
                    results.append(filtered)
                    if len(results) >= limit:
                        break
            
            offset += 100
            if data.get("partial", False):
                break
                
        return {
            "query": q,
            "count": len(results),
            "results": results[:limit],
            "source": "HF Proxy"
        }
    except Exception as e:
        return {"query": q, "count": 0, "results": [], "error": str(e)}

# ── FastAPI Endpoints ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": "Indian Database Search API",
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel",
        "dataset": DATASET,
        "method": "Hugging Face Datasets Server API",
        "search_fields": ["name", "mobile", "email"],
        "status": "active"
    }

@app.get("/health")
def health():
    return {"status": "ok", "api": "HF Proxy", "developer": "@SOCIALBANNERR"}

@app.get("/search")
async def search(
    q: str = Query(..., description="Search query (name, mobile, or email)"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
):
    data = search_hf(q, limit)
    return Response(
        content=json.dumps(data, indent=2),
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
        return f"❌ No results for: **{query}**"
    
    out = f"🔍 **{query}** - {data['count']} results\n\n"
    for i, row in enumerate(data["results"], 1):
        fields = []
        if row.get("name"):
            fields.append(f"Name: {row['name']}")
        if row.get("mobile"):
            fields.append(f"Mobile: {row['mobile']}")
        if row.get("email"):
            fields.append(f"Email: {row['email']}")
        out += f"**{i}.** " + ", ".join(fields) + "\n\n"
    return out

demo = gr.Interface(
    fn=search_ui,
    inputs=[
        gr.Textbox(label="🔍 Search", placeholder="Name, mobile, or email..."),
        gr.Slider(1, 50, value=10, step=1, label="Max Results")
    ],
    outputs=gr.Markdown(),
    title="📡 Indian Database Search API",
    description="Search **1.78 billion records** — Name, Mobile, Email | Built by @SOCIALBANNERR"
)

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
