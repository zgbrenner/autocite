from __future__ import annotations

from typing import Any

WORKSPACE_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AutoCite Workspace</title>
<style>:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#171717;background:#f7f7f5}*{box-sizing:border-box}body{margin:0;padding:16px}.shell{max-width:1100px;margin:auto}.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.title{font-size:20px;font-weight:700}.badge{padding:4px 9px;border-radius:999px;background:#e7e7e2;font-size:12px}.controls{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.card{background:#fff;border:1px solid #dddcd5;border-radius:12px;padding:14px}.wide{grid-column:1/-1}.label{font-size:12px;font-weight:700;text-transform:uppercase;color:#666;margin-bottom:7px}pre{white-space:pre-wrap;word-break:break-word;max-height:360px;overflow:auto;margin:0;font:13px/1.5 ui-monospace,monospace}button,select{border:1px solid #c9c8c0;background:#fff;border-radius:8px;padding:7px 10px;cursor:pointer}button.primary{background:#1f2937;color:#fff}.finding{border-top:1px solid #ecebe5;padding:10px 0}.finding:first-child{border-top:0}.meta{font-size:12px;color:#666}.actions{display:flex;gap:6px;margin-top:7px}.accepted{border-left:4px solid #208b57;padding-left:8px}.rejected{opacity:.55;text-decoration:line-through}.empty{color:#666;font-style:italic}@media(max-width:760px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}}</style></head>
<body><div class="shell"><div class="top"><div><div class="title">AutoCite Citecheck Workspace</div><div class="meta">Evidence-backed review; legal judgment remains with the user.</div></div><span id="mode" class="badge">Waiting</span></div>
<div class="controls"><select id="filter"><option value="all">All findings</option><option value="edit">Proposed edits</option><option value="issue">Unresolved issues</option><option value="evidence">Source evidence</option></select><button id="copy" class="primary">Copy corrected text</button><button id="acceptAll">Accept all edits</button><button id="rejectAll">Reject all edits</button></div>
<div class="grid"><section class="card"><div class="label">Original</div><pre id="original">Waiting for tool result.</pre></section><section class="card"><div class="label">Selected result</div><pre id="corrected"></pre></section><section class="card wide"><div class="label">Findings</div><div id="findings" class="empty">No findings loaded.</div></section></div></div>
<script>
const state={payload:null,decisions:new Map()};const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function selectedText(){const p=state.payload||{},original=p.original_text||'',edits=[...(p.applied_edits||[])].sort((a,b)=>b.start-a.start);let out=original;edits.forEach((e,i)=>{const id='a'+i;if(state.decisions.get(id)==='rejected')return;out=out.slice(0,e.start)+(e.suggestion??e.original??'')+out.slice(e.end)});return edits.length?out:(p.corrected_text||original)}
function setDecision(id,value){state.decisions.set(id,value);renderFindings();$('corrected').textContent=selectedText()}
function findingRows(){const p=state.payload||{},rows=[];[...(p.applied_edits||[])].sort((a,b)=>b.start-a.start).forEach((x,i)=>rows.push({id:'a'+i,type:'edit',title:x.code||'Proposed edit',detail:`${x.original||''} → ${x.suggestion||''}`,meta:x.rule||'',suggestion:x.message||''}));(p.issues||[]).forEach((x,i)=>rows.push({id:'i'+i,type:'issue',title:x.code||'Citation issue',detail:x.message||'',meta:x.rule||'',suggestion:x.suggestion||''}));(((p.deep_review_results||{}).cases)||[]).forEach((x,i)=>{const a=x.authority||{},e=x.evidence||{},q=e.quotation||{},pin=e.pincite||{},prop=e.proposition||{};rows.push({id:'e'+i,type:'evidence',title:a.case_name||'Case authority',detail:[`Quotation: ${q.status||'not reviewed'}`,`Pincite: ${pin.status||'not reviewed'}`,'Proposition: legal judgment required'].join(' · '),meta:a.source_url||'',suggestion:(prop.candidate_passages||[])[0]?.passage||''})});return rows}
function renderFindings(){const f=$('filter').value,rows=findingRows().filter(r=>f==='all'||r.type===f);if(!rows.length){$('findings').innerHTML='<div class="empty">No findings for this filter.</div>';return}$('findings').innerHTML=rows.map(r=>{const d=state.decisions.get(r.id)||((r.type==='edit')?'accepted':'');const actions=r.type==='edit'?`<div class="actions"><button data-id="${r.id}" data-action="accepted">Accept</button><button data-id="${r.id}" data-action="rejected">Reject</button></div>`:'';return `<article class="finding ${d}"><strong>${esc(r.title)}</strong><div>${esc(r.detail)}</div>${r.suggestion?`<div class="meta">${esc(r.suggestion)}</div>`:''}${r.meta?`<div class="meta">${esc(r.meta)}</div>`:''}${actions}</article>`}).join('');document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>setDecision(b.dataset.id,b.dataset.action))}
function render(payload){state.payload=payload||{};state.decisions.clear();$('mode').textContent=(payload.summary||{}).mode||payload.mode||'unknown';$('original').textContent=payload.original_text||'';$('corrected').textContent=selectedText();renderFindings()}
$('filter').onchange=renderFindings;$('copy').onclick=async()=>{await navigator.clipboard.writeText(selectedText());$('copy').textContent='Copied';setTimeout(()=>$('copy').textContent='Copy corrected text',1200)};$('acceptAll').onclick=()=>{findingRows().filter(r=>r.type==='edit').forEach(r=>state.decisions.set(r.id,'accepted'));renderFindings();$('corrected').textContent=selectedText()};$('rejectAll').onclick=()=>{findingRows().filter(r=>r.type==='edit').forEach(r=>state.decisions.set(r.id,'rejected'));renderFindings();$('corrected').textContent=selectedText()};
window.addEventListener('message',event=>{if(event.source!==window.parent)return;const msg=event.data;if(!msg||msg.jsonrpc!=='2.0'||msg.method!=='ui/notifications/tool-result')return;render(msg.params?.structuredContent||msg.params?.content||msg.params||{})},{passive:true});
</script></body></html>'''


def workspace_payload(review: dict[str, Any]) -> dict[str, Any]:
    """Return bounded data needed by the interactive workspace and host model."""
    original = str(review.get("original_text") or "")
    corrected = str(review.get("corrected_text") or "")
    return {
        "summary": {
            "mode": review.get("mode"),
            "applied_edit_count": len(review.get("applied_edits") or []),
            "remaining_issue_count": len(review.get("remaining_issues") or []),
            "deep_case_count": len(
                ((review.get("deep_review_results") or {}).get("cases") or [])
            ),
        },
        "original_text": original[:100_000],
        "corrected_text": corrected[:100_000],
        "issues": list(review.get("remaining_issues") or [])[:500],
        "applied_edits": list(review.get("applied_edits") or [])[:500],
        "deep_review_results": review.get("deep_review_results") or {},
        "response_contract": review.get("response_contract") or [],
    }
