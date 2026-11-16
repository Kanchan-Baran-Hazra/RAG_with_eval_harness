import html
import json
from datetime import datetime
from pathlib import Path


def generate_gen_html_report(results: list[dict], output_html_path: str):
    """Generates a self-contained, interactive Dark Theme HTML report for RAG Generation evaluation."""
    total = len(results)
    
    # A query passes overall if it is both faithful (no hallucinations) and factually correct
    passed = sum(
        1 for r in results 
        if r["evaluation"]["is_faithful"] and r["evaluation"]["is_correct"]
    )
    failed = total - passed
    hallucinated_count = sum(
        1 for r in results if not r["evaluation"]["is_faithful"]
    )

    avg_faith = sum(r["evaluation"]["faithfulness_score"] for r in results) / total if total else 0.0
    avg_corr = sum(r["evaluation"]["correctness_score"] for r in results) / total if total else 0.0
    avg_rel = sum(r["evaluation"]["relevance_score"] for r in results) / total if total else 0.0
    pass_rate = (passed / total * 100) if total else 0.0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cards_html = []
    for r in results:
        eval_data = r["evaluation"]
        is_faithful = eval_data["is_faithful"]
        is_correct = eval_data["is_correct"]
        is_overall_pass = is_faithful and is_correct

        f_score = eval_data["faithfulness_score"]
        c_score = eval_data["correctness_score"]
        r_score = eval_data["relevance_score"]

        status_class = "pass" if is_overall_pass else "fail"
        hallucinated_attr = "true" if not is_faithful else "false"
        badge_text = "PASS" if is_overall_pass else "NEEDS REVIEW"

        # Safely escape all text fields
        item_id = html.escape(str(r.get("id", "")))
        question = html.escape(str(r.get("question", "")))
        ground_truth = html.escape(str(r.get("ground_truth", "")))
        generated_answer = html.escape(str(r.get("generated_answer", "")))
        reason = html.escape(str(eval_data.get("reason", "")))

        # Format Hallucinated Claims if any exist
        hallucinations = eval_data.get("hallucinated_claims", [])
        if hallucinations:
            hall_items = "".join(f"<li>{html.escape(str(h))}</li>" for h in hallucinations)
            hallucination_box = f"""
            <div class="hallucination-box">
                <strong>⚠️ Hallucinated Claims Detected (Not in Context):</strong>
                <ul>{hall_items}</ul>
            </div>
            """
        else:
            hallucination_box = ""

        # Format Retrieved Context Chunks
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
            chunks_html = "<p class='empty-msg'>No context chunks logged.</p>"

        cards_html.append(f"""
        <div class="card {status_class}" data-status="{status_class}" data-hallucinated="{hallucinated_attr}">
            <div class="card-header">
                <div class="title-group">
                    <span class="item-id">{item_id}</span>
                    <span class="badge {status_class}">{badge_text}</span>
                    {"<span class='badge hallucinated'>HALLUCINATED</span>" if not is_faithful else ""}
                </div>
                <div class="metric-pills">
                    <span class="pill {'pill-ok' if is_faithful else 'pill-bad'}">Faithful: {f_score}/5</span>
                    <span class="pill {'pill-ok' if is_correct else 'pill-bad'}">Correct: {c_score}/5</span>
                    <span class="pill {'pill-ok' if r_score >= 4 else 'pill-warn'}">Relevant: {r_score}/5</span>
                </div>
            </div>

            <div class="question-box">
                <span class="label">User Question</span>
                <p>{question}</p>
            </div>

            <div class="grid-2">
                <div class="panel gt-panel">
                    <span class="label">Ground Truth (Golden)</span>
                    <p>{ground_truth}</p>
                </div>
                <div class="panel gen-panel">
                    <span class="label">Generated RAG Answer</span>
                    <p>{generated_answer}</p>
                </div>
            </div>

            <div class="judge-box">
                <span class="label">Judge Verdict & Reasoning</span>
                <p>{reason}</p>
                {hallucination_box}
            </div>

            <details {"open" if not is_overall_pass else ""}>
                <summary>Inspect Source Context Provided to Generator ({len(hits)} chunks)</summary>
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
<title>RAG Generation Evaluation Report</title>
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
    .container {{ max-width: 1150px; margin: 0 auto; }}
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
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    .stat-card {{
        background: var(--card-bg);
        padding: 1.15rem;
        border-radius: 10px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }}
    .stat-title {{ font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    .stat-value {{ font-size: 1.65rem; font-weight: 700; margin-top: 0.25rem; color: #ffffff; }}

    /* Filter Buttons */
    .filters {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }}
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

    /* Cards */
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
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }}
    .title-group {{ display: flex; align-items: center; gap: 0.6rem; }}
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
    .badge.hallucinated {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}

    .metric-pills {{ display: flex; flex-wrap: wrap; gap: 0.45rem; }}
    .pill {{
        font-size: 0.82rem;
        font-weight: 700;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
    }}
    .pill-ok {{ background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.25); }}
    .pill-warn {{ background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }}
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
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--border);
    }}
    .gt-panel {{ background: var(--panel-bg); }}
    .gen-panel {{ background: rgba(59, 130, 246, 0.08); border-color: rgba(59, 130, 246, 0.3); }}
    .panel p {{ margin: 0; font-size: 0.95rem; white-space: pre-wrap; color: #e2e8f0; }}

    .judge-box {{
        background: var(--panel-bg);
        padding: 0.9rem 1rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        margin-bottom: 1rem;
    }}
    .judge-box p {{ margin: 0; font-size: 0.92rem; color: #cbd5e1; }}

    .hallucination-box {{
        margin-top: 0.75rem;
        padding: 0.75rem 0.9rem;
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 6px;
        font-size: 0.88rem;
        color: #fca5a5;
    }}
    .hallucination-box ul {{ margin: 0.35rem 0 0 1.2rem; padding: 0; }}

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
</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>RAG Generation Evaluation Report</h1>
            <div class="meta-info">Metrics: <strong>Faithfulness</strong> | <strong>Correctness</strong> | <strong>Relevance</strong></div>
        </div>
        <div class="meta-info">Generated: {timestamp}</div>
    </header>

    <div class="summary-grid">
        <div class="stat-card">
            <div class="stat-title">Overall Pass Rate</div>
            <div class="stat-value" style="color: {'#4ade80' if pass_rate >= 80 else '#f87171'};">{pass_rate:.1f}%</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Avg Faithfulness</div>
            <div class="stat-value">{avg_faith:.2f} / 5.0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Avg Correctness</div>
            <div class="stat-value">{avg_corr:.2f} / 5.0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Avg Relevance</div>
            <div class="stat-value">{avg_rel:.2f} / 5.0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Hallucinations</div>
            <div class="stat-value" style="color: {'#4ade80' if hallucinated_count == 0 else '#f87171'};">{hallucinated_count}</div>
        </div>
    </div>

    <div class="filters">
        <button class="filter-btn active" onclick="filterCards('all', this)">All ({total})</button>
        <button class="filter-btn" onclick="filterCards('pass', this)">Passed ({passed})</button>
        <button class="filter-btn" onclick="filterCards('fail', this)">Needs Review ({failed})</button>
        <button class="filter-btn" onclick="filterCards('hallucinated', this)">Hallucinated ({hallucinated_count})</button>
    </div>

    <div id="cards-list">
        {"".join(cards_html)}
    </div>
</div>

<script>
function filterCards(filterType, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {{
        if (filterType === 'all') {{
            card.style.display = 'block';
        }} else if (filterType === 'hallucinated') {{
            card.style.display = card.dataset.hallucinated === 'true' ? 'block' : 'none';
        }} else {{
            card.style.display = card.dataset.status === filterType ? 'block' : 'none';
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