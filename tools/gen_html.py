#!/usr/bin/env python3
"""Generate quotes-by-layer.html from quotes.json.

Reads the curated bank (which carries a per-quote "layer" field) and writes a
single self-contained, dependency-free HTML page: quotes grouped into the 8
operating-system layers, with live search, click-to-filter tags, a distribution
bar, and light/dark theming.

Usage (from anywhere):  python tools/gen_html.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUOTES = ROOT / "quotes.json"
OUT = ROOT / "quotes-by-layer.html"

# Layer display order (the OS narrative), one-line role, and accent colour.
LAYERS = [
    ("1. Mortality & Time",         "Life is short — the ignition",            "#e0567a"),
    ("2. Action & Decisiveness",    "Decide, then move",                       "#e08a3c"),
    ("3. Perseverance & Adversity", "Persist through resistance",              "#d9b23c"),
    ("4. Inner Mastery",            "Govern your own mind",                    "#5bb06a"),
    ("5. Strategy & Power",         "Win by intelligence, not just force",     "#3ca0c4"),
    ("6. Wisdom & Learning",        "Understand, keep learning",               "#5c78d6"),
    ("7. Humor & Perspective",      "Don't take yourself too seriously",       "#9b6cd6"),
    ("8. Connection & Meaning",     "Purpose — and the thin thread of others", "#d264b0"),
    ("9. Other",                    "Uncategorised",                           "#8a8f98"),
]

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Daily Quote Bot — Quotes by Layer</title>
<style>
:root{
  --bg:#faf9f7; --panel:#ffffff; --ink:#1c1d21; --muted:#6b7079; --line:#e7e4df;
  --chip:#f0eee9; --shadow:0 1px 2px rgba(0,0,0,.05),0 4px 16px rgba(0,0,0,.04);
}
@media (prefers-color-scheme:dark){
  :root{--bg:#141517;--panel:#1c1e21;--ink:#eceef1;--muted:#9aa0a8;--line:#2c2f34;
  --chip:#26292e;--shadow:0 1px 2px rgba(0,0,0,.3),0 6px 20px rgba(0,0,0,.25);}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:900px;margin:0 auto;padding:32px 20px 80px}
header h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.02em}
header p{margin:0;color:var(--muted);font-size:.92rem}
.bar{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:20px 0 6px;box-shadow:var(--shadow)}
.bar span{display:block}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:.78rem;color:var(--muted);margin-bottom:22px}
.legend b{color:var(--ink);font-weight:600}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}
.controls{position:sticky;top:0;z-index:5;background:var(--bg);padding:12px 0 14px;margin-bottom:6px;border-bottom:1px solid var(--line)}
#q{width:100%;padding:11px 14px;font-size:1rem;border:1px solid var(--line);border-radius:10px;
  background:var(--panel);color:var(--ink);box-shadow:var(--shadow)}
#q::placeholder{color:var(--muted)}
.meta{display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:.8rem;color:var(--muted)}
.meta a{color:inherit;cursor:pointer;text-decoration:underline;text-underline-offset:2px}
details{background:var(--panel);border:1px solid var(--line);border-radius:14px;margin:14px 0;
  overflow:hidden;box-shadow:var(--shadow)}
summary{cursor:pointer;list-style:none;padding:16px 18px;display:flex;align-items:baseline;gap:10px}
summary::-webkit-details-marker{display:none}
summary .ly{font-weight:650;letter-spacing:-.01em}
summary .ds{color:var(--muted);font-size:.85rem;flex:1}
summary .ct{color:var(--muted);font-variant-numeric:tabular-nums;font-size:.85rem}
summary .car{color:var(--muted);transition:transform .15s}
details[open] summary .car{transform:rotate(90deg)}
.list{padding:0 18px 10px}
.card{padding:14px 0;border-top:1px solid var(--line)}
.card .txt{margin:0}
.card .by{color:var(--muted);font-size:.9rem;margin-top:5px}
.tags{margin-top:7px;display:flex;flex-wrap:wrap;gap:6px}
.tag{font-size:.72rem;background:var(--chip);color:var(--muted);padding:2px 9px;border-radius:20px;cursor:pointer}
.tag:hover{color:var(--ink)}
mark{background:#ffd76a;color:#1c1d21;border-radius:3px;padding:0 1px}
.empty{color:var(--muted);text-align:center;padding:40px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Claude Daily Quote Bot — Quotes by Layer</h1>
  <p><span id="total"></span> hand-picked quotes, classified into 8 layers. Search filters live across all layers; click a tag to filter by it.</p>
</header>
<div class="bar" id="bar"></div>
<div class="legend" id="legend"></div>
<div class="controls">
  <input id="q" type="search" placeholder="Search quotes, authors, tags…  (Esc to clear)" autocomplete="off">
  <div class="meta"><span id="showing"></span><a id="toggle">collapse all</a></div>
</div>
<div id="sections"></div>
<div class="empty" id="empty" hidden>No matches.</div>
</div>
<script>
const DATA = __PAYLOAD__;
const byLayer = {};
DATA.layers.forEach(l => byLayer[l.name] = []);
DATA.quotes.forEach(q => (byLayer[q.layer] || (byLayer[q.layer]=[])).push(q));

document.getElementById('total').textContent = DATA.total;

const bar = document.getElementById('bar'), legend = document.getElementById('legend');
DATA.layers.filter(l=>l.count>0).forEach(l=>{
  const s=document.createElement('span');
  s.style.width=(l.count/DATA.total*100)+'%'; s.style.background=l.color;
  s.title=l.name+' — '+l.count; bar.appendChild(s);
  const item=document.createElement('span');
  item.innerHTML='<span class="dot" style="background:'+l.color+'"></span><b>'+l.name.replace(/^\d+\.\s/,'')+'</b> '+l.count;
  legend.appendChild(item);
});

const esc = s => s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function hl(s,q){ if(!q) return esc(s);
  const i=s.toLowerCase().indexOf(q); if(i<0) return esc(s);
  return esc(s.slice(0,i))+'<mark>'+esc(s.slice(i,i+q.length))+'</mark>'+esc(s.slice(i+q.length));
}

const sections=document.getElementById('sections');
DATA.layers.forEach(l=>{
  if(!byLayer[l.name] || !byLayer[l.name].length) return;
  const d=document.createElement('details'); d.open=true; d.dataset.layer=l.name;
  d.style.borderLeft='3px solid '+l.color;
  const sum=document.createElement('summary');
  sum.innerHTML='<span class="car">▶</span><span class="ly">'+esc(l.name)+'</span>'
    +'<span class="ds">'+esc(l.desc)+'</span><span class="ct" data-ct>'+l.count+'</span>';
  d.appendChild(sum);
  const list=document.createElement('div'); list.className='list';
  byLayer[l.name].forEach(q=>{
    const c=document.createElement('div'); c.className='card';
    c.dataset.text=(q.text+' '+q.author+' '+q.tags.join(' ')).toLowerCase();
    c.innerHTML='<p class="txt">“<span data-t></span>”</p><div class="by">— <span data-a></span></div>'
      +'<div class="tags">'+q.tags.map(t=>'<span class="tag">'+esc(t)+'</span>').join('')+'</div>';
    c._q=q; list.appendChild(c);
  });
  d.appendChild(list); sections.appendChild(d);
});

const input=document.getElementById('q'), showing=document.getElementById('showing'),
      empty=document.getElementById('empty');
function apply(){
  const raw=input.value.trim().toLowerCase();
  let shown=0, anySection=false;
  document.querySelectorAll('details').forEach(d=>{
    let n=0;
    d.querySelectorAll('.card').forEach(c=>{
      const hit=!raw || c.dataset.text.includes(raw);
      c.hidden=!hit; if(hit){ n++; shown++;
        c.querySelector('[data-t]').innerHTML=hl(c._q.text,raw);
        c.querySelector('[data-a]').innerHTML=hl(c._q.author,raw);
      }
    });
    d.hidden=n===0; if(n>0) anySection=true;
    d.querySelector('[data-ct]').textContent=n;
    if(raw && n>0) d.open=true;
  });
  showing.textContent = raw ? (shown+' match'+(shown===1?'':'es')) : DATA.total+' quotes';
  empty.hidden=anySection;
}
input.addEventListener('input',apply);
input.addEventListener('keydown',e=>{if(e.key==='Escape'){input.value='';apply();}});
sections.addEventListener('click',e=>{
  const t=e.target.closest('.tag'); if(t){ input.value=t.textContent; apply();
    window.scrollTo({top:0,behavior:'smooth'});}
});
const toggle=document.getElementById('toggle');
toggle.addEventListener('click',()=>{
  const open=toggle.textContent.startsWith('collapse');
  document.querySelectorAll('details').forEach(d=>d.open=!open);
  toggle.textContent=open?'expand all':'collapse all';
});
apply();
</script>
</body>
</html>
"""


def main() -> None:
    quotes = json.loads(QUOTES.read_text(encoding="utf-8"))
    total = len(quotes)
    counts = Counter(q.get("layer", "9. Other") for q in quotes)
    layers = [
        {"name": name, "desc": desc, "color": color, "count": counts.get(name, 0)}
        for name, desc, color in LAYERS
    ]
    payload = json.dumps(
        {"quotes": quotes, "layers": layers, "total": total}, ensure_ascii=False
    ).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.replace("__PAYLOAD__", payload), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes) — {total} quotes.")


if __name__ == "__main__":
    main()
