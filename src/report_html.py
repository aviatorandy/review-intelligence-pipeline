"""
Generates a beautiful HTML report from output.json.
Usage: python -m src.report_html --file results/runs/<timestamp>/output.json
Output: results/runs/<timestamp>/report.html
"""
import argparse
import json
import os


def _ask_section(job_id: str) -> str:
    return f"""
<div style="background:#fff;border-top:1px solid #e2e5ec;margin-top:48px;padding:48px 20px 64px">
<div style="max-width:860px;margin:0 auto">
  <h2 style="font-size:1.1rem;font-weight:700;color:#111827;margin-bottom:6px">Ask the Reviews</h2>
  <p style="font-size:0.85rem;color:#6b7280;margin-bottom:20px">Get plain-English answers grounded in what your customers actually said.</p>

  <div id="embed-status-row" style="font-size:0.8rem;color:#6b7280;margin-bottom:16px;display:flex;align-items:center;gap:8px;background:#f5f6fa;border:1px solid #e2e5ec;border-radius:8px;padding:10px 14px">
    <span id="embed-dot" style="width:8px;height:8px;border-radius:50%;background:#d97706;display:inline-block;animation:pulse 1.5s ease infinite;flex-shrink:0"></span>
    <span id="embed-status-text">Building search index — ready in about a minute after the report loads...</span>
  </div>

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">
    <span class="sq-chip" onclick="setQ(this)">What should we fix first?</span>
    <span class="sq-chip" onclick="setQ(this)">Why are customers leaving negative reviews?</span>
    <span class="sq-chip" onclick="setQ(this)">What do customers love most?</span>
    <span class="sq-chip" onclick="setQ(this)">What should we change in the Amazon listing?</span>
    <span class="sq-chip" onclick="setQ(this)">What are the best customer quotes for marketing?</span>
    <span class="sq-chip" onclick="setQ(this)">Compare 5-star and 1-star reviews.</span>
    <span class="sq-chip" onclick="setQ(this)">What are the top roadmap recommendations?</span>
  </div>

  <div style="display:flex;gap:10px;margin-bottom:16px">
    <input id="ask-input" type="text" placeholder="Ask anything about your customers..."
      disabled style="flex:1;background:#f5f6fa;border:1px solid #d0d5df;border-radius:10px;
      padding:12px 16px;color:#111827;font-family:'Inter',sans-serif;font-size:0.9rem;outline:none;
      transition:border-color 0.2s,box-shadow 0.2s">
    <button id="ask-btn" onclick="askQ()" disabled
      style="background:#4f46e5;color:#fff;border:none;border-radius:10px;padding:12px 24px;
      font-family:'Inter',sans-serif;font-weight:600;font-size:0.9rem;cursor:pointer;opacity:0.4;
      transition:opacity 0.2s,background 0.15s;white-space:nowrap">Ask</button>
  </div>

  <div id="answer-box" style="display:none;background:#f5f6fa;border:1px solid #e2e5ec;border-radius:12px;padding:20px 24px">
    <div style="font-size:0.7rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">Question</div>
    <div id="answer-q" style="font-size:0.88rem;color:#4f46e5;font-weight:500;margin-bottom:14px"></div>
    <div id="answer-text" style="font-size:0.92rem;line-height:1.75;color:#111827"></div>
    <div id="sources-wrap" style="margin-top:14px"></div>
  </div>
</div>
</div>

<style>
  .sq-chip {{
    background:#fff;border:1px solid #e2e5ec;border-radius:99px;
    padding:6px 14px;font-size:0.78rem;color:#6b7280;cursor:pointer;
    font-family:'Inter',sans-serif;
    transition:border-color 0.15s,color 0.15s,background 0.15s;
  }}
  .sq-chip:hover {{border-color:#4f46e5;color:#4f46e5;background:#eef2ff}}
  @keyframes pulse {{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}
  @keyframes spin {{to{{transform:rotate(360deg)}}}}
</style>

<script>
const JOB_ID = "{job_id}";
let embedReady = false;

function setQ(el) {{
  document.getElementById('ask-input').value = el.textContent;
}}

async function askQ() {{
  const q = document.getElementById('ask-input').value.trim();
  if (!q || !embedReady) return;
  const btn = document.getElementById('ask-btn');
  btn.disabled = true;
  btn.innerHTML = '<span style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,0.3);border-top-color:#fff;border-radius:50%;animation:spin 0.8s linear infinite;vertical-align:middle"></span>';
  try {{
    const res = await fetch('/ask/' + JOB_ID, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{question: q}})
    }});
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    document.getElementById('answer-q').textContent = data.question;
    document.getElementById('answer-text').textContent = data.answer;
    const sw = document.getElementById('sources-wrap');
    sw.innerHTML = '<div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">Source Reviews</div>';
    (data.sources || []).forEach(s => {{
      const icon = s.sentiment === 'positive' ? '👍' : '👎';
      const col = s.sentiment === 'positive' ? '#16a34a' : '#dc2626';
      sw.innerHTML += `<span style="display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e5ec;border-radius:99px;padding:4px 12px;font-size:0.72rem;color:#6b7280;margin:3px;font-family:'Inter',sans-serif">
        <span style="color:${{col}}">${{icon}}</span>Review #${{s.review_id}}
        <span style="opacity:0.5">${{(s.relevance*100).toFixed(0)}}% match</span></span>`;
    }});
    document.getElementById('answer-box').style.display = 'block';
  }} catch(e) {{ alert('Error: ' + e.message); }}
  finally {{
    btn.disabled = false;
    btn.textContent = 'Ask';
    if (embedReady) btn.style.opacity = '1';
  }}
}}

document.getElementById('ask-input').addEventListener('keydown', e => {{
  if (e.key === 'Enter') askQ();
}});

(function pollEmbed() {{
  fetch('/status/' + JOB_ID).then(r => r.json()).then(data => {{
    const dot = document.getElementById('embed-dot');
    const txt = document.getElementById('embed-status-text');
    if (data.embed_status === 'ready') {{
      embedReady = true;
      dot.style.animation = 'none';
      dot.style.background = '#16a34a';
      txt.textContent = 'Search index ready — ask anything about your customers';
      document.getElementById('ask-input').disabled = false;
      const btn = document.getElementById('ask-btn');
      btn.disabled = false;
      btn.style.opacity = '1';
    }} else if (data.embed_status === 'error') {{
      dot.style.animation = 'none';
      dot.style.background = '#dc2626';
      txt.textContent = 'Indexing failed: ' + (data.embed_message || '');
    }} else {{
      if (data.embed_message) txt.textContent = data.embed_message;
      setTimeout(pollEmbed, 2500);
    }}
  }}).catch(() => setTimeout(pollEmbed, 3000));
}})();
</script>"""


def _app_tab_report(apps: dict, output_path: str, data_path: str | None, job_id: str | None):
    """Render a tabbed multi-app report."""
    app_names = list(apps.keys())

    def tab_buttons():
        btns = ""
        for i, name in enumerate(app_names):
            active = "active" if i == 0 else ""
            btns += f'<button class="tab-btn {active}" onclick="showApp({i})">{name}</button>\n'
        return btns

    def tab_panels():
        panels = ""
        for i, (name, obj) in enumerate(apps.items()):
            display = "block" if i == 0 else "none"
            panels += f'<div class="tab-panel" id="app-panel-{i}" style="display:{display}">\n'
            panels += _app_section_html(name, obj, job_id)
            panels += "</div>\n"
        return panels

    ask_section_html = _ask_section(job_id) if job_id else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Product Insights Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #f5f6fa; --surface: #ffffff; --surface2: #f3f4f6;
    --border: #e2e5ec; --text: #111827; --muted: #6b7280;
    --accent: #4f46e5; --accent-light: #eef2ff;
    --green: #16a34a; --green-light: #dcfce7;
    --red: #dc2626; --red-light: #fee2e2;
    --amber: #d97706; --amber-light: #fef3c7;
  }}
  body {{ background:var(--bg); color:var(--text); font-family:'Inter',sans-serif; min-height:100vh; font-size:15px; }}
  .top-bar {{ background:#fff; border-bottom:1px solid var(--border); padding:20px 24px 0; position:sticky; top:0; z-index:100; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
  .top-bar-inner {{ max-width:900px; margin:0 auto; }}
  .top-bar h1 {{ font-size:1.1rem; font-weight:800; letter-spacing:-0.02em; margin-bottom:14px; }}
  .top-bar h1 span {{ color:var(--accent); }}
  .tab-row {{ display:flex; gap:4px; overflow-x:auto; padding-bottom:0; }}
  .tab-btn {{
    background:none; border:none; font-family:'Inter',sans-serif;
    font-size:0.82rem; font-weight:600; color:var(--muted); cursor:pointer;
    padding:8px 14px; border-radius:8px 8px 0 0;
    border:1px solid transparent; border-bottom:none;
    transition:color 0.15s, background 0.15s;
    white-space:nowrap;
  }}
  .tab-btn:hover {{ color:var(--accent); background:var(--accent-light); }}
  .tab-btn.active {{ color:var(--accent); background:#fff; border-color:var(--border); margin-bottom:-1px; position:relative; }}
  .container {{ max-width:900px; margin:0 auto; padding:32px 20px 64px; }}
  .stat-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:28px; }}
  .stat-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 18px; box-shadow:0 1px 3px rgba(0,0,0,0.05); }}
  .stat-label {{ font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--muted); margin-bottom:6px; }}
  .stat-value {{ font-size:1.6rem; font-weight:800; letter-spacing:-0.03em; line-height:1; }}
  .stat-sub {{ font-size:0.72rem; color:var(--muted); margin-top:4px; }}
  .exec-summary {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 24px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,0.05); }}
  .exec-summary .label {{ font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--muted); margin-bottom:10px; }}
  .exec-summary p {{ font-size:0.92rem; line-height:1.75; color:var(--text); }}
  .sentiment-block {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 24px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,0.05); }}
  .section-label {{ font-size:0.68rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }}
  .sentiment-row {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
  .sentiment-label {{ width:70px; font-size:0.8rem; font-weight:500; color:var(--muted); flex-shrink:0; }}
  .bar-track {{ flex:1; height:8px; background:var(--surface2); border-radius:99px; overflow:hidden; border:1px solid var(--border); }}
  .bar-fill {{ height:100%; border-radius:99px; }}
  .sentiment-pct {{ width:44px; text-align:right; font-size:0.88rem; font-weight:600; }}
  .section {{ margin-bottom:32px; }}
  .section > h2 {{ font-size:0.95rem; font-weight:700; margin-bottom:14px; display:flex; align-items:center; gap:8px; color:var(--text); }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 20px; margin-bottom:8px; transition:border-color 0.15s,box-shadow 0.15s; box-shadow:0 1px 2px rgba(0,0,0,0.04); }}
  .card:hover {{ border-color:var(--accent); box-shadow:0 2px 8px rgba(79,70,229,0.08); }}
  .card-header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px; flex-wrap:wrap; }}
  .theme-name {{ font-size:0.92rem; font-weight:700; color:var(--text); flex:1; }}
  .card-meta {{ display:flex; align-items:center; gap:8px; flex-shrink:0; }}
  .review-count {{ font-size:0.78rem; font-weight:600; }}
  .badge {{ font-size:0.65rem; padding:2px 9px; border-radius:99px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase; }}
  .evidence-list {{ display:flex; flex-direction:column; gap:6px; }}
  .evidence-item {{ background:var(--surface2); border-left:3px solid var(--accent); border-radius:0 8px 8px 0; padding:8px 12px; }}
  .review-id {{ font-size:0.68rem; color:var(--muted); font-weight:600; display:block; margin-bottom:3px; letter-spacing:0.04em; }}
  .quote {{ font-size:0.82rem; color:var(--text); line-height:1.5; font-style:italic; }}
  .export-row {{ display:flex; gap:8px; margin-bottom:24px; flex-wrap:wrap; }}
  .export-btn {{ font-size:0.78rem; font-weight:600; padding:6px 14px; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--muted); cursor:pointer; text-decoration:none; font-family:'Inter',sans-serif; transition:border-color 0.15s,color 0.15s; }}
  .export-btn:hover {{ border-color:var(--accent); color:var(--accent); }}
</style>
</head>
<body>

<div class="top-bar">
  <div class="top-bar-inner">
    <h1>Product <span>Insights</span> Report
      <span style="font-size:0.78rem;font-weight:500;color:var(--muted);margin-left:10px">{len(app_names)} apps</span>
    </h1>
    <div class="tab-row">
      {tab_buttons()}
    </div>
  </div>
</div>

<div class="container">
  {"" if not job_id else f'<div class="export-row"><a class="export-btn" href="/export/csv/{job_id}" download>⬇ Export CSV</a><a class="export-btn" href="/export/report/{job_id}" download>⬇ Download Report</a></div>'}
  {tab_panels()}
</div>

{ask_section_html}

<script>
function showApp(idx) {{
  document.querySelectorAll('.tab-panel').forEach((p,i) => p.style.display = i===idx ? 'block' : 'none');
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('active', i===idx));
}}
</script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"✅ Multi-app HTML report saved to: {output_path}")


def _app_section_html(app_name: str, obj: dict, job_id: str | None) -> str:
    """Render the body content for one app tab (no full <html> wrapper)."""
    sentiment = obj.get("sentiment", {})
    pos = sentiment.get("positive_rate", 0)
    neg = sentiment.get("negative_rate", 0)
    n = sentiment.get("n_reviews", 0)
    meta = obj.get("meta", {})
    total_analyzed = meta.get("total_analyzed", n)
    total_uploaded = meta.get("total_uploaded", n)
    quality = obj.get("quality", {})
    q_pct = int(quality.get("schema_pass_rate", 1.0) * 100)
    q_color = "#16a34a" if q_pct >= 80 else "#d97706" if q_pct >= 60 else "#dc2626"
    q_label = "Excellent" if q_pct >= 80 else "Good" if q_pct >= 60 else "Partial"
    executive_summary = obj.get("executive_summary", "")
    improvement_recs = obj.get("improvement_recommendations", [])
    listing_recs = obj.get("listing_recommendations", [])
    marketing_quotes = obj.get("top_marketing_quotes", [])

    def confidence_badge(conf):
        styles = {
            "high":   "background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0",
            "medium": "background:#fef3c7;color:#d97706;border:1px solid #fde68a",
            "low":    "background:#fee2e2;color:#dc2626;border:1px solid #fca5a5",
        }
        style = styles.get(conf, "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb")
        return f'<span class="badge" style="{style}">{conf}</span>'

    def priority_badge(priority):
        styles = {
            "high":   "background:#fee2e2;color:#dc2626;border:1px solid #fca5a5",
            "medium": "background:#fef3c7;color:#d97706;border:1px solid #fde68a",
            "low":    "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb",
        }
        style = styles.get(priority, "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb")
        label = {"high": "High Priority", "medium": "Medium", "low": "Low"}.get(priority, priority)
        return f'<span class="badge" style="{style}">{label}</span>'

    def evidence_html(evidence_list):
        items = ""
        for ev in evidence_list[:3]:
            items += f'''<div class="evidence-item">
                <span class="review-id">Review #{ev.get("review_id", "")}</span>
                <span class="quote">"{ev.get("quote", "")}"</span>
            </div>'''
        return items

    def theme_cards(items, is_complaint=False):
        accent = "#ef4444" if is_complaint else "#22c55e"
        cards = ""
        for item in items:
            theme = item.get("theme", "")
            count = item.get("review_count", "?")
            conf = item.get("confidence", "low")
            cards += f'''<div class="card">
                <div class="card-header">
                    <span class="theme-name">{theme}</span>
                    <div class="card-meta">
                        <span class="review-count" style="color:{accent}">{count} reviews</span>
                        {confidence_badge(conf)}
                    </div>
                </div>
                <div class="evidence-list">{evidence_html(item.get("evidence", []))}</div>
            </div>'''
        return cards

    def improvement_cards(recs):
        cards = ""
        for i, rec in enumerate(recs):
            impact = rec.get("business_impact", "")
            theme = rec.get("supporting_theme", "")
            cards += f'''<div class="card">
                <div class="card-header">
                    <div style="display:flex;align-items:center;gap:10px">
                        <span style="width:24px;height:24px;border-radius:50%;background:#eef2ff;color:#4f46e5;font-size:0.75rem;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">{i+1}</span>
                        <span class="theme-name">{rec.get("title","")}</span>
                    </div>
                    {priority_badge(rec.get("priority","medium"))}
                </div>
                <p style="font-size:0.86rem;color:#374151;line-height:1.65;margin-bottom:8px">{rec.get("description","")}</p>
                {"" if not impact else f'<div style="background:#f5f6fa;border-left:3px solid #4f46e5;border-radius:0 8px 8px 0;padding:7px 11px;font-size:0.8rem;color:#4f46e5;font-weight:500;margin-bottom:6px">Impact: {impact}</div>'}
                {"" if not theme else f'<div style="font-size:0.73rem;color:#9ca3af">Based on: {theme}</div>'}
            </div>'''
        return cards

    out = f"""
<div style="margin-bottom:24px;padding-top:4px">
  <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);margin-bottom:4px">{total_uploaded:,} reviews uploaded</div>
  <div class="stat-grid">
    <div class="stat-card"><div class="stat-label">Analyzed</div><div class="stat-value" style="color:var(--accent)">{total_analyzed:,}</div><div class="stat-sub">reviews</div></div>
    <div class="stat-card"><div class="stat-label">Positive</div><div class="stat-value" style="color:var(--green)">{pos*100:.0f}%</div><div class="stat-sub">{int(pos*n):,} customers</div></div>
    <div class="stat-card"><div class="stat-label">Negative</div><div class="stat-value" style="color:var(--red)">{neg*100:.0f}%</div><div class="stat-sub">{int(neg*n):,} customers</div></div>
    <div class="stat-card"><div class="stat-label">Data Quality</div><div class="stat-value" style="color:{q_color}">{q_pct}%</div><div class="stat-sub">{q_label}</div></div>
  </div>
</div>

{"" if not executive_summary else f'<div class="exec-summary"><div class="label">Executive Summary</div><p>{executive_summary}</p></div>'}

<div class="sentiment-block">
  <div class="section-label">Sentiment</div>
  <div class="sentiment-row">
    <span class="sentiment-label">Positive</span>
    <div class="bar-track"><div class="bar-fill" style="width:{pos*100:.1f}%;background:var(--green)"></div></div>
    <span class="sentiment-pct" style="color:var(--green)">{pos*100:.1f}%</span>
  </div>
  <div class="sentiment-row">
    <span class="sentiment-label">Negative</span>
    <div class="bar-track"><div class="bar-fill" style="width:{neg*100:.1f}%;background:var(--red)"></div></div>
    <span class="sentiment-pct" style="color:var(--red)">{neg*100:.1f}%</span>
  </div>
</div>

{"" if not improvement_recs else f'<section class="section"><h2>🛠 Improvement Opportunities</h2>{improvement_cards(improvement_recs)}</section>'}
<section class="section"><h2>❌ Top Complaints</h2>{theme_cards(obj.get("top_complaints",[]), is_complaint=True)}</section>
<section class="section"><h2>✅ What Customers Love</h2>{theme_cards(obj.get("top_strengths",[]), is_complaint=False)}</section>

{_listing_section(listing_recs)}
{_quote_section(marketing_quotes)}
"""
    return out


def _listing_section(recs: list) -> str:
    if not recs:
        return ""
    cards = ""
    for r in recs:
        rationale_html = (
            f'<div style="font-size:0.78rem;color:#6b7280;font-style:italic">{r.get("rationale","")}</div>'
            if r.get("rationale") else ""
        )
        cards += (
            f'<div class="card">'
            f'<div class="card-header"><span class="theme-name">{r.get("title","")}</span></div>'
            f'<p style="font-size:0.86rem;color:#374151;line-height:1.65;margin-bottom:6px">{r.get("description","")}</p>'
            f'{rationale_html}</div>'
        )
    return f'<section class="section"><h2>🛒 Listing Recommendations</h2>{cards}</section>'


def _quote_section(quotes: list) -> str:
    if not quotes:
        return ""
    cards = ""
    for q in quotes:
        theme_html = (
            f'<div style="font-size:0.72rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.07em;font-weight:600">{q.get("theme","")}</div>'
            if q.get("theme") else ""
        )
        quote_text = q.get("quote", "")
        cards += (
            f'<div style="background:#fafafa;border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:8px">'
            f'<div style="font-size:0.95rem;color:var(--text);line-height:1.65;font-style:italic;margin-bottom:6px">"{quote_text}"</div>'
            f'{theme_html}</div>'
        )
    return f'<section class="section"><h2>⭐ Best Quotes for Marketing</h2>{cards}</section>'


def generate_html(obj, output_path, data_path=None, job_id=None):
    if obj.get("multi_app") and "apps" in obj:
        _app_tab_report(obj["apps"], output_path, data_path, job_id)
        return

    sentiment = obj.get("sentiment", {})
    pos = sentiment.get("positive_rate", 0)
    neg = sentiment.get("negative_rate", 0)
    n = sentiment.get("n_reviews", 0)

    if data_path:
        raw = os.path.splitext(os.path.basename(data_path))[0]
        # Hide UUIDs (hex-dash pattern) — fall back to generic label
        import re as _re
        if _re.fullmatch(r"[0-9a-f\-]{32,}", raw, _re.I):
            product_label = "Your Product"
        else:
            product_label = raw.replace("_", " ").replace("-", " ").title()
    else:
        product_label = "Your Product"

    meta = obj.get("meta", {})
    total_uploaded = meta.get("total_uploaded", n)
    total_analyzed = meta.get("total_analyzed", n)
    tier = meta.get("tier", "")
    chunks_processed = meta.get("chunks_processed", 0)
    chunks_failed = meta.get("chunks_failed", 0)

    quality = obj.get("quality", {})
    schema_pass_rate = quality.get("schema_pass_rate", 1.0)

    executive_summary = obj.get("executive_summary", "")
    improvement_recs = obj.get("improvement_recommendations", [])
    listing_recs = obj.get("listing_recommendations", [])
    marketing_quotes = obj.get("top_marketing_quotes", [])

    def confidence_badge(conf):
        styles = {
            "high":   "background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0",
            "medium": "background:#fef3c7;color:#d97706;border:1px solid #fde68a",
            "low":    "background:#fee2e2;color:#dc2626;border:1px solid #fca5a5",
        }
        style = styles.get(conf, "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb")
        return f'<span class="badge" style="{style}">{conf}</span>'

    def priority_badge(priority):
        styles = {
            "high":   "background:#fee2e2;color:#dc2626;border:1px solid #fca5a5",
            "medium": "background:#fef3c7;color:#d97706;border:1px solid #fde68a",
            "low":    "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb",
        }
        style = styles.get(priority, "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb")
        label = {"high": "High Priority", "medium": "Medium", "low": "Low"}.get(priority, priority)
        return f'<span class="badge" style="{style}">{label}</span>'

    def evidence_html(evidence_list):
        items = ""
        for ev in evidence_list[:3]:
            items += f'''
            <div class="evidence-item">
                <span class="review-id">Review #{ev.get("review_id", "")}</span>
                <span class="quote">"{ev.get("quote", "")}"</span>
            </div>'''
        return items

    def theme_cards(items, is_complaint=False):
        cards = ""
        accent = "#ef4444" if is_complaint else "#22c55e"
        for item in items:
            theme = item.get("theme", item.get("claim", ""))
            count = item.get("review_count", "?")
            conf = item.get("confidence", "low")
            evidence = item.get("evidence", [])
            cards += f'''
            <div class="card">
                <div class="card-header">
                    <span class="theme-name">{theme}</span>
                    <div class="card-meta">
                        <span class="review-count" style="color:{accent}">{count} reviews</span>
                        {confidence_badge(conf)}
                    </div>
                </div>
                <div class="evidence-list">{evidence_html(evidence)}</div>
            </div>'''
        return cards

    def improvement_cards(recs):
        cards = ""
        for i, rec in enumerate(recs):
            title = rec.get("title", "")
            desc = rec.get("description", "")
            priority = rec.get("priority", "medium")
            impact = rec.get("business_impact", "")
            theme = rec.get("supporting_theme", "")
            num = i + 1
            cards += f'''
            <div class="card">
                <div class="card-header">
                    <div style="display:flex;align-items:center;gap:10px">
                        <span style="width:26px;height:26px;border-radius:50%;background:#eef2ff;color:#4f46e5;font-size:0.78rem;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">{num}</span>
                        <span class="theme-name">{title}</span>
                    </div>
                    {priority_badge(priority)}
                </div>
                <p style="font-size:0.88rem;color:#374151;line-height:1.65;margin-bottom:10px">{desc}</p>
                {"" if not impact else f'<div style="background:#f5f6fa;border-left:3px solid #4f46e5;border-radius:0 8px 8px 0;padding:8px 12px;font-size:0.82rem;color:#4f46e5;font-weight:500;margin-bottom:8px">Business impact: {impact}</div>'}
                {"" if not theme else f'<div style="font-size:0.75rem;color:#9ca3af">Based on: {theme}</div>'}
            </div>'''
        return cards

    def listing_cards(recs):
        cards = ""
        for rec in recs:
            title = rec.get("title", "")
            desc = rec.get("description", "")
            rationale = rec.get("rationale", "")
            cards += f'''
            <div class="card">
                <div class="card-header">
                    <span class="theme-name">{title}</span>
                </div>
                <p style="font-size:0.88rem;color:#374151;line-height:1.65;margin-bottom:10px">{desc}</p>
                {"" if not rationale else f'<div style="font-size:0.8rem;color:#6b7280;font-style:italic">{rationale}</div>'}
            </div>'''
        return cards

    def marketing_quote_cards(quotes):
        cards = ""
        for q in quotes:
            quote = q.get("quote", "")
            theme = q.get("theme", "")
            cards += f'''
            <div style="background:#fafafa;border:1px solid #e2e5ec;border-radius:12px;padding:18px 22px;margin-bottom:10px">
                <div style="font-size:1rem;color:#111827;line-height:1.65;font-style:italic;margin-bottom:8px">"{quote}"</div>
                {"" if not theme else f'<div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.07em;font-weight:600">{theme}</div>'}
            </div>'''
        return cards

    # Quality indicator
    q_pct = int(schema_pass_rate * 100)
    q_color = "#16a34a" if q_pct >= 80 else "#d97706" if q_pct >= 60 else "#dc2626"
    q_label = "Excellent" if q_pct >= 80 else "Good" if q_pct >= 60 else "Partial"

    ask_section_html = _ask_section(job_id) if job_id else ""

    # Stat cards
    tier_display = {"small": "Full Dataset", "medium": "Smart Sample", "large": "Large Dataset"}.get(tier, tier.title() if tier else "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{product_label} — Product Insights Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #f5f6fa;
    --surface: #ffffff;
    --surface2: #f3f4f6;
    --border: #e2e5ec;
    --text: #111827;
    --muted: #6b7280;
    --accent: #4f46e5;
    --accent-light: #eef2ff;
    --green: #16a34a;
    --green-light: #dcfce7;
    --red: #dc2626;
    --red-light: #fee2e2;
    --amber: #d97706;
    --amber-light: #fef3c7;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    padding: 48px 20px;
    font-size: 15px;
  }}

  .container {{ max-width: 860px; margin: 0 auto; }}

  header {{
    border-bottom: 1px solid var(--border);
    padding-bottom: 28px;
    margin-bottom: 36px;
  }}

  header h1 {{
    font-size: clamp(1.6rem, 4vw, 2.2rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text);
    line-height: 1.15;
    margin-bottom: 6px;
  }}

  header h1 span {{ color: var(--accent); }}
  header .subtitle {{ color: var(--muted); font-size: 0.88rem; margin-top: 4px; }}

  .export-row {{ display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; }}
  .export-btn {{
    font-size:0.78rem;font-weight:600;padding:6px 14px;border-radius:8px;border:1px solid var(--border);
    background:var(--surface);color:var(--muted);cursor:pointer;text-decoration:none;
    font-family:'Inter',sans-serif;transition:border-color 0.15s,color 0.15s;
  }}
  .export-btn:hover {{ border-color:var(--accent);color:var(--accent); }}

  /* Stat cards */
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 32px;
  }}

  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}

  .stat-label {{
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 8px;
  }}

  .stat-value {{
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
  }}

  .stat-sub {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 4px;
  }}

  /* Executive summary */
  .exec-summary {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}

  .exec-summary .label {{
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 12px;
  }}

  .exec-summary p {{
    font-size: 0.95rem;
    line-height: 1.75;
    color: var(--text);
  }}

  /* Sentiment */
  .sentiment-block {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}

  .section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 16px;
  }}

  .sentiment-row {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 10px;
  }}

  .sentiment-label {{
    width: 72px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--muted);
    flex-shrink: 0;
  }}

  .bar-track {{
    flex: 1;
    height: 10px;
    background: var(--surface2);
    border-radius: 99px;
    overflow: hidden;
    border: 1px solid var(--border);
  }}

  .bar-fill {{
    height: 100%;
    border-radius: 99px;
  }}

  .sentiment-pct {{
    width: 48px;
    text-align: right;
    font-size: 0.9rem;
    font-weight: 600;
  }}

  .section {{
    margin-bottom: 40px;
  }}

  .section > h2 {{
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text);
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
    transition: border-color 0.15s, box-shadow 0.15s;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }}

  .card:hover {{ border-color: var(--accent); box-shadow: 0 2px 8px rgba(79,70,229,0.08); }}

  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}

  .theme-name {{
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text);
    flex: 1;
  }}

  .card-meta {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }}

  .review-count {{
    font-size: 0.8rem;
    font-weight: 600;
  }}

  .badge {{
    font-size: 0.68rem;
    padding: 3px 10px;
    border-radius: 99px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  .evidence-list {{ display: flex; flex-direction: column; gap: 8px; }}

  .evidence-item {{
    background: var(--surface2);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
  }}

  .review-id {{
    font-size: 0.7rem;
    color: var(--muted);
    font-weight: 600;
    display: block;
    margin-bottom: 4px;
    letter-spacing: 0.04em;
  }}

  .quote {{
    font-size: 0.84rem;
    color: var(--text);
    line-height: 1.55;
    font-style: italic;
  }}

  .quality-bar {{
    display:flex;align-items:center;gap:12px;margin-top:8px;
  }}
</style>
</head>
<body>
<div class="container">

  <header>
    <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);margin-bottom:6px">Product Insights Report</div>
    <h1>{product_label}</h1>
    <p class="subtitle">{total_analyzed:,} reviews analyzed · {tier_display}</p>
    <div class="export-row">
      {"" if not job_id else f'<a class="export-btn" href="/export/csv/{job_id}" download>⬇ Export CSV</a><a class="export-btn" href="/export/report/{job_id}" download>⬇ Download Report</a>'}
    </div>
  </header>

  <!-- Dashboard stat cards -->
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-label">Reviews Analyzed</div>
      <div class="stat-value" style="color:var(--accent)">{total_analyzed:,}</div>
      <div class="stat-sub">of {total_uploaded:,} uploaded</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Positive Sentiment</div>
      <div class="stat-value" style="color:var(--green)">{pos*100:.0f}%</div>
      <div class="stat-sub">{int(pos * n):,} satisfied customers</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Negative Sentiment</div>
      <div class="stat-value" style="color:var(--red)">{neg*100:.0f}%</div>
      <div class="stat-sub">{int(neg * n):,} customers with issues</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Data Quality</div>
      <div class="stat-value" style="color:{q_color}">{q_pct}%</div>
      <div class="stat-sub">{q_label} · {chunks_processed} chunks passed</div>
    </div>
  </div>

  {"" if not executive_summary else f'''
  <!-- Executive Summary -->
  <div class="exec-summary">
    <div class="label">Executive Summary</div>
    <p>{executive_summary}</p>
  </div>'''}

  <!-- Sentiment -->
  <div class="sentiment-block">
    <div class="section-label">Sentiment Distribution</div>
    <div class="sentiment-row">
      <span class="sentiment-label">Positive</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:{pos*100:.1f}%; background: var(--green);"></div>
      </div>
      <span class="sentiment-pct" style="color: var(--green)">{pos*100:.1f}%</span>
    </div>
    <div class="sentiment-row">
      <span class="sentiment-label">Negative</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:{neg*100:.1f}%; background: var(--red);"></div>
      </div>
      <span class="sentiment-pct" style="color: var(--red)">{neg*100:.1f}%</span>
    </div>
  </div>

  {"" if not improvement_recs else f'''
  <!-- Improvement Recommendations -->
  <section class="section">
    <h2>🛠 Top Improvement Opportunities</h2>
    {improvement_cards(improvement_recs)}
  </section>'''}

  <section class="section">
    <h2>❌ Top Customer Complaints</h2>
    {theme_cards(obj.get("top_complaints", []), is_complaint=True)}
  </section>

  <section class="section">
    <h2>✅ What Customers Love</h2>
    {theme_cards(obj.get("top_strengths", []), is_complaint=False)}
  </section>

  {"" if not listing_recs else f'''
  <!-- Listing Recommendations -->
  <section class="section">
    <h2>🛒 Amazon Listing Recommendations</h2>
    {listing_cards(listing_recs)}
  </section>'''}

  {"" if not marketing_quotes else f'''
  <!-- Marketing Quotes -->
  <section class="section">
    <h2>⭐ Best Customer Quotes for Marketing</h2>
    {marketing_quote_cards(marketing_quotes)}
  </section>'''}

</div>

{ask_section_html}

</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"✅ HTML report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to output.json")
    args = parser.parse_args()

    output_path = args.file.replace("output.json", "report.html")

    with open(args.file) as f:
        obj = json.load(f)

    generate_html(obj, output_path)
    print(f"   Open it with: open {output_path}")


if __name__ == "__main__":
    main()
