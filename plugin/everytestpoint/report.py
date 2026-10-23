"""Write CSV, JSON, and a self-contained interactive HTML report."""

from __future__ import annotations

import base64
import csv
import html
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Mapping

from .dft import calculate_probe_pairs
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
    generated_at: str | None = None,
) -> None:
    payload = board.to_dict()
    payload["generated_at"] = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    payload["render_error"] = render_error
    payload["renders"] = _render_payload(render_geometry)
    payload["dft_pairs"] = [pair.to_dict() for pair in calculate_probe_pairs(board)]
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


def write_dft_csv(board: BoardData, path: Path) -> None:
    fields = ["point_a", "net_a", "point_b", "net_b", "sides", "distance_mm"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for pair in calculate_probe_pairs(board):
            values = pair.to_dict()
            values["sides"] = ",".join(values["sides"])
            writer.writerow(values)


def _placeholder(side: str) -> str:
    label = "TOP" if side == "top" else "BOTTOM"
    return f"""<svg viewBox="0 0 1200 760" role="img" aria-label="{label} render unavailable">
      <rect width="1200" height="760" rx="28" fill="#13231d" stroke="#386f5a" stroke-width="5"/>
      <path d="M80 80H1120V680H80Z" fill="none" stroke="#4e8f72" stroke-width="2" stroke-dasharray="12 14"/>
      <text x="600" y="365" text-anchor="middle" fill="#d9f99d" font-size="48" font-family="system-ui">{label}</text>
      <text x="600" y="420" text-anchor="middle" fill="#94a3b8" font-size="24" font-family="system-ui">KiCad render unavailable</text>
    </svg>"""


def _everypin_logo() -> str:
    """Return the official wordmark inline so the report stays self-contained."""
    logo = Path(__file__).with_name("everypin-logo.svg").read_text(encoding="utf-8")
    logo = logo.replace(
        "<svg ",
        '<svg role="img" aria-label="Everypin" ',
        1,
    )
    return logo.replace(
        'width="619" height="269" viewBox="0 0 619 269"',
        'width="459" height="109" viewBox="80 80 459 109"',
        1,
    )


def _golos_text_font_data() -> str:
    """Return the bundled variable font as a data URI payload."""
    font = Path(__file__).with_name("GolosText-Variable.ttf").read_bytes()
    return base64.b64encode(font).decode("ascii")


def write_html(
    board: BoardData,
    path: Path,
    renders_available: bool,
    render_error: str | None,
    render_geometry: Mapping[str, RenderGeometry] | None = None,
    generated_at: str | None = None,
) -> None:
    generated_at = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    payload = board.to_dict()
    payload["generated_at"] = generated_at
    payload["colors"] = CATEGORY_COLORS
    payload["renders"] = _render_payload(render_geometry)
    payload["dft_pairs"] = [pair.to_dict() for pair in calculate_probe_pairs(board)]
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(board.name)
    revision = html.escape(board.revision or "—")
    try:
        generated_label = datetime.fromisoformat(generated_at).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        generated_label = generated_at.replace("T", " ")
    generated_label = html.escape(generated_label)
    logo_svg = _everypin_logo()
    golos_text_data = _golos_text_font_data()
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
  <title>{title} · Everypin</title>
  <style>
    @font-face{{font-family:"Golos Text";src:url("data:font/ttf;base64,{golos_text_data}") format("truetype");font-style:normal;font-weight:400 900;font-display:swap}}
    *{{box-sizing:border-box;font-family:"Golos Text",ui-sans-serif,system-ui,sans-serif}} :root{{color-scheme:dark;background:#07100d;color:#f8fafc}}
    body{{margin:0;background:radial-gradient(circle at 70% -10%,#183b2d 0,transparent 34rem),#07100d}}
    header{{position:sticky;top:0;z-index:30;padding:16px 22px;border-bottom:1px solid #ffffff18;background:#091510ed;backdrop-filter:blur(16px)}}
    .brand-logo{{width:152px;margin-bottom:8px}} .brand-logo svg{{display:block;width:100%;height:auto}} .title-row{{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline}} .title-row h1{{margin:4px 0 6px;font-size:clamp(20px,3vw,32px)}} .report-kind{{color:#86efac;font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}}
    .report-meta{{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:12px;color:#94a3b8;font-size:12px}} .report-meta span{{display:flex;gap:6px;align-items:baseline}} .report-meta b{{color:#d1fae5;font-variant-numeric:tabular-nums}}
    .stats,.toolbar,.legend,.tabs{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}} .stat,.chip{{padding:6px 10px;border:1px solid #ffffff1c;border-radius:999px;background:#ffffff0a;color:#cbd5e1;font-size:12px}}
    .tabs{{margin-top:13px;border-bottom:1px solid #ffffff16}} .tab{{border:0;border-bottom:2px solid transparent;border-radius:9px 9px 0 0;background:transparent;color:#94a3b8;font-weight:800}} .tab.active{{border-bottom-color:#4ade80;background:#153c2b;color:#dcfce7}}
    .toolbar{{margin-top:10px}} .toolbar label{{display:flex;gap:7px;align-items:center;color:#94a3b8;font-size:12px}} input,select,button,a.button{{min-height:38px;padding:8px 12px;border:1px solid #ffffff24;border-radius:10px;background:#0d2119;color:#f8fafc;text-decoration:none}} input{{min-width:min(330px,80vw)}} input.compact{{min-width:0;width:105px}} button{{cursor:pointer}} button.active{{border-color:#4ade80;background:#174a32}}
    main{{padding:18px}} .warning{{margin-bottom:14px;padding:12px 14px;border:1px solid #f59e0b88;border-radius:12px;background:#78350f55;color:#fde68a}}
    .boards{{display:grid;grid-template-columns:repeat(2,minmax(460px,1fr));gap:18px;overflow:auto}} .board-card,.table-card,.detail{{border:1px solid #ffffff17;border-radius:18px;background:#0b1813;box-shadow:0 20px 60px #0006}}
    .board-card{{min-width:460px;padding:14px}} .board-title{{display:flex;justify-content:space-between;margin-bottom:10px;font-size:13px;font-weight:800;color:#d1fae5}}
    .board-view{{position:relative;isolation:isolate}} .board-view>img,.board-view>svg{{display:block;width:100%;height:auto;filter:drop-shadow(0 14px 22px #000a);user-select:none;pointer-events:none}}
    .marker{{position:absolute;z-index:3;display:block;width:14px;height:14px;min-height:0;aspect-ratio:1;margin:-7px 0 0 -7px;padding:0;border:2px solid white;border-radius:50%;background:var(--marker);box-shadow:0 0 0 2px #000b,0 0 14px var(--marker);cursor:pointer;line-height:0;transition:transform .12s}}
    .marker:hover,.marker.selected{{z-index:12;transform:scale(1.6)}} .label{{position:absolute;left:12px;top:-9px;padding:4px 7px;border:1px solid #ffffff32;border-radius:7px;background:#06100df2;font-size:11px;line-height:1.2;white-space:nowrap;opacity:0;pointer-events:none}}
    .marker:hover .label,.marker.selected .label,.show-labels .label{{opacity:1}} .lower{{display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:18px;margin-top:18px}}
    .detail{{padding:16px}} .detail h2{{margin:0 0 12px;font-size:18px}} dl{{display:grid;grid-template-columns:110px 1fr;gap:7px 10px;margin:0;font-size:13px}} dt{{color:#94a3b8}} dd{{margin:0;font-weight:700;overflow-wrap:anywhere}}
    .table-card{{overflow:hidden}} .table-scroll{{max-height:520px;overflow:auto}} table{{width:100%;border-collapse:collapse;font-size:13px}} th{{position:sticky;top:0;z-index:2;padding:10px;text-align:left;background:#10251c;color:#bbf7d0}} td{{padding:9px 10px;border-top:1px solid #ffffff0d}} tr{{cursor:pointer}} tr:hover,tr.selected{{background:#22c55e18}} .side{{text-transform:uppercase;font-size:10px;font-weight:800;letter-spacing:.08em}}
    .dft-board-card{{max-width:900px;margin:0 auto 18px}} .dft-overlay{{position:absolute;inset:0;z-index:2;width:100%;height:100%;filter:none!important;pointer-events:none}} .dft-overlay line{{stroke:#ef4444;stroke-width:2;vector-effect:non-scaling-stroke;opacity:.72}} .dft-marker{{z-index:4}} .dft-marker.conflict{{background:#ef4444!important;box-shadow:0 0 0 2px #450a0a,0 0 16px #ef4444}} .dft-marker:not(.conflict){{opacity:.72}} tr.conflict{{background:#7f1d1d88;color:#fee2e2}} tr.conflict:hover,tr.conflict.selected{{background:#991b1bcc}} .distance{{font-variant-numeric:tabular-nums;font-weight:800}} .negative{{color:#fca5a5}} .positive{{color:#86efac}} .dft-summary{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}} .dft-note{{margin:10px 2px 16px;color:#94a3b8;font-size:12px}}
    .footer{{padding:15px 4px 4px;color:#64748b;font-size:11px}} .hidden{{display:none!important}}
    @media(max-width:980px){{.boards{{grid-template-columns:1fr}}.lower{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<header>
  <div class="brand-logo">{logo_svg}</div>
  <div class="title-row"><h1>{title}</h1><span class="report-kind">Test point report</span></div>
  <div class="report-meta"><span>Revision <b>{revision}</b></span><span>Date <b>{generated_label}</b></span></div>
  <div class="stats"><span class="stat"><b id="visibleCount">{len(board.testpoints)}</b> test points</span><span class="stat">{board.covered_nets} / {board.total_nets} nets covered</span><span class="stat">{board.bounds.width:.2f} × {board.bounds.height:.2f} mm</span></div>
  <nav class="tabs"><button class="tab active" data-tab="map">Test points</button><button class="tab" data-tab="dft">DFT spacing</button></nav>
  <div class="toolbar" id="mapToolbar"><input id="search" type="search" placeholder="Search TP, net, value…"><select id="side"><option value="both">Both sides</option><option value="top">Top only</option><option value="bottom">Bottom only</option></select><button id="labels">Show labels</button><a class="button" href="testpoints.csv" download>CSV</a><a class="button" href="jigsapp-testpoints.csv" download>JigsApp CSV</a><a class="button" href="testpoints.json" download>JSON</a></div>
  <div class="toolbar hidden" id="dftToolbar"><label>Probe pitch <select id="pogoPreset"><option value="1.27">1.27 mm</option><option value="1.91">1.91 mm</option><option value="2.54" selected>2.54 mm</option><option value="3.18">3.18 mm</option><option value="5.08">5.08 mm</option><option value="">Custom</option></select></label><label>Minimum <input class="compact" id="pogoPitch" type="number" min="0.01" step="0.01" value="2.54"> mm</label><label>Fixture side <select id="dftSide"><option value="top">Top</option><option value="bottom">Bottom</option></select></label><a class="button" href="dft-distances.csv" download>DFT CSV</a></div>
</header>
<main>{error_banner}
  <section id="mapPanel">
  <div class="boards" id="boards">
    <section class="board-card" data-board-side="top"><div class="board-title"><span>TOP / FRONT</span><span>viewed from above</span></div><div class="board-view" id="topBoard">{top_media}</div></section>
    <section class="board-card" data-board-side="bottom"><div class="board-title"><span>BOTTOM / BACK</span><span>X mirrored</span></div><div class="board-view" id="bottomBoard">{bottom_media}</div></section>
  </div>
  <div class="lower">
    <aside class="detail"><h2 id="detailTitle">Select a test point</h2><dl><dt>Net</dt><dd id="dNet">—</dd><dt>Side</dt><dd id="dSide">—</dd><dt>Source</dt><dd id="dSource">—</dd><dt>Value</dt><dd id="dValue">—</dd><dt>Board X / Y</dt><dd id="dXY">—</dd><dt>KiCad X / Y</dt><dd id="dAbs">—</dd><dt>Detected by</dt><dd id="dReason">—</dd></dl><h3>Legend</h3><div class="legend" id="legend"></div></aside>
    <section class="table-card"><div class="table-scroll"><table><thead><tr><th>ID</th><th>Net</th><th>Side</th><th>X, mm</th><th>Y, mm</th><th>Source</th></tr></thead><tbody id="rows"></tbody></table></div></section>
  </div>
  <div class="footer">Coordinates use a Cartesian board-local origin at the lower-left of the Edge.Cuts bounding box. Bottom view mirrors X, matching the physical underside view.</div>
  </section>
  <section class="hidden" id="dftPanel">
    <div class="dft-summary"><span class="stat"><b id="dftPairCount">0</b> probe pairs</span><span class="stat"><b id="dftConflictCount">0</b> below pitch</span><span class="stat">minimum <b id="dftMinimum">—</b></span></div>
    <p class="dft-note">Center-to-center spacing is evaluated only for probes that can be installed on the selected fixture side. Red lines, points, and rows are below the selected pogo-pin pitch.</p>
    <section class="board-card dft-board-card" id="dftTopCard"><div class="board-title"><span>DFT · TOP / FRONT</span><span>viewed from above</span></div><div class="board-view" id="dftTopBoard">{top_media}</div></section>
    <section class="board-card dft-board-card hidden" id="dftBottomCard"><div class="board-title"><span>DFT · BOTTOM / BACK</span><span>X mirrored</span></div><div class="board-view" id="dftBottomBoard">{bottom_media}</div></section>
    <section class="table-card"><div class="table-scroll"><table><thead><tr><th>Point A</th><th>Net A</th><th>Point B</th><th>Net B</th><th>Side</th><th>Distance</th><th>Pitch margin</th></tr></thead><tbody id="dftRows"></tbody></table></div></section>
    <div class="footer">Distance is Euclidean center-to-center spacing in board coordinates. A negative pitch margin means the selected pogo-pin spacing cannot be maintained.</div>
  </section>
</main>
<script>
const data={payload_json};
const $=id=>document.getElementById(id),pointsById=new Map(data.testpoints.map(p=>[p.id,p]));
const markerMap=new Map(),rowMap=new Map(),dftMarkerMap=new Map(),dftPairRows=[];let selected=null,showLabels=false;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
function markerSides(p){{return p.side==="both"?["top","bottom"]:[p.side]}}
function position(p,side){{const x=side==="bottom"?data.bounds.width-p.top_left_x_mm:p.top_left_x_mm,g=data.renders[side];if(!g)return{{left:100*x/data.bounds.width,top:100*p.top_left_y_mm/data.bounds.height}};return{{left:100*(g.board_left+g.board_width*x/data.bounds.width)/g.image_width,top:100*(g.board_top+g.board_height*p.top_left_y_mm/data.bounds.height)/g.image_height}}}}
function pixelPosition(p,side){{const x=side==="bottom"?data.bounds.width-p.top_left_x_mm:p.top_left_x_mm,g=data.renders[side]||{{image_width:1200,image_height:760,board_left:0,board_top:0,board_width:1200,board_height:760}};return{{x:g.board_left+g.board_width*x/data.bounds.width,y:g.board_top+g.board_height*p.top_left_y_mm/data.bounds.height}}}}
function selectPoint(p){{selected=p.id;document.querySelectorAll("#mapPanel .selected").forEach(n=>n.classList.remove("selected"));(markerMap.get(p.id)||[]).forEach(n=>n.classList.add("selected"));rowMap.get(p.id)?.classList.add("selected");$("detailTitle").textContent=`${{p.id}} · ${{p.net||"No net"}}`;$("dNet").textContent=p.net||"—";$("dSide").textContent=p.side;$("dSource").textContent=`${{p.source_ref}} / pad ${{p.source_pad||"—"}}`;$("dValue").textContent=p.value||"—";$("dXY").textContent=`${{p.x_mm.toFixed(4)}} / ${{p.y_mm.toFixed(4)}} mm`;$("dAbs").textContent=`${{p.absolute_x_mm.toFixed(4)}} / ${{p.absolute_y_mm.toFixed(4)}} mm`;$("dReason").textContent=p.selection_reason.replaceAll("_"," ");}}
function buildMap(){{for(const [name,color] of Object.entries(data.colors)){{$("legend").insertAdjacentHTML("beforeend",`<span class="chip"><i style="width:9px;height:9px;border-radius:50%;background:${{color}}"></i>${{esc(name)}}</span>`)}}for(const p of data.testpoints){{for(const s of markerSides(p)){{const pos=position(p,s),m=document.createElement("button");m.className="marker";m.style.cssText=`left:${{pos.left}}%;top:${{pos.top}}%;--marker:${{data.colors[p.category]}}`;m.dataset.id=p.id;m.dataset.side=s;m.title=`${{p.id}} · ${{p.net}}`;m.innerHTML=`<span class="label">${{esc(p.id)}}<br>${{esc(p.net||p.value)}}</span>`;m.onclick=()=>selectPoint(p);$(s+"Board").appendChild(m);markerMap.set(p.id,[...(markerMap.get(p.id)||[]),m])}}const r=document.createElement("tr");r.dataset.id=p.id;r.innerHTML=`<td><b>${{esc(p.id)}}</b></td><td>${{esc(p.net||"—")}}</td><td><span class="side">${{esc(p.side)}}</span></td><td>${{p.x_mm.toFixed(3)}}</td><td>${{p.y_mm.toFixed(3)}}</td><td>${{esc(p.source_ref)}}.${{esc(p.source_pad)}}</td>`;r.onclick=()=>{{selectPoint(p);(markerMap.get(p.id)||[])[0]?.scrollIntoView({{behavior:"smooth",block:"center",inline:"center"}})}};$("rows").appendChild(r);rowMap.set(p.id,r)}}}}
function filterMap(){{const q=$("search").value.trim().toLowerCase(),s=$("side").value;let count=0;for(const p of data.testpoints){{const matchText=[p.id,p.net,p.value,p.source_ref,p.source_pad,p.category].join(" ").toLowerCase().includes(q);const matchSide=s==="both"||p.side==="both"||p.side===s;const visible=matchText&&matchSide;rowMap.get(p.id).classList.toggle("hidden",!visible);for(const m of markerMap.get(p.id)||[])m.classList.toggle("hidden",!visible||s!=="both"&&m.dataset.side!==s);if(visible)count++}}$("visibleCount").textContent=count;document.querySelectorAll("[data-board-side]").forEach(card=>card.classList.toggle("hidden",s!=="both"&&card.dataset.boardSide!==s))}}
function pairKey(pair){{return `${{pair.point_a}}|${{pair.point_b}}`}}
function selectDftPair(pair,row){{document.querySelectorAll("#dftPanel .selected").forEach(n=>n.classList.remove("selected"));row.classList.add("selected");const side=$("dftSide").value;for(const id of [pair.point_a,pair.point_b])dftMarkerMap.get(`${{side}}|${{id}}`)?.classList.add("selected")}}
function buildDft(){{for(const side of ["top","bottom"]){{const board=$(side==="top"?"dftTopBoard":"dftBottomBoard"),g=data.renders[side]||{{image_width:1200,image_height:760}},svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.classList.add("dft-overlay");svg.dataset.side=side;svg.setAttribute("viewBox",`0 0 ${{g.image_width}} ${{g.image_height}}`);svg.setAttribute("preserveAspectRatio","none");board.appendChild(svg);for(const p of data.testpoints.filter(point=>markerSides(point).includes(side))){{const pos=position(p,side),m=document.createElement("button");m.className="marker dft-marker";m.style.cssText=`left:${{pos.left}}%;top:${{pos.top}}%;--marker:${{data.colors[p.category]}}`;m.title=`${{p.id}} · ${{p.net}}`;m.innerHTML=`<span class="label">${{esc(p.id)}}<br>${{esc(p.net||p.value)}}</span>`;board.appendChild(m);dftMarkerMap.set(`${{side}}|${{p.id}}`,m)}}}}for(const pair of data.dft_pairs){{const row=document.createElement("tr");row.dataset.sides=pair.sides.join(" ");row.innerHTML=`<td><b>${{esc(pair.point_a)}}</b></td><td>${{esc(pair.net_a||"—")}}</td><td><b>${{esc(pair.point_b)}}</b></td><td>${{esc(pair.net_b||"—")}}</td><td><span class="side">${{esc(pair.sides.join(", "))}}</span></td><td class="distance">${{pair.distance_mm.toFixed(4)}} mm</td><td class="margin"></td>`;row.onclick=()=>selectDftPair(pair,row);$("dftRows").appendChild(row);dftPairRows.push([pair,row])}}}}
function updateDft(){{const pitch=Math.max(0,Number($("pogoPitch").value)||0),side=$("dftSide").value,visible=data.dft_pairs.filter(pair=>pair.sides.includes(side)),conflicts=visible.filter(pair=>pair.distance_mm<pitch),conflictingPoints=new Set(conflicts.flatMap(pair=>[pair.point_a,pair.point_b]));$("dftPairCount").textContent=visible.length;$("dftConflictCount").textContent=conflicts.length;$("dftMinimum").textContent=visible.length?`${{Math.min(...visible.map(pair=>pair.distance_mm)).toFixed(4)}} mm`:"—";$("dftTopCard").classList.toggle("hidden",side!=="top");$("dftBottomCard").classList.toggle("hidden",side!=="bottom");for(const [pair,row] of dftPairRows){{const shown=pair.sides.includes(side),margin=pair.distance_mm-pitch;row.classList.toggle("hidden",!shown);row.classList.toggle("conflict",shown&&margin<0);const cell=row.querySelector(".margin");cell.textContent=`${{margin>=0?"+":""}}${{margin.toFixed(4)}} mm`;cell.className=`margin ${{margin<0?"negative":"positive"}}`}}for(const [key,marker] of dftMarkerMap){{const [markerSide,id]=key.split("|");marker.classList.toggle("conflict",markerSide===side&&conflictingPoints.has(id))}}const svg=document.querySelector(`.dft-overlay[data-side="${{side}}"]`);svg.replaceChildren();for(const pair of conflicts){{const a=pixelPosition(pointsById.get(pair.point_a),side),b=pixelPosition(pointsById.get(pair.point_b),side),line=document.createElementNS("http://www.w3.org/2000/svg","line");line.setAttribute("x1",a.x);line.setAttribute("y1",a.y);line.setAttribute("x2",b.x);line.setAttribute("y2",b.y);svg.appendChild(line)}}}}
function activateTab(name){{const dft=name==="dft";$("mapPanel").classList.toggle("hidden",dft);$("dftPanel").classList.toggle("hidden",!dft);$("mapToolbar").classList.toggle("hidden",dft);$("dftToolbar").classList.toggle("hidden",!dft);document.querySelectorAll(".tab").forEach(tab=>tab.classList.toggle("active",tab.dataset.tab===name));if(dft)updateDft()}}
$("search").addEventListener("input",filterMap);$("side").addEventListener("change",filterMap);$("labels").onclick=()=>{{showLabels=!showLabels;$("boards").classList.toggle("show-labels",showLabels);$("labels").classList.toggle("active",showLabels);$("labels").textContent=showLabels?"Hide labels":"Show labels"}};$("pogoPreset").addEventListener("change",()=>{{if($("pogoPreset").value)$("pogoPitch").value=$("pogoPreset").value;updateDft()}});$("pogoPitch").addEventListener("input",()=>{{const match=[...$("pogoPreset").options].find(option=>option.value&&Number(option.value)===Number($("pogoPitch").value));$("pogoPreset").value=match?.value||"";updateDft()}});$("dftSide").addEventListener("change",updateDft);document.querySelectorAll(".tab").forEach(tab=>tab.onclick=()=>activateTab(tab.dataset.tab));buildMap();buildDft();const sideCounts={{top:data.testpoints.filter(p=>markerSides(p).includes("top")).length,bottom:data.testpoints.filter(p=>markerSides(p).includes("bottom")).length}};$("dftSide").value=sideCounts.bottom>=sideCounts.top?"bottom":"top";filterMap();updateDft();
</script></body></html>"""
    path.write_text(document, encoding="utf-8")
