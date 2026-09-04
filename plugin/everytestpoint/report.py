"""Write CSV, JSON, and a self-contained interactive HTML report."""

from __future__ import annotations

import csv
import html
import json
from dataclasses import asdict
from pathlib import Path
from typing import Mapping

from .pcb import BoardData
from .render import RenderGeometry

CATEGORY_COLORS = {
    "Ground": "#38bdf8",
    "Power": "#facc15",
    "Debug": "#c084fc",
    "Analog": "#fb7185",
    "Differential": "#34d399",
    "Signal": "#f97316",
}


def _render_payload(render_geometry: Mapping[str, RenderGeometry] | None) -> dict:
    return {
        side: geometry.to_dict()
        for side, geometry in (render_geometry or {}).items()
    }


def write_json(
    board: BoardData,
    path: Path,
    render_error: str | None = None,
    render_geometry: Mapping[str, RenderGeometry] | None = None,
) -> None:
    payload = board.to_dict()
    payload["render_error"] = render_error
    payload["renders"] = _render_payload(render_geometry)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(board: BoardData, path: Path) -> None:
    fieldnames = list(asdict(board.testpoints[0]).keys()) if board.testpoints else [
        "id", "source_ref", "source_pad", "value", "net", "side", "footprint_side",
        "x_mm", "y_mm", "absolute_x_mm", "absolute_y_mm", "top_left_x_mm",
        "top_left_y_mm", "pad_type", "category", "selection_reason",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(point) for point in board.testpoints)


def write_jigsapp_csv(board: BoardData, path: Path) -> None:
    fields = [
        "source ref des", "source pad", "net", "net class", "side", "x", "y",
        "pad type", "footprint side",
    ]
    origin_x, origin_y = board.aux_origin or (0.0, 0.0)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        for point in board.testpoints:
            writer.writerow(
                {
                    "source ref des": point.source_ref,
                    "source pad": point.source_pad,
                    "net": point.net,
                    "net class": "",
                    "side": point.side.upper(),
                    "x": round(point.absolute_x_mm - origin_x, 4),
                    "y": round(-(point.absolute_y_mm - origin_y), 4),
                    "pad type": point.pad_type,
                    "footprint side": point.footprint_side.upper(),
                }
            )


def _placeholder(side: str) -> str:
    label = "TOP" if side == "top" else "BOTTOM"
    return f"""<svg viewBox="0 0 1200 760" role="img" aria-label="{label} render unavailable">
      <rect width="1200" height="760" rx="28" fill="#13231d" stroke="#386f5a" stroke-width="5"/>
      <path d="M80 80H1120V680H80Z" fill="none" stroke="#4e8f72" stroke-width="2" stroke-dasharray="12 14"/>
      <text x="600" y="365" text-anchor="middle" fill="#d9f99d" font-size="48" font-family="system-ui">{label}</text>
      <text x="600" y="420" text-anchor="middle" fill="#94a3b8" font-size="24" font-family="system-ui">KiCad render unavailable</text>
    </svg>"""


def write_html(
    board: BoardData,
    path: Path,
    renders_available: bool,
    render_error: str | None,
    render_geometry: Mapping[str, RenderGeometry] | None = None,
) -> None:
    payload = board.to_dict()
    payload["colors"] = CATEGORY_COLORS
    payload["renders"] = _render_payload(render_geometry)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(board.name)
    error_banner = (
        f'<div class="warning">3D render failed: {html.escape(render_error or "unknown error")}. '
        "The coordinates and exports were still generated.</div>"
        if render_error else ""
    )
    top_media = '<img src="images/top.png" alt="Top side">' if renders_available else _placeholder("top")
    bottom_media = '<img src="images/bottom.png" alt="Bottom side">' if renders_available else _placeholder("bottom")

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} · Every Test Point</title>
  <style>
    *{{box-sizing:border-box}} :root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;background:#07100d;color:#f8fafc}}
    body{{margin:0;background:radial-gradient(circle at 70% -10%,#183b2d 0,transparent 34rem),#07100d}}
    header{{position:sticky;top:0;z-index:30;padding:16px 22px;border-bottom:1px solid #ffffff18;background:#091510ed;backdrop-filter:blur(16px)}}
    .eyebrow{{color:#86efac;font-size:11px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}} h1{{margin:4px 0 12px;font-size:clamp(20px,3vw,32px)}}
    .stats,.toolbar,.legend{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}} .stat,.chip{{padding:6px 10px;border:1px solid #ffffff1c;border-radius:999px;background:#ffffff0a;color:#cbd5e1;font-size:12px}}
    .toolbar{{margin-top:12px}} input,select,button,a.button{{min-height:38px;padding:8px 12px;border:1px solid #ffffff24;border-radius:10px;background:#0d2119;color:#f8fafc;text-decoration:none}} input{{min-width:min(330px,80vw)}} button{{cursor:pointer}} button.active{{border-color:#4ade80;background:#174a32}}
    main{{padding:18px}} .warning{{margin-bottom:14px;padding:12px 14px;border:1px solid #f59e0b88;border-radius:12px;background:#78350f55;color:#fde68a}}
    .boards{{display:grid;grid-template-columns:repeat(2,minmax(460px,1fr));gap:18px;overflow:auto}} .board-card,.table-card,.detail{{border:1px solid #ffffff17;border-radius:18px;background:#0b1813;box-shadow:0 20px 60px #0006}}
    .board-card{{min-width:460px;padding:14px}} .board-title{{display:flex;justify-content:space-between;margin-bottom:10px;font-size:13px;font-weight:800;color:#d1fae5}}
    .board-view{{position:relative;isolation:isolate}} .board-view>img,.board-view>svg{{display:block;width:100%;height:auto;filter:drop-shadow(0 14px 22px #000a);user-select:none;pointer-events:none}}
    .marker{{position:absolute;z-index:3;display:block;width:14px;height:14px;min-height:0;aspect-ratio:1;margin:-7px 0 0 -7px;padding:0;border:2px solid white;border-radius:50%;background:var(--marker);box-shadow:0 0 0 2px #000b,0 0 14px var(--marker);cursor:pointer;line-height:0;transition:transform .12s}}
    .marker:hover,.marker.selected{{z-index:12;transform:scale(1.6)}} .label{{position:absolute;left:12px;top:-9px;padding:4px 7px;border:1px solid #ffffff32;border-radius:7px;background:#06100df2;font-size:11px;line-height:1.2;white-space:nowrap;opacity:0;pointer-events:none}}
    .marker:hover .label,.marker.selected .label,.show-labels .label{{opacity:1}} .lower{{display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:18px;margin-top:18px}}
    .detail{{padding:16px}} .detail h2{{margin:0 0 12px;font-size:18px}} dl{{display:grid;grid-template-columns:110px 1fr;gap:7px 10px;margin:0;font-size:13px}} dt{{color:#94a3b8}} dd{{margin:0;font-weight:700;overflow-wrap:anywhere}}
    .table-card{{overflow:hidden}} .table-scroll{{max-height:520px;overflow:auto}} table{{width:100%;border-collapse:collapse;font-size:13px}} th{{position:sticky;top:0;z-index:2;padding:10px;text-align:left;background:#10251c;color:#bbf7d0}} td{{padding:9px 10px;border-top:1px solid #ffffff0d}} tr{{cursor:pointer}} tr:hover,tr.selected{{background:#22c55e18}} .side{{text-transform:uppercase;font-size:10px;font-weight:800;letter-spacing:.08em}}
    .footer{{padding:15px 4px 4px;color:#64748b;font-size:11px}} .hidden{{display:none!important}}
    @media(max-width:980px){{.boards{{grid-template-columns:1fr}}.lower{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<header>
  <div class="eyebrow">Every Test Point · KiCad 10</div><h1>{title}</h1>
  <div class="stats"><span class="stat"><b id="visibleCount">{len(board.testpoints)}</b> test points</span><span class="stat">{board.covered_nets} / {board.total_nets} nets covered</span><span class="stat">{board.bounds.width:.2f} × {board.bounds.height:.2f} mm</span></div>
  <div class="toolbar"><input id="search" type="search" placeholder="Search TP, net, value…"><select id="side"><option value="both">Both sides</option><option value="top">Top only</option><option value="bottom">Bottom only</option></select><button id="labels">Show labels</button><a class="button" href="testpoints.csv" download>CSV</a><a class="button" href="jigsapp-testpoints.csv" download>JigsApp CSV</a><a class="button" href="testpoints.json" download>JSON</a></div>
</header>
<main>{error_banner}
  <div class="boards" id="boards">
    <section class="board-card" data-board-side="top"><div class="board-title"><span>TOP / FRONT</span><span>viewed from above</span></div><div class="board-view" id="topBoard">{top_media}</div></section>
    <section class="board-card" data-board-side="bottom"><div class="board-title"><span>BOTTOM / BACK</span><span>X mirrored</span></div><div class="board-view" id="bottomBoard">{bottom_media}</div></section>
  </div>
  <div class="lower">
    <aside class="detail"><h2 id="detailTitle">Select a test point</h2><dl><dt>Net</dt><dd id="dNet">—</dd><dt>Side</dt><dd id="dSide">—</dd><dt>Source</dt><dd id="dSource">—</dd><dt>Value</dt><dd id="dValue">—</dd><dt>Board X / Y</dt><dd id="dXY">—</dd><dt>KiCad X / Y</dt><dd id="dAbs">—</dd><dt>Detected by</dt><dd id="dReason">—</dd></dl><h3>Legend</h3><div class="legend" id="legend"></div></aside>
    <section class="table-card"><div class="table-scroll"><table><thead><tr><th>ID</th><th>Net</th><th>Side</th><th>X, mm</th><th>Y, mm</th><th>Source</th></tr></thead><tbody id="rows"></tbody></table></div></section>
  </div>
  <div class="footer">Coordinates use a Cartesian board-local origin at the lower-left of the Edge.Cuts bounding box. Bottom view mirrors X, matching the physical underside view.</div>
</main>
<script>
const data={payload_json};
const markerMap=new Map(),rowMap=new Map(); let selected=null,showLabels=false;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
function markerSides(p){{return p.side==="both"?["top","bottom"]:[p.side]}}
function position(p,side){{const x=side==="bottom"?data.bounds.width-p.top_left_x_mm:p.top_left_x_mm,g=data.renders[side];if(!g)return{{left:100*x/data.bounds.width,top:100*p.top_left_y_mm/data.bounds.height}};return{{left:100*(g.board_left+g.board_width*x/data.bounds.width)/g.image_width,top:100*(g.board_top+g.board_height*p.top_left_y_mm/data.bounds.height)/g.image_height}}}}
function selectPoint(p){{selected=p.id;document.querySelectorAll(".selected").forEach(n=>n.classList.remove("selected"));(markerMap.get(p.id)||[]).forEach(n=>n.classList.add("selected"));rowMap.get(p.id)?.classList.add("selected");detailTitle.textContent=`${{p.id}} · ${{p.net||"No net"}}`;dNet.textContent=p.net||"—";dSide.textContent=p.side;dSource.textContent=`${{p.source_ref}} / pad ${{p.source_pad||"—"}}`;dValue.textContent=p.value||"—";dXY.textContent=`${{p.x_mm.toFixed(4)}} / ${{p.y_mm.toFixed(4)}} mm`;dAbs.textContent=`${{p.absolute_x_mm.toFixed(4)}} / ${{p.absolute_y_mm.toFixed(4)}} mm`;dReason.textContent=p.selection_reason.replaceAll("_"," ");}}
function build(){{for(const [name,color] of Object.entries(data.colors)){{legend.insertAdjacentHTML("beforeend",`<span class="chip"><i style="width:9px;height:9px;border-radius:50%;background:${{color}}"></i>${{esc(name)}}</span>`)}}for(const p of data.testpoints){{for(const s of markerSides(p)){{const pos=position(p,s),m=document.createElement("button");m.className="marker";m.style.cssText=`left:${{pos.left}}%;top:${{pos.top}}%;--marker:${{data.colors[p.category]}}`;m.dataset.id=p.id;m.dataset.side=s;m.title=`${{p.id}} · ${{p.net}}`;m.innerHTML=`<span class="label">${{esc(p.id)}}<br>${{esc(p.net||p.value)}}</span>`;m.onclick=()=>selectPoint(p);document.getElementById(s+"Board").appendChild(m);markerMap.set(p.id,[...(markerMap.get(p.id)||[]),m])}}const r=document.createElement("tr");r.dataset.id=p.id;r.innerHTML=`<td><b>${{esc(p.id)}}</b></td><td>${{esc(p.net||"—")}}</td><td><span class="side">${{esc(p.side)}}</span></td><td>${{p.x_mm.toFixed(3)}}</td><td>${{p.y_mm.toFixed(3)}}</td><td>${{esc(p.source_ref)}}.${{esc(p.source_pad)}}</td>`;r.onclick=()=>{{selectPoint(p);(markerMap.get(p.id)||[])[0]?.scrollIntoView({{behavior:"smooth",block:"center",inline:"center"}})}};rows.appendChild(r);rowMap.set(p.id,r)}}}}
function filter(){{const q=search.value.trim().toLowerCase(),s=side.value;let count=0;for(const p of data.testpoints){{const matchText=[p.id,p.net,p.value,p.source_ref,p.source_pad,p.category].join(" ").toLowerCase().includes(q);const matchSide=s==="both"||p.side==="both"||p.side===s;const visible=matchText&&matchSide;rowMap.get(p.id).classList.toggle("hidden",!visible);for(const m of markerMap.get(p.id)||[])m.classList.toggle("hidden",!visible||s!=="both"&&m.dataset.side!==s);if(visible)count++}}visibleCount.textContent=count;document.querySelectorAll("[data-board-side]").forEach(card=>card.classList.toggle("hidden",s!=="both"&&card.dataset.boardSide!==s))}}
search.addEventListener("input",filter);side.addEventListener("change",filter);labels.onclick=()=>{{showLabels=!showLabels;boards.classList.toggle("show-labels",showLabels);labels.classList.toggle("active",showLabels);labels.textContent=showLabels?"Hide labels":"Show labels"}};build();filter();
</script></body></html>"""
    path.write_text(document, encoding="utf-8")
