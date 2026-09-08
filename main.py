import json
import os
import duckdb
import gradio as gr
from fastapi import FastAPI, Query, Response

# ── Config ──────────────────────────────────────────────────────────────
app = FastAPI(title="850MindData API")

# Base URL for all Parquet files
BASE_URL = "https://huggingface.co/buckets/bronx-ultra/850MindData-bucket/resolve/main/data"

# Generate all 853 file URLs (Hi-Tek_Part_000.parquet to Hi-Tek_Part_852.parquet)
REMOTE_PARTS = [f"{BASE_URL}/Hi-Tek_Part_{i:03d}.parquet" for i in range(853)]

# ── DuckDB Connection ──────────────────────────────────────────────────
def get_conn():
    con = duckdb.connect()
    con.execute("SET home_directory='/tmp'")
    con.execute("SET extension_directory='/tmp/duckdb_extensions'")
    con.execute("INSTALL parquet; LOAD parquet;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET threads = 2")
    
    # Read ALL 853 files (ICMR style)
    part_list = ", ".join([f"'{url}'" for url in REMOTE_PARTS])
    con.execute(f"""
        CREATE OR REPLACE VIEW data_850 AS 
        SELECT * FROM read_parquet([{part_list}])
    """)
    return con

# ── Search Function ──────────────────────────────────────────────────
def search_data(q: str, limit: int = 10):
    q = q.strip()
    if not q:
        return {"query": q, "count": 0, "results": []}
    
    con = get_conn()
    
    # Get columns
    try:
        sample = con.execute("SELECT * FROM data_850 LIMIT 1").fetchall()
        if not sample:
            return {"query": q, "count": 0, "results": [], "error": "No data"}
        columns = [d[0] for d in con.description]
    except Exception as e:
        return {"query": q, "count": 0, "results": [], "error": str(e)}
    
    # Search in all columns
    conditions = []
    for col in columns:
        conditions.append(f"{col} ILIKE '%{q}%'")
    sql = f"SELECT * FROM data_850 WHERE {' OR '.join(conditions)} LIMIT {limit + 5}"
    
    try:
        rows = con.execute(sql).fetchall()
        if rows:
            cols = [d[0] for d in con.description]
            results = [dict(zip(cols, r)) for r in rows][:limit]
            return {"query": q, "count": len(results), "results": results}
        else:
            return {"query": q, "count": 0, "results": []}
    except Exception as e:
        return {"query": q, "count": 0, "results": [], "error": str(e)}

# ── FastAPI ──────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": "850MindData API",
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel",
        "total_files": 853,
        "total_size": "77.1 GB",
        "status": "active"
    }

@app.get("/search")
async def search(q: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    data = search_data(q, limit)
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json"
    )

# ── Gradio UI ──────────────────────────────────────────────────────
def search_ui(query, limit):
    if not query:
        return "⚠️ Kuch search karo!"
    data = search_data(query, int(limit))
    if "error" in data:
        return f"❌ Error: {data['error']}"
    if not data.get("results"):
        return f"❌ No results for: **{query}**"
    
    out = f"🔍 **{query}** - {data['count']} results\n\n"
    for i, row in enumerate(data["results"], 1):
        out += f"**Result {i}:**\n"
        for key, value in row.items():
            if value:
                out += f"  - **{key}:** {value}\n"
        out += "\n"
    return out

demo = gr.Interface(
    fn=search_ui,
    inputs=[
        gr.Textbox(label="🔍 Search", placeholder="Name, mobile, email..."),
        gr.Slider(1, 50, value=10, step=1, label="Max Results")
    ],
    outputs=gr.Markdown(),
    title="📡 850MindData API (853 Files)",
    description="Search **77.1 GB dataset** — 853 files | Built by @SOCIALBANNERR"
)

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
