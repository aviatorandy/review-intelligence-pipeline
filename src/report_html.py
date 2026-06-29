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
<div class="container" style="margin-top:48px;padding-bottom:60px">
  <section class="section" id="ask-section">
    <h2>💬 Ask the Reviews</h2>

    <div id="embed-status-row" style="font-size:0.78rem;color:var(--muted);margin-bottom:14px;display:flex;align-items:center;gap:8px">
      <span id="embed-dot" style="width:8px;height:8px;border-radius:50%;background:var(--amber);display:inline-block;animation:pulse 1.5s ease infinite;flex-shrink:0"></span>
      <span id="embed-status-text">Building search index...</span>
    </div>

    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px" id="chips">
      <span class="sq-chip" onclick="setQ(this)">Why do users love this product?</span>
      <span class="sq-chip" onclick="setQ(this)">What are the main complaints?</span>
      <span class="sq-chip" onclick="setQ(this)">Is it good for kids?</span>
      <span class="sq-chip" onclick="setQ(this)">What do people say about ads?</span>
      <span class="sq-chip" onclick="setQ(this)">Does it work offline?</span>
    </div>

    <div style="display:flex;gap:10px;margin-bottom:16px">
      <input id="ask-input" type="text" placeholder="e.g. Why do users uninstall the app?"
        disabled style="flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:10px;
        padding:12px 16px;color:var(--text);font-family:'DM Mono',monospace;font-size:0.88rem;outline:none">
      <button id="ask-btn" onclick="askQ()" disabled
        style="background:var(--accent);color:#fff;border:none;border-radius:10px;padding:12px 22px;
        font-family:'Syne',sans-serif;font-weight:600;font-size:0.9rem;cursor:pointer;opacity:0.45">Ask</button>
    </div>

    <div id="answer-box" style="display:none;background:var(--surface2);border:1px solid var(--border);
      border-radius:12px;padding:20px">
      <div style="font-size:0.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">Question</div>
      <div id="answer-q" style="font-size:0.85rem;color:var(--accent);margin-bottom:14px"></div>
      <div id="answer-text" style="font-size:0.85rem;line-height:1.7;white-space:pre-wrap"></div>
      <div id="sources-wrap" style="margin-top:14px"></div>
    </div>
  </section>
</div>

<style>
  .sq-chip {{
    background:var(--surface);border:1px solid var(--border);border-radius:99px;
    padding:6px 14px;font-size:0.75rem;color:var(--muted);cursor:pointer;
    transition:border-color 0.2s,color 0.2s;
  }}
  .sq-chip:hover {{border-color:var(--accent);color:var(--text)}}
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
      const col = s.sentiment === 'positive' ? 'var(--green)' : 'var(--red)';
      sw.innerHTML += `<span style="display:inline-flex;align-items:center;gap:6px;background:var(--surface);border:1px solid var(--border);border-radius:99px;padding:4px 12px;font-size:0.72rem;color:var(--muted);margin:3px">
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
        colors = {"high": "#22c55e", "medium": "#f59e0b", "low": "#ef4444"}
        color = colors.get(conf, "#888")
        return f'<span class="badge" style="background:{color}">{conf}</span>'

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
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #0a0a0f;
    --surface: #13131a;
    --surface2: #1c1c26;
    --border: #2a2a38;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --accent: #7c6af7;
    --green: #22c55e;
    --red: #ef4444;
    --amber: #f59e0b;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    padding: 40px 20px;
  }}

  .container {{ max-width: 900px; margin: 0 auto; }}

  header {{
    border-bottom: 1px solid var(--border);
    padding-bottom: 32px;
    margin-bottom: 48px;
    animation: fadeUp 0.6s ease both;
  }}

  header h1 {{
    font-family: 'Syne', sans-serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #e8e8f0 0%, #7c6af7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
  }}

  header .subtitle {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 8px;
    letter-spacing: 0.05em;
  }}

  .sentiment-block {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 48px;
    animation: fadeUp 0.6s 0.1s ease both;
  }}

  .sentiment-block h2 {{
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 24px;
  }}

  .sentiment-row {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 14px;
  }}

  .sentiment-label {{
    width: 70px;
    font-size: 0.8rem;
    color: var(--muted);
    flex-shrink: 0;
  }}

  .bar-track {{
    flex: 1;
    height: 10px;
    background: var(--surface2);
    border-radius: 99px;
    overflow: hidden;
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
    font-weight: 500;
  }}

  .n-reviews {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 12px;
  }}

  .section {{
    margin-bottom: 48px;
    animation: fadeUp 0.6s 0.2s ease both;
  }}

  .section h2 {{
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
  }}

  .card:hover {{ border-color: var(--accent); }}

  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }}

  .theme-name {{
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 600;
  }}

  .card-meta {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }}

  .review-count {{
    font-size: 0.8rem;
    font-weight: 500;
  }}

  .badge {{
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 99px;
    color: #000;
    font-weight: 600;
    letter-spacing: 0.05em;
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
    display: block;
    margin-bottom: 4px;
    letter-spacing: 0.05em;
  }}

  .quote {{
    font-size: 0.82rem;
    color: var(--text);
    line-height: 1.5;
    font-style: italic;
  }}

  .bullet-item {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
  }}

  .bullet-item:hover {{ border-color: var(--accent); }}

  .bullet-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}

  .bullet-claim {{
    font-size: 0.92rem;
    line-height: 1.5;
    flex: 1;
  }}

  .unknown-tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}

  .unknown-tag {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 99px;
    padding: 6px 16px;
    font-size: 0.78rem;
    color: var(--muted);
  }}

  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>Review Intelligence<br>Report</h1>
    <p class="subtitle">{product_label} · AMAZON REVIEWS · {n} REVIEWS SAMPLED</p>
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
