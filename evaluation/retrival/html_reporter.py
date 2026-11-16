import html
import json
from datetime import datetime
from pathlib import Path


def generate_html_report(results: list[dict], output_html_path: str):
    """Generates a self-contained, interactive Dark Theme HTML report from retrieval evaluation results."""
    total = len(results)
    passed = sum(1 for r in results if r["evaluation"]["is_supported"])
    failed = total - passed
    avg_score = sum(r["evaluation"]["score"] for r in results) / total if total else 0.0
    pass_rate = (passed / total * 100) if total else 0.0

    # Grab config from first record if available
    config = results[0].get("retrieval_config", {}) if results else {}
    strategy = config.get("strategy", "N/A")
    top_k = config.get("top_k", "N/A")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cards_html = []
    for r in results:
        eval_data = r["evaluation"]
        is_supported = eval_data["is_supported"]
        score = eval_data["score"]
        status_class = "pass" if is_supported else "fail"
        badge_text = "SUPPORTED" if is_supported else "UNSUPPORTED"

        # Escape HTML safely
        item_id = html.escape(str(r.get("id", "")))
        question = html.escape(str(r.get("question", "")))
        ground_truth = html.escape(str(r.get("ground_truth", "")))
        reason = html.escape(str(eval_data.get("reason", "")))

        # Format Missing Facts
        missing_facts = eval_data.get("missing_facts", [])
        if missing_facts:
            missing_items = "".join(f"<li>{html.escape(str(f))}</li>" for f in missing_facts)
            missing_section = f"""
            <div class="missing-box">
                <strong>⚠️ Missing Facts:</strong>
                <ul>{missing_items}</ul>
            </div>
            """
        else:
            missing_section = ""

        # Format Retrieved Chunks
        hits = r.get("retrieved_hits", [])
        if hits:
            chunks_list = []
            for idx, hit in enumerate(hits, start=1):
                chunk_text = html.escape(str(hit.get("text", "")))
                chunk_score = hit.get("score", "N/A")
                meta_str = html.escape(json.dumps(hit.get("metadata", {})))
                chunks_list.append(f"""
                <div class="chunk-item">
                    <div class="chunk-header">
                        <span class="chunk-rank">Rank #{idx}</span>
                        <span class="chunk-score">Score: {chunk_score}</span>
                        <span class="chunk-meta" title="{meta_str}">Metadata: {meta_str}</span>
                    </div>
                    <pre class="chunk-text">{chunk_text}</pre>
                </div>
                """)
            chunks_html = "".join(chunks_list)
        else:
            chunks_html = "<p class='empty-msg'>No chunks retrieved.</p>"

        cards_html.append(f"""
        <div class="card {status_class}" data-status="{status_class}">
            <div class="card-header">
                <div class="title-group">
                    <span class="item-id">{item_id}</span>
                    <span class="badge {status_class}">{badge_text}</span>
                </div>
                <div class="score-pill {'pill-ok' if is_supported else 'pill-bad'}">Score: {score} / 5</div>
            </div>

            <div class="question-box">
                <span class="label">Question</span>
                <p>{question}</p>
            </div>

            <div class="grid-2">
                <div class="panel gt-panel">
                    <span class="label">Ground Truth (Golden)</span>
                    <p class="gt-text">{ground_truth}</p>
                </div>
                <div class="panel reason-panel">
                    <span class="label">Judge Reasoning</span>
                    <p class="reason-text">{reason}</p>
                    {missing_section}
                </div>
            </div>

            <details {"open" if not is_supported else ""}>
                <summary>Retrieved Context ({len(hits)} chunks)</summary>
                <div class="chunks-container">
                    {chunks_html}
                </div>
            </details>
        </div>
        """)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RAG Retrieval Evaluation Report</title>
<style>
    :root {{
        --bg: #0b1120;
        --card-bg: #131c31;
        --panel-bg: #0f172a;
        --text: #f1f5f9;
        --muted: #94a3b8;
        --border: #26334d;
        --pass-bg: rgba(34, 197, 94, 0.15);
        --pass-text: #4ade80;
        --pass-border: #22c55e;
        --fail-bg: rgba(239, 68, 68, 0.15);
        --fail-text: #f87171;
        --fail-border: #ef4444;
        --accent: #3b82f6;
        --accent-hover: #60a5fa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: var(--bg);
        color: var(--text);
        margin: 0;
        padding: 2rem;
        line-height: 1.5;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
        padding-bottom: 1rem;
    }}
    h1 {{ margin: 0; font-size: 1.75rem; color: #ffffff; }}
    .meta-info {{ color: var(--muted); font-size: 0.9rem; }}
    .meta-info strong {{ color: #cbd5e1; }}
    
    /* Summary Dashboard */
    .summary-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    .stat-card {{
        background: var(--card-bg);
        padding: 1.25rem;
        border-radius: 10px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }}
    .stat-title {{ font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    .stat-value {{ font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; color: #ffffff; }}

    /* Filter Buttons */
    .filters {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }}
    .filter-btn {{
        padding: 0.5rem 1rem;
        border: 1px solid var(--border);
        background: var(--card-bg);
        border-radius: 6px;
        cursor: pointer;
        font-weight: 600;
        color: var(--muted);
        transition: all 0.15s ease;
    }}
    .filter-btn:hover {{ border-color: var(--accent); color: #ffffff; }}
    .filter-btn.active {{ background: var(--accent); color: #ffffff; border-color: var(--accent); }}

    /* Evaluation Cards */
    .card {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-left: 5px solid var(--border);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }}
    .card.pass {{ border-left-color: var(--pass-border); }}
    .card.fail {{ border-left-color: var(--fail-border); }}

    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }}
    .title-group {{ display: flex; align-items: center; gap: 0.75rem; }}
    .item-id {{ font-weight: 700; font-size: 1.1rem; color: #ffffff; }}
    .badge {{
        font-size: 0.72rem;
        font-weight: 700;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        letter-spacing: 0.03em;
    }}
    .badge.pass {{ background: var(--pass-bg); color: var(--pass-text); border: 1px solid rgba(34, 197, 94, 0.3); }}
    .badge.fail {{ background: var(--fail-bg); color: var(--fail-text); border: 1px solid rgba(239, 68, 68, 0.3); }}

    .score-pill {{
        font-size: 0.85rem;
        font-weight: 700;
        padding: 0.3rem 0.75rem;
        border-radius: 6px;
    }}
    .pill-ok {{ background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.25); }}
    .pill-bad {{ background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25); }}

    .label {{
        display: block;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--muted);
        margin-bottom: 0.35rem;
    }}
    .question-box {{
        background: var(--panel-bg);
        padding: 0.9rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
    }}
    .question-box p {{ margin: 0; font-weight: 600; color: #ffffff; }}

    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 1rem;
    }}
    @media (max-width: 768px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
    .panel {{
        background: var(--panel-bg);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--border);
    }}
    .gt-panel {{ background: var(--panel-bg); }}
    .reason-panel {{ background: rgba(59, 130, 246, 0.06); border-color: rgba(59, 130, 246, 0.25); }}
    .panel p {{ margin: 0; font-size: 0.95rem; color: #e2e8f0; white-space: pre-wrap; }}

    .missing-box {{
        margin-top: 0.75rem;
        padding: 0.75rem 0.9rem;
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 6px;
        font-size: 0.88rem;
        color: #fca5a5;
    }}
    .missing-box ul {{ margin: 0.35rem 0 0 1.2rem; padding: 0; }}

    /* Collapsible Chunks */
    details {{
        border-top: 1px solid var(--border);
        padding-top: 0.75rem;
    }}
    summary {{
        cursor: pointer;
        font-weight: 600;
        color: var(--accent-hover);
        user-select: none;
    }}
    summary:hover {{ text-decoration: underline; }}
    .chunks-container {{ margin-top: 0.75rem; display: flex; flex-direction: column; gap: 0.75rem; }}
    .chunk-item {{
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
        background: #090e1a;
    }}
    .chunk-header {{
        background: #18233c;
        padding: 0.45rem 0.75rem;
        font-size: 0.8rem;
        display: flex;
        gap: 1rem;
        border-bottom: 1px solid var(--border);
    }}
    .chunk-rank {{ font-weight: 700; color: #e2e8f0; }}
    .chunk-score {{ color: #38bdf8; font-weight: 600; }}
    .chunk-meta {{ color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .chunk-text {{
        margin: 0;
        padding: 0.85rem;
        white-space: pre-wrap;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.84rem;
        color: #cbd5e1;
        background: #090e1a;
    }}
    .empty-msg {{ color: var(--muted); font-style: italic; }}
</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>RAG Retrieval Evaluation Report</h1>
            <div class="meta-info">Strategy: <strong>{html.escape(str(strategy))}</strong> | Top-K: <strong>{html.escape(str(top_k))}</strong></div>
        </div>
        <div class="meta-info">Generated: {timestamp}</div>
    </header>

    <div class="summary-grid">
        <div class="stat-card">
            <div class="stat-title">Total Queries</div>
            <div class="stat-value">{total}</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Average Score</div>
            <div class="stat-value">{avg_score:.2f} / 5.0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Pass Rate</div>
            <div class="stat-value" style="color: {'#4ade80' if pass_rate >= 80 else '#f87171'};">{pass_rate:.1f}%</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Passed / Failed</div>
            <div class="stat-value">{passed} / {failed}</div>
        </div>
    </div>

    <div class="filters">
        <button class="filter-btn active" onclick="filterCards('all', this)">All ({total})</button>
        <button class="filter-btn" onclick="filterCards('pass', this)">Passed ({passed})</button>
        <button class="filter-btn" onclick="filterCards('fail', this)">Failed ({failed})</button>
    </div>

    <div id="cards-list">
        {"".join(cards_html)}
    </div>
</div>

<script>
function filterCards(status, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {{
        if (status === 'all' || card.dataset.status === status) {{
            card.style.display = 'block';
        }} else {{
            card.style.display = 'none';
        }}
    }});
}}
</script>
</body>
</html>
"""
    out_file = Path(output_html_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(full_html, encoding="utf-8")








































# with light theam

# import html
# import json
# from datetime import datetime
# from pathlib import Path


# def generate_html_report(results: list[dict], output_html_path: str):
#     """Generates a self-contained, interactive HTML report from evaluation results."""
#     total = len(results)
#     passed = sum(1 for r in results if r["evaluation"]["is_supported"])
#     failed = total - passed
#     avg_score = sum(r["evaluation"]["score"] for r in results) / total if total else 0.0
#     pass_rate = (passed / total * 100) if total else 0.0

#     # Grab config from first record if available
#     config = results[0].get("retrieval_config", {}) if results else {}
#     strategy = config.get("strategy", "N/A")
#     top_k = config.get("top_k", "N/A")
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     cards_html = []
#     for r in results:
#         eval_data = r["evaluation"]
#         is_supported = eval_data["is_supported"]
#         score = eval_data["score"]
#         status_class = "pass" if is_supported else "fail"
#         badge_text = "SUPPORTED" if is_supported else "UNSUPPORTED"

#         # Escape HTML safely
#         item_id = html.escape(str(r.get("id", "")))
#         question = html.escape(str(r.get("question", "")))
#         ground_truth = html.escape(str(r.get("ground_truth", "")))
#         reason = html.escape(str(eval_data.get("reason", "")))

#         # Format Missing Facts
#         missing_facts = eval_data.get("missing_facts", [])
#         if missing_facts:
#             missing_items = "".join(f"<li>{html.escape(str(f))}</li>" for f in missing_facts)
#             missing_section = f"""
#             <div class="missing-box">
#                 <strong>Missing Facts:</strong>
#                 <ul>{missing_items}</ul>
#             </div>
#             """
#         else:
#             missing_section = ""

#         # Format Retrieved Chunks
#         hits = r.get("retrieved_hits", [])
#         if hits:
#             chunks_list = []
#             for idx, hit in enumerate(hits, start=1):
#                 chunk_text = html.escape(str(hit.get("text", "")))
#                 chunk_score = hit.get("score", "N/A")
#                 meta_str = html.escape(json.dumps(hit.get("metadata", {})))
#                 chunks_list.append(f"""
#                 <div class="chunk-item">
#                     <div class="chunk-header">
#                         <span class="chunk-rank">Rank #{idx}</span>
#                         <span class="chunk-score">Score: {chunk_score}</span>
#                         <span class="chunk-meta" title="{meta_str}">Metadata: {meta_str}</span>
#                     </div>
#                     <pre class="chunk-text">{chunk_text}</pre>
#                 </div>
#                 """)
#             chunks_html = "".join(chunks_list)
#         else:
#             chunks_html = "<p class='empty-msg'>No chunks retrieved.</p>"

#         cards_html.append(f"""
#         <div class="card {status_class}" data-status="{status_class}">
#             <div class="card-header">
#                 <div class="title-group">
#                     <span class="item-id">{item_id}</span>
#                     <span class="badge {status_class}">{badge_text}</span>
#                 </div>
#                 <div class="score-pill score-{score}">Score: {score} / 5</div>
#             </div>

#             <div class="question-box">
#                 <span class="label">Question</span>
#                 <p>{question}</p>
#             </div>

#             <div class="grid-2">
#                 <div class="panel">
#                     <span class="label">Ground Truth (Golden)</span>
#                     <p class="gt-text">{ground_truth}</p>
#                 </div>
#                 <div class="panel">
#                     <span class="label">Judge Reasoning</span>
#                     <p class="reason-text">{reason}</p>
#                     {missing_section}
#                 </div>
#             </div>

#             <details {"open" if not is_supported else ""}>
#                 <summary>Retrieved Context ({len(hits)} chunks)</summary>
#                 <div class="chunks-container">
#                     {chunks_html}
#                 </div>
#             </details>
#         </div>
#         """)

#     full_html = f"""<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="UTF-8">
# <meta name="viewport" content="width=device-width, initial-scale=1.0">
# <title>RAG Retrieval Evaluation Report</title>
# <style>
#     :root {{
#         --bg: #f8fafc;
#         --card-bg: #ffffff;
#         --text: #0f172a;
#         --muted: #64748b;
#         --border: #e2e8f0;
#         --pass-bg: #dcfce7;
#         --pass-text: #166534;
#         --pass-border: #22c55e;
#         --fail-bg: #fee2e2;
#         --fail-text: #991b1b;
#         --fail-border: #ef4444;
#         --accent: #2563eb;
#     }}
#     * {{ box-sizing: border-box; }}
#     body {{
#         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
#         background: var(--bg);
#         color: var(--text);
#         margin: 0;
#         padding: 2rem;
#         line-height: 1.5;
#     }}
#     .container {{ max-width: 1100px; margin: 0 auto; }}
#     header {{
#         display: flex;
#         justify-content: space-between;
#         align-items: flex-end;
#         margin-bottom: 1.5rem;
#         border-bottom: 2px solid var(--border);
#         padding-bottom: 1rem;
#     }}
#     h1 {{ margin: 0; font-size: 1.75rem; }}
#     .meta-info {{ color: var(--muted); font-size: 0.9rem; }}
    
#     /* Summary Dashboard */
#     .summary-grid {{
#         display: grid;
#         grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
#         gap: 1rem;
#         margin-bottom: 1.5rem;
#     }}
#     .stat-card {{
#         background: var(--card-bg);
#         padding: 1.25rem;
#         border-radius: 10px;
#         border: 1px solid var(--border);
#         box-shadow: 0 1px 2px rgba(0,0,0,0.04);
#     }}
#     .stat-title {{ font-size: 0.85rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }}
#     .stat-value {{ font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }}

#     /* Filter Buttons */
#     .filters {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }}
#     .filter-btn {{
#         padding: 0.5rem 1rem;
#         border: 1px solid var(--border);
#         background: var(--card-bg);
#         border-radius: 6px;
#         cursor: pointer;
#         font-weight: 600;
#         color: var(--text);
#     }}
#     .filter-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

#     /* Evaluation Cards */
#     .card {{
#         background: var(--card-bg);
#         border: 1px solid var(--border);
#         border-left: 5px solid var(--border);
#         border-radius: 10px;
#         padding: 1.5rem;
#         margin-bottom: 1.25rem;
#         box-shadow: 0 1px 3px rgba(0,0,0,0.05);
#     }}
#     .card.pass {{ border-left-color: var(--pass-border); }}
#     .card.fail {{ border-left-color: var(--fail-border); }}

#     .card-header {{
#         display: flex;
#         justify-content: space-between;
#         align-items: center;
#         margin-bottom: 1rem;
#     }}
#     .title-group {{ display: flex; align-items: center; gap: 0.75rem; }}
#     .item-id {{ font-weight: 700; font-size: 1.1rem; }}
#     .badge {{
#         font-size: 0.75rem;
#         font-weight: 700;
#         padding: 0.2rem 0.6rem;
#         border-radius: 999px;
#     }}
#     .badge.pass {{ background: var(--pass-bg); color: var(--pass-text); }}
#     .badge.fail {{ background: var(--fail-bg); color: var(--fail-text); }}
#     .score-pill {{
#         font-weight: 700;
#         padding: 0.3rem 0.75rem;
#         border-radius: 6px;
#         background: #f1f5f9;
#     }}

#     .label {{
#         display: block;
#         font-size: 0.75rem;
#         font-weight: 700;
#         text-transform: uppercase;
#         color: var(--muted);
#         margin-bottom: 0.35rem;
#     }}
#     .question-box {{
#         background: #f8fafc;
#         padding: 0.85rem 1rem;
#         border-radius: 8px;
#         margin-bottom: 1rem;
#         border: 1px solid var(--border);
#     }}
#     .question-box p {{ margin: 0; font-weight: 600; }}

#     .grid-2 {{
#         display: grid;
#         grid-template-columns: 1fr 1fr;
#         gap: 1rem;
#         margin-bottom: 1rem;
#     }}
#     @media (max-width: 768px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
#     .panel {{
#         background: #fafafa;
#         padding: 1rem;
#         border-radius: 8px;
#         border: 1px solid var(--border);
#     }}
#     .panel p {{ margin: 0; font-size: 0.95rem; }}

#     .missing-box {{
#         margin-top: 0.75rem;
#         padding: 0.65rem;
#         background: #fff1f2;
#         border: 1px solid #fecdd3;
#         border-radius: 6px;
#         font-size: 0.88rem;
#         color: #9f1239;
#     }}
#     .missing-box ul {{ margin: 0.35rem 0 0 1.2rem; padding: 0; }}

#     /* Collapsible Chunks */
#     details {{
#         border-top: 1px solid var(--border);
#         padding-top: 0.75rem;
#     }}
#     summary {{
#         cursor: pointer;
#         font-weight: 600;
#         color: var(--accent);
#         user-select: none;
#     }}
#     .chunks-container {{ margin-top: 0.75rem; display: flex; flex-direction: column; gap: 0.75rem; }}
#     .chunk-item {{
#         border: 1px solid var(--border);
#         border-radius: 6px;
#         overflow: hidden;
#     }}
#     .chunk-header {{
#         background: #f1f5f9;
#         padding: 0.4rem 0.75rem;
#         font-size: 0.8rem;
#         display: flex;
#         gap: 1rem;
#         border-bottom: 1px solid var(--border);
#     }}
#     .chunk-rank {{ font-weight: 700; }}
#     .chunk-score {{ color: #0369a1; font-weight: 600; }}
#     .chunk-meta {{ color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
#     .chunk-text {{
#         margin: 0;
#         padding: 0.75rem;
#         white-space: pre-wrap;
#         font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
#         font-size: 0.85rem;
#         background: #ffffff;
#     }}
# </style>
# </head>
# <body>
# <div class="container">
#     <header>
#         <div>
#             <h1>RAG Retrieval Evaluation Report</h1>
#             <div class="meta-info">Strategy: <strong>{html.escape(str(strategy))}</strong> | Top-K: <strong>{html.escape(str(top_k))}</strong></div>
#         </div>
#         <div class="meta-info">Generated: {timestamp}</div>
#     </header>

#     <div class="summary-grid">
#         <div class="stat-card">
#             <div class="stat-title">Total Queries</div>
#             <div class="stat-value">{total}</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-title">Average Score</div>
#             <div class="stat-value">{avg_score:.2f} / 5.0</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-title">Pass Rate</div>
#             <div class="stat-value" style="color: {'#16a34a' if pass_rate >= 80 else '#dc2626'};">{pass_rate:.1f}%</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-title">Passed / Failed</div>
#             <div class="stat-value">{passed} / {failed}</div>
#         </div>
#     </div>

#     <div class="filters">
#         <button class="filter-btn active" onclick="filterCards('all', this)">All ({total})</button>
#         <button class="filter-btn" onclick="filterCards('pass', this)">Passed ({passed})</button>
#         <button class="filter-btn" onclick="filterCards('fail', this)">Failed ({failed})</button>
#     </div>

#     <div id="cards-list">
#         {"".join(cards_html)}
#     </div>
# </div>

# <script>
# function filterCards(status, btn) {{
#     document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
#     btn.classList.add('active');
#     document.querySelectorAll('.card').forEach(card => {{
#         if (status === 'all' || card.dataset.status === status) {{
#             card.style.display = 'block';
#         }} else {{
#             card.style.display = 'none';
#         }}
#     }});
# }}
# </script>
# </body>
# </html>
# """
#     Path(output_html_path).write_text(full_html, encoding="utf-8")