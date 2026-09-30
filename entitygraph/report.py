"""Generate a portable, escaped HTML report from actual pipeline output."""
from html import escape


def render(graph):
    e = lambda value: escape(str(value), quote=True)
    cards = "".join(f'<article><strong>{len(graph[key])}</strong><span>{key}</span></article>'
                    for key in ["documents", "mentions", "entities", "transactions"])
    rows = "".join(f'<tr><td>{e(m["text"])}</td><td>{e(m["label"])}</td><td>{e(m["canonical"])}</td>'
                   f'<td>{e(m["document_id"])} · {m["start"]}:{m["end"]}</td></tr>' for m in graph["mentions"])
    names = {v["id"]: v["name"] for v in graph["entities"]}
    payments = "".join(f'<li>{e(names[t["source_id"]])} → {e(names[t["target_id"]])}'
                       f' <b>USD {e(t["amount"])}</b> <small>{e(t["document_id"])}</small></li>' for t in graph["transactions"])
    documents = "".join(f'<details><summary>{e(d["id"])}</summary><pre>{e(d["text"])}</pre></details>' for d in graph["documents"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>EntityGraph | Evidence explorer</title><style>
body{{font:16px system-ui;background:#0d1424;color:#e3ebf9;max-width:1150px;margin:auto;padding:40px 24px}}
h1{{font-size:48px;margin:8px 0}}p,small{{color:#9eb0cc}}.cards{{display:flex;gap:16px;flex-wrap:wrap;margin:32px 0}}
article{{background:#18243a;border:1px solid #30405c;padding:24px;flex:1;border-radius:12px}}strong{{display:block;font-size:36px;color:#67e8c5}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #30405c}}
input{{padding:12px;width:90%;background:#18243a;color:white;border:1px solid #536789;border-radius:8px}}li{{padding:12px}}pre{{white-space:pre-wrap}}details{{padding:14px;background:#18243a;margin:8px 0}}.scroll{{overflow:auto}}
</style><p>ENTITYGRAPH / SOURCE EVIDENCE</p><h1>From documents to connections.</h1>
<p>Extraction: {e(graph["extraction_mode"])}. Scores describe extraction only, not identity confidence.</p>
<div class="cards">{cards}</div><h2>Explicit payments</h2><ul>{payments}</ul>
<h2>Mention lineage</h2><input id="filter" aria-label="Filter mentions" placeholder="Filter by entity, type, or source…">
<div class="scroll"><table><thead><tr><th>Source text</th><th>Type</th><th>Resolved name</th><th>Evidence offsets</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Source documents</h2>{documents}<script>document.getElementById('filter').addEventListener('input',function(){{for(const row of document.querySelectorAll('tbody tr'))row.hidden=!row.textContent.toLowerCase().includes(this.value.toLowerCase())}})</script></html>'''
