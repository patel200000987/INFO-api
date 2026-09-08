import json
import os
import httpx
from fastapi import FastAPI, Query, Response
import gradio as gr

# ── Config ──────────────────────────────────────────────────────────────
app = FastAPI(title="Telegram Search API")

# Hugging Face Datasets Server API (Proxy)
HF_API = "https://datasets-server.huggingface.co/rows"
DATASET = "Kzr0xx/telegram"

# ── Search Function ────────────────────────────────────────────────────
def search_hf(q: str, limit: int = 10):
    """Search in username and user_id fields using HF API"""
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
                
            # Filter rows where q matches username or user_id
            for row in rows:
                row_data = row.get("row", {})
                # Check in username and user_id only
                username = (row_data.get("username") or "").lower()
                user_id = str(row_data.get("user_id") or "").lower()
                
                if q in username or q in user_id:
                    # Return only required fields
                    filtered = {
                        "tgusername": row_data.get("username", ""),
                        "tgid": row_data.get("user_id", "")
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
            "results": results[:limit]
            # "source" removed — hidden
        }
    except Exception as e:
        return {"query": q, "count": 0, "results": [], "error": str(e)}

# ── FastAPI Endpoints ──────────────────────────────────────────────────
@app.get("/")
def root():
    # Sirf app, developer, channel
    return {
        "app": "Telegram Search API",
        "developer": "╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀",
        "credit": "@SOCIALBANNERR"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
async def search(
    q: str = Query(..., description="Search query (username or user_id)"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
):
    data = search_hf(q, limit)
    # Add "New Api By Patel" at the end
    data["footer"] = "New Api By Patel"
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
        return f"❌ No results for: **{query}**"
    
    out = f"🔍 **{query}** - {data['count']} results\n\n"
    for i, row in enumerate(data["results"], 1):
        out += f"**Result {i}:**\n"
        out += f"  - **Username:** {row.get('tgusername', 'N/A')}\n"
        out += f"  - **User ID:** {row.get('tgid', 'N/A')}\n\n"
    out += "\n---\n**New Api By Patel**"
    return out

demo = gr.Interface(
    fn=search_ui,
    inputs=[
        gr.Textbox(label="🔍 Search", placeholder="Username or User ID..."),
        gr.Slider(1, 50, value=10, step=1, label="Max Results")
    ],
    outputs=gr.Markdown(),
    title="📡 Telegram Search API",
    description="Search **429 million records** — Username, User ID | Built by ╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀"
)

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
