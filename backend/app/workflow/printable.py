"""Print-styled readiness brief (export format html): single column, black on white, no navigation."""
from __future__ import annotations

from html import escape

from ..engine.verdict import OVERALL_LABELS, RESULT_LABELS
from .bundle import build
from .results import PRINCIPLE


def render(case_id: int) -> str:
    b = build(case_id)
    c = b["case"]
    rows = []
    for h in b["hypotheses"]:
        if h.get("removed_reason"):
            continue
        v = h.get("verdict") or {}
        conf = (v.get("confidence") or "").title() if v.get("confidence") not in (None, "none") else "—"
        rows.append(f"<tr><td><b>{escape(h['code'])}</b> {escape(h['text'])}{' <i>(must-have)</i>' if h['must_have'] else ''}"
                    f"</td><td>{escape(h['comparator'])} {escape(h['line_text'])}</td>"
                    f"<td>{escape(RESULT_LABELS.get(v.get('result'), '—'))}</td><td>{conf}</td>"
                    f"<td>{escape(', '.join(v.get('evidence_ids') or []) or '—')}</td></tr>")
    ov = b.get("overall")
    summ = b.get("summary") or {}
    k = b["counts"]
    concl = (b.get("conclusion") or {}).get("text") or ""
    sent = "".join(f"<li>{escape(x['text'])} <span class='ids'>[{escape(', '.join(x['evidence_ids']))}]</span></li>"
                   for x in summ.get("sentences") or [])
    unk = "".join(f"<li><b>{escape(u['idea'])}</b>: {escape(u['text'])}</li>" for u in summ.get("unknowns") or [])
    from datetime import date
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Readiness brief · {escape(c['title'])}</title>
<style>
body{{font-family:"IBM Plex Sans","Segoe UI",Arial,sans-serif;color:#000;background:#fff;max-width:800px;margin:24px auto;padding:0 16px;font-size:14px;line-height:1.5}}
h1{{font-size:22px;margin:0}} h2{{font-size:16px;margin:22px 0 6px;border-bottom:1px solid #000;padding-bottom:3px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #444;padding:5px 7px;text-align:left;vertical-align:top}}
.meta{{color:#333}} .ids{{font-family:"IBM Plex Mono",Consolas,monospace;font-size:12px}} .box{{border:1px solid #000;padding:10px;min-height:80px;white-space:pre-wrap}}
section{{page-break-inside:avoid}} @media print{{h2{{page-break-after:avoid}} .np{{display:none}}}}
</style></head><body>
<p class="np"><button onclick="window.print()">Print or save as PDF</button></p>
<h1>Readiness brief: {escape(c['title'])}</h1>
<p class="meta">{escape(c['client_name'])} · {escape(c['country'])} · {escape(c['industry'])} · {escape(c['function'])} · {date.today().isoformat()}</p>
<p><i>{escape(PRINCIPLE)}</i></p>
<section><h2>The ask</h2><p>{escape(c['raw_ask'])}</p></section>
<section><h2>Results by idea</h2><table><tr><th>Idea</th><th>Pass line</th><th>Result</th><th>Confidence</th><th>Evidence</th></tr>{''.join(rows)}</table>
<p><b>Overall:</b> {escape(OVERALL_LABELS[ov['result']]) + '. ' + escape(ov['rule_applied']) if ov else 'Not added up yet.'}</p></section>
<section><h2>Summary</h2><ul>{sent or '<li>Not written yet.</li>'}</ul></section>
<section><h2>Open gaps</h2><ul>{unk or '<li>None listed.</li>'}</ul></section>
<section><h2>Evidence</h2><p>Collected {k['collected']} · unique {k['unique']} · auto-approved with sources reviewed {k['auto_approved']} · decided by a person {k['decided_by_person']} · rejected {k['rejected']} · pending {k['pending']}</p></section>
<section><h2>Conclusion (written by the consultant)</h2><div class="box">{escape(concl) or '&nbsp;'}</div></section>
{'<p><i>Sample data (simulated).</i></p>' if c.get('sample') else ''}
</body></html>"""
