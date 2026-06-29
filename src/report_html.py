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
  <h2 style="font-size:1rem;font-weight:700;color:#111827;margin-bottom:16px;display:flex;align-items:center;gap:8px">💬 Ask the Reviews</h2>

  <div id="embed-status-row" style="font-size:0.8rem;color:#6b7280;margin-bottom:16px;display:flex;align-items:center;gap:8px;background:#f5f6fa;border:1px solid #e2e5ec;border-radius:8px;padding:10px 14px">
    <span id="embed-dot" style="width:8px;height:8px;border-radius:50%;background:#d97706;display:inline-block;animation:pulse 1.5s ease infinite;flex-shrink:0"></span>
    <span id="embed-status-text">Building search index — this takes a minute after the report loads...</span>
  </div>

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">
    <span class="sq-chip" onclick="setQ(this)">Why do users love this product?</span>
    <span class="sq-chip" onclick="setQ(this)">What are the main complaints?</span>
    <span class="sq-chip" onclick="setQ(this)">Is it good for kids?</span>
    <span class="sq-chip" onclick="setQ(this)">What do people say about ads?</span>
    <span class="sq-chip" onclick="setQ(this)">Does it work offline?</span>
  </div>

  <div style="display:flex;gap:10px;margin-bottom:16px">
    <input id="ask-input" type="text" placeholder="e.g. Why do users uninstall the app?"
      disabled style="flex:1;background:#f5f6fa;border:1px solid #d0d5df;border-radius:10px;
      padding:12px 16px;color:#111827;font-family:'Inter',sans-serif;font-size:0.9rem;outline:none;
      transition:border-color 0.2s,box-shadow 0.2s">
    <button id="ask-btn" onclick="askQ()" disabled
      style="background:#4f46e5;color:#fff;border:none;border-radius:10px;padding:12px 24px;
      font-family:'Inter',sans-serif;font-weight:600;font-size:0.9rem;cursor:pointer;opacity:0.4;
      transition:opacity 0.2s,background 0.15s">Ask</button>
  </div>

  <div id="answer-box" style="display:none;background:#f5f6fa;border:1px solid #e2e5ec;border-radius:12px;padding:20px 24px">
    <div style="font-size:0.7rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">Question</div>
    <div id="answer-q" style="font-size:0.88rem;color:#4f46e5;font-weight:500;margin-bottom:14px"></div>
    <div id="answer-text" style="font-size:0.88rem;line-height:1.7;color:#111827;white-space:pre-wrap"></div>
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
    sw.innerHTML = '<div style="font-size:0.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">Retrieved Reviews</div>';
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
      dot.style.background = 'var(--green)';
      txt.textContent = 'Search index ready — ask anything about these reviews';
      document.getElementById('ask-input').disabled = false;
      const btn = document.getElementById('ask-btn');
      btn.disabled = false;
      btn.style.opacity = '1';
    }} else if (data.embed_status === 'error') {{
      dot.style.animation = 'none';
      dot.style.background = 'var(--red)';
      txt.textContent = 'Indexing failed: ' + (data.embed_message || '');
    }} else {{
      if (data.embed_message) txt.textContent = data.embed_message;
      setTimeout(pollEmbed, 2500);
    }}
  }}).catch(() => setTimeout(pollEmbed, 3000));
}})();
</script>"""


def generate_html(obj, output_path, data_path=None, job_id=None):
    sentiment = obj.get("sentiment", {})
    pos = sentiment.get("positive_rate", 0)
    neg = sentiment.get("negative_rate", 0)
    n = sentiment.get("n_reviews", 0)

    # Derive product label from data file path (e.g. "angry_birds.csv" → "ANGRY BIRDS")
    if data_path:
        import os
        product_label = os.path.splitext(os.path.basename(data_path))[0].replace("_", " ").upper()
    else:
        product_label = "PRODUCT"

    def confidence_badge(conf):
        styles = {
            "high":   "background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0",
            "medium": "background:#fef3c7;color:#d97706;border:1px solid #fde68a",
            "low":    "background:#fee2e2;color:#dc2626;border:1px solid #fca5a5",
        }
        style = styles.get(conf, "background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb")
        return f'<span class="badge" style="{style}">{conf}</span>'

    def evidence_html(evidence_list):
        items = ""
        for ev in evidence_list:
            items += f'''
            <div class="evidence-item">
                <span class="review-id">Review #{ev["review_id"]}</span>
                <span class="quote">"{ev["quote"]}"</span>
            </div>'''
        return items

    def theme_cards(items, is_complaint=False):
        cards = ""
        for item in items:
            theme = item.get("theme", item.get("claim", ""))
            count = item.get("review_count", "?")
            conf = item.get("confidence", "low")
            evidence = item.get("evidence", [])
            accent = "#ef4444" if is_complaint else "#22c55e"
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

    def bullet_items(bullets):
        items = ""
        for b in bullets:
            conf = b.get("confidence", "low")
            evidence = b.get("evidence", [])
            items += f'''
            <div class="bullet-item">
                <div class="bullet-header">
                    {confidence_badge(conf)}
                    <span class="bullet-claim">{b["claim"]}</span>
                </div>
                <div class="evidence-list">{evidence_html(evidence)}</div>
            </div>'''
        return items

    unknowns = obj.get("unknowns", [])
    unknowns_html = ""
    if unknowns:
        tags = "".join(f'<span class="unknown-tag">{u}</span>' for u in unknowns)
        unknowns_html = f'<section class="section"><h2>❓ Unknowns</h2><div class="unknown-tags">{tags}</div></section>'

    ask_section_html = _ask_section(job_id) if job_id else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Review Intelligence Report</title>
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
    margin-bottom: 40px;
  }}

  header h1 {{
    font-size: clamp(1.8rem, 4vw, 2.6rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text);
    line-height: 1.15;
  }}

  header h1 span {{ color: var(--accent); }}

  header .subtitle {{
    color: var(--muted);
    font-size: 0.88rem;
    margin-top: 6px;
  }}

  .sentiment-block {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}

  .sentiment-block h2 {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 20px;
  }}

  .sentiment-row {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 12px;
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
    transition: width 1.2s cubic-bezier(0.16, 1, 0.3, 1);
  }}

  .sentiment-pct {{
    width: 48px;
    text-align: right;
    font-size: 0.9rem;
    font-weight: 600;
  }}

  .n-reviews {{
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 10px;
  }}

  .section {{
    margin-bottom: 40px;
  }}

  .section h2 {{
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

  .bullet-item {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: border-color 0.15s, box-shadow 0.15s;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }}

  .bullet-item:hover {{ border-color: var(--accent); box-shadow: 0 2px 8px rgba(79,70,229,0.08); }}

  .bullet-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }}

  .bullet-claim {{
    font-size: 0.9rem;
    line-height: 1.55;
    flex: 1;
    color: var(--text);
  }}

  .unknown-tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}

  .unknown-tag {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 99px;
    padding: 5px 14px;
    font-size: 0.78rem;
    color: var(--muted);
  }}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>Review <span style="color:var(--accent)">Intelligence</span> Report</h1>
    <p class="subtitle">{product_label} · Amazon Reviews · {n} reviews analyzed</p>
  </header>

  <div class="sentiment-block">
    <h2>Sentiment Distribution</h2>
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
    <p class="n-reviews">Based on {n} sampled reviews with ground-truth labels</p>
  </div>

  <section class="section">
    <h2>📋 Executive Summary</h2>
    {bullet_items(obj.get("summary_bullets", []))}
  </section>

  <section class="section">
    <h2>✅ Top Strengths</h2>
    {theme_cards(obj.get("top_strengths", []), is_complaint=False)}
  </section>

  <section class="section">
    <h2>❌ Top Complaints</h2>
    {theme_cards(obj.get("top_complaints", []), is_complaint=True)}
  </section>

  {unknowns_html}

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
