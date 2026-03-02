"""2G/3G/4G/5G Spectrum Band Identifier.

Complete cellular frequency band database with identification, comparison, and analysis.

API:
    GET  /api/v1/bands                       - All bands (filterable by gen)
    GET  /api/v1/bands/{gen}                 - Bands for generation (2G/3G/4G/5G)
    GET  /api/v1/identify?freq=3500          - Identify band by frequency
    GET  /api/v1/search?q=middle+east        - Search bands
    GET  /api/v1/compare                     - Compare all generations
    GET  /api/v1/overlaps                    - Find band overlaps across gens
    GET  /api/v1/region/{name}               - Bands for a region
    GET  /api/v1/stats                       - Database statistics
    GET  /                                   - Interactive explorer
"""

import logging
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from bands.spectrum_db import (
    get_all_bands, get_bands_by_generation, identify_band_by_frequency, search_bands
)
from analyzer.frequency_analyzer import (
    get_generation_summary, find_band_overlaps, compare_generations, get_bands_for_region
)

logging.basicConfig(level="INFO", format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="2G/3G/4G/5G Spectrum Band Identifier", version="1.0.0")

@app.on_event("startup")
async def startup():
    total = len(get_all_bands())
    logger.info("Spectrum Band Identifier started | %d bands loaded | Port 8005" % total)


@app.get("/api/v1/bands")
async def list_bands(generation: str = None):
    """List all bands, optionally filtered by generation."""
    if generation:
        bands = get_bands_by_generation(generation)
        return {"generation": generation, "count": len(bands), "bands": [b.to_dict() for b in bands]}
    all_b = get_all_bands()
    return {"count": len(all_b), "bands": [b.to_dict() for b in all_b]}


@app.get("/api/v1/bands/{generation}")
async def bands_by_generation(generation: str):
    """Get detailed summary for a generation (2G, 3G, 4G, 5G)."""
    return get_generation_summary(generation.upper())


@app.get("/api/v1/identify")
async def identify_frequency(freq: float = Query(..., description="Frequency in MHz")):
    """Identify which band(s) a frequency belongs to."""
    matches = identify_band_by_frequency(freq)
    return {
        "frequency_mhz": freq,
        "matches_found": len(matches),
        "bands": matches,
        "note": "Frequency may belong to multiple bands across generations" if len(matches) > 1 else "",
    }


@app.get("/api/v1/search")
async def search(q: str = Query(..., description="Search query (band name, region, etc)")):
    """Search bands by name, region, or description."""
    results = search_bands(q)
    return {"query": q, "results_found": len(results), "bands": results}


@app.get("/api/v1/compare")
async def compare():
    """Compare spectrum allocation across all generations."""
    return compare_generations()


@app.get("/api/v1/overlaps")
async def overlaps():
    """Find frequency overlaps between different generations."""
    o = find_band_overlaps()
    return {"overlaps_found": len(o), "overlaps": o}


@app.get("/api/v1/region/{region}")
async def region_bands(region: str):
    """Get all bands available in a specific region."""
    return get_bands_for_region(region)


@app.get("/api/v1/stats")
async def stats():
    """Database statistics."""
    all_b = get_all_bands()
    by_gen = {}
    for b in all_b:
        by_gen[b.generation] = by_gen.get(b.generation, 0) + 1
    return {
        "total_bands": len(all_b),
        "by_generation": by_gen,
        "duplex_modes": {"FDD": sum(1 for b in all_b if b.duplex == "FDD"),
                        "TDD": sum(1 for b in all_b if b.duplex == "TDD"),
                        "SDL": sum(1 for b in all_b if b.duplex == "SDL")},
        "frequency_range_mhz": {"min": min(b.downlink_low_mhz for b in all_b),
                                "max": max(b.downlink_high_mhz for b in all_b)},
    }


@app.get("/", response_class=HTMLResponse)
async def explorer():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Spectrum Band Identifier</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.c{max-width:1100px;margin:0 auto;padding:2rem}
h1{font-size:2rem;color:#22d3ee;margin-bottom:.5rem}
.sub{color:#94a3b8;margin-bottom:2rem}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-bottom:1.5rem}
.card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1rem;text-align:center;cursor:pointer;transition:border .2s}
.card:hover{border-color:#22d3ee}.card.active{border-color:#22d3ee;background:#164e63}
.card .val{font-size:1.5rem;font-weight:700}.card .lbl{font-size:.75rem;color:#94a3b8}
.c2g .val{color:#94a3b8}.c3g .val{color:#fbbf24}.c4g .val{color:#22d3ee}.c5g .val{color:#a78bfa}
.section{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1.5rem;margin-bottom:1rem}
h2{color:#22d3ee;margin-bottom:.75rem;font-size:1rem}
input{padding:.5rem;border:1px solid #334155;border-radius:6px;background:#0f172a;color:#e2e8f0;width:200px;margin-right:.5rem}
button{padding:.5rem 1rem;border:none;border-radius:8px;background:#0891b2;color:white;font-size:.85rem;cursor:pointer;font-weight:600;margin:.25rem}
button:hover{background:#0e7490}
#output{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:1rem;
        min-height:200px;white-space:pre-wrap;font-family:monospace;font-size:.8rem;margin-top:1rem;overflow-x:auto;max-height:600px;overflow-y:auto}
table{width:100%;border-collapse:collapse;font-size:.8rem}
th{background:#334155;padding:.5rem;text-align:left;color:#22d3ee;position:sticky;top:0}
td{padding:.4rem .5rem;border-bottom:1px solid #1e293b}
tr:hover td{background:#1e293b}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:.7rem;margin:1px}
.tag-2g{background:#374151;color:#9ca3af}.tag-3g{background:#78350f;color:#fbbf24}
.tag-4g{background:#164e63;color:#22d3ee}.tag-5g{background:#3b0764;color:#a78bfa}
.tag-fdd{background:#1e3a5f;color:#60a5fa}.tag-tdd{background:#3f1f0a;color:#f97316}
</style></head>
<body><div class="c">
<h1>2G/3G/4G/5G Spectrum Band Identifier</h1>
<p class="sub">Complete cellular frequency band database - identify, compare, and explore</p>

<div class="grid" id="genCards">
<div class="card c2g" onclick="loadGen('2G')"><div class="val" id="n2g">-</div><div class="lbl">2G (GSM)</div></div>
<div class="card c3g" onclick="loadGen('3G')"><div class="val" id="n3g">-</div><div class="lbl">3G (UMTS)</div></div>
<div class="card c4g" onclick="loadGen('4G')"><div class="val" id="n4g">-</div><div class="lbl">4G (LTE)</div></div>
<div class="card c5g" onclick="loadGen('5G')"><div class="val" id="n5g">-</div><div class="lbl">5G (NR)</div></div>
</div>

<div class="section">
<h2>Identify Frequency</h2>
<input type="number" id="freqInput" placeholder="Enter MHz (e.g. 3500)" step="0.1">
<button onclick="identifyFreq()">Identify Band</button>
<button onclick="identifyFreq(617)">617 MHz</button>
<button onclick="identifyFreq(900)">900 MHz</button>
<button onclick="identifyFreq(1800)">1800 MHz</button>
<button onclick="identifyFreq(2100)">2100 MHz</button>
<button onclick="identifyFreq(2600)">2600 MHz</button>
<button onclick="identifyFreq(3500)">3500 MHz</button>
<button onclick="identifyFreq(28000)">28 GHz</button>
</div>

<div class="section">
<h2>Explore</h2>
<button onclick="loadCompare()">Compare Generations</button>
<button onclick="loadOverlaps()">Find Overlaps</button>
<button onclick="loadRegion('Middle East')">Middle East Bands</button>
<button onclick="loadRegion('Europe')">Europe</button>
<button onclick="loadRegion('Americas')">Americas</button>
<button onclick="loadRegion('Asia')">Asia</button>
<input type="text" id="searchInput" placeholder="Search (e.g. mmWave)" style="width:150px">
<button onclick="searchBands()">Search</button>
</div>

<div id="output">Click a generation card or enter a frequency to explore the spectrum database.</div>
</div>

<script>
async function loadStats(){
  const r=await fetch('/api/v1/stats');const d=await r.json();
  document.getElementById('n2g').textContent=d.by_generation['2G']||0;
  document.getElementById('n3g').textContent=d.by_generation['3G']||0;
  document.getElementById('n4g').textContent=d.by_generation['4G']||0;
  document.getElementById('n5g').textContent=d.by_generation['5G']||0;
}

function tag(gen){return '<span class="tag tag-'+gen.toLowerCase()+'">'+gen+'</span>'}
function dtag(d){return '<span class="tag tag-'+d.toLowerCase()+'">'+d+'</span>'}

async function loadGen(gen){
  const r=await fetch('/api/v1/bands/'+gen);const d=await r.json();
  let html='<h3>'+gen+' Bands ('+d.total_bands+' bands)</h3><br>';
  html+='<table><tr><th>Band</th><th>Name</th><th>Duplex</th><th>UL (MHz)</th><th>UL Mid</th><th>DL (MHz)</th><th>DL Mid</th><th>BW</th><th>Regions</th></tr>';
  (d.bands||[]).forEach(b=>{
    const ul=b.uplink_mhz, dl=b.downlink_mhz;
    html+='<tr><td><b>'+b.band_number+'</b></td><td>'+b.name+'</td><td>'+dtag(b.duplex)+'</td>';
    html+='<td>'+ul.low+' - '+ul.high+'</td><td><b>'+ul.mid+'</b></td>';
    html+='<td>'+dl.low+' - '+dl.high+'</td><td><b>'+dl.mid+'</b></td>';
    html+='<td>'+dl.bandwidth+'</td>';
    html+='<td>'+b.regions.join(', ')+'</td></tr>';
  });
  html+='</table>';
  document.getElementById('output').innerHTML=html;
}

async function identifyFreq(f){
  const freq=f||document.getElementById('freqInput').value;
  if(!freq)return;
  document.getElementById('freqInput').value=freq;
  const r=await fetch('/api/v1/identify?freq='+freq);const d=await r.json();
  let html='<h3>Frequency: '+d.frequency_mhz+' MHz - '+d.matches_found+' band(s) found</h3><br>';
  if(!d.bands.length){html+='<p>No matching bands found for this frequency.</p>';document.getElementById('output').innerHTML=html;return;}
  html+='<table><tr><th>Gen</th><th>Band</th><th>Name</th><th>Match</th><th>Duplex</th><th>Range (MHz)</th><th>Mid Freq</th><th>Offset</th><th>Category</th></tr>';
  d.bands.forEach(b=>{
    const info=b.match_type==='downlink'?b.downlink_mhz:b.uplink_mhz;
    html+='<tr><td>'+tag(b.generation)+'</td><td><b>'+b.band_number+'</b></td><td>'+b.name+'</td>';
    html+='<td>'+b.match_type+'</td><td>'+dtag(b.duplex)+'</td>';
    html+='<td>'+info.low+' - '+info.high+'</td><td><b>'+info.mid+'</b></td>';
    html+='<td>'+b.offset_from_center_mhz+' MHz</td><td>'+b.frequency_category+'</td></tr>';
  });
  html+='</table>';
  document.getElementById('output').innerHTML=html;
}

async function loadCompare(){
  const r=await fetch('/api/v1/compare');const d=await r.json();
  let html='<h3>Generation Comparison</h3><br><table><tr><th>Generation</th><th>Bands</th><th>Total DL Spectrum</th><th>Freq Range</th><th>Duplex</th><th>Max Ch BW</th></tr>';
  ['2G','3G','4G','5G'].forEach(g=>{
    const s=d[g];
    html+='<tr><td>'+tag(g)+'</td><td>'+s.band_count+'</td><td><b>'+s.total_downlink_spectrum_mhz+' MHz</b></td>';
    html+='<td>'+s.lowest_freq_mhz+' - '+s.highest_freq_mhz+' MHz</td>';
    html+='<td>'+s.duplex_modes.map(dtag).join(' ')+'</td><td>'+s.max_channel_bw_mhz+' MHz</td></tr>';
  });
  html+='</table>';
  document.getElementById('output').innerHTML=html;
}

async function loadOverlaps(){
  const r=await fetch('/api/v1/overlaps');const d=await r.json();
  let html='<h3>Cross-Generation Frequency Overlaps ('+d.overlaps_found+')</h3><br>';
  html+='<table><tr><th>Band 1</th><th>Band 2</th><th>Overlap Type</th><th>Overlap</th><th>Range</th></tr>';
  d.overlaps.forEach(o=>{
    html+='<tr><td>'+o.band_1+'</td><td>'+o.band_2+'</td><td>'+o.overlap_type+'</td>';
    html+='<td><b>'+o.overlap_mhz+' MHz</b></td><td>'+o.range_mhz+'</td></tr>';
  });
  html+='</table>';
  document.getElementById('output').innerHTML=html;
}

async function loadRegion(region){
  const r=await fetch('/api/v1/region/'+region);const d=await r.json();
  let html='<h3>'+d.region+' - '+d.total_bands+' bands</h3><br>';
  ['2G','3G','4G','5G'].forEach(g=>{
    const bands=d.by_generation[g];
    if(!bands.length)return;
    html+='<h4>'+tag(g)+' ('+bands.length+' bands)</h4><table><tr><th>Band</th><th>Name</th><th>DL Range</th><th>DL Mid</th><th>Duplex</th><th>Notes</th></tr>';
    bands.forEach(b=>{
      html+='<tr><td><b>'+b.band_number+'</b></td><td>'+b.name+'</td>';
      html+='<td>'+b.downlink_mhz.low+'-'+b.downlink_mhz.high+'</td><td><b>'+b.downlink_mhz.mid+'</b></td>';
      html+='<td>'+dtag(b.duplex)+'</td><td>'+b.notes+'</td></tr>';
    });
    html+='</table><br>';
  });
  document.getElementById('output').innerHTML=html;
}

async function searchBands(){
  const q=document.getElementById('searchInput').value;
  if(!q)return;
  const r=await fetch('/api/v1/search?q='+encodeURIComponent(q));const d=await r.json();
  let html='<h3>Search: "'+d.query+'" - '+d.results_found+' results</h3><br>';
  html+='<table><tr><th>Gen</th><th>Band</th><th>Name</th><th>DL Range</th><th>DL Mid</th><th>Duplex</th><th>Regions</th></tr>';
  d.bands.forEach(b=>{
    html+='<tr><td>'+tag(b.generation)+'</td><td><b>'+b.band_number+'</b></td><td>'+b.name+'</td>';
    html+='<td>'+b.downlink_mhz.low+'-'+b.downlink_mhz.high+'</td><td><b>'+b.downlink_mhz.mid+'</b></td>';
    html+='<td>'+dtag(b.duplex)+'</td><td>'+b.regions.join(', ')+'</td></tr>';
  });
  html+='</table>';
  document.getElementById('output').innerHTML=html;
}

loadStats();
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=False)
