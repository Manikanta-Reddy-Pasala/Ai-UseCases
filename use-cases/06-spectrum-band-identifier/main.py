"""2G/3G/4G/5G Spectrum Band Identifier — IQ Signal Analysis Edition.

Accepts raw IQ data from any SDR, performs spectral analysis,
detects signals, identifies the technology (2G/3G/4G/5G),
and outputs center frequency + decoding hints.

Supports: RTL-SDR (uint8/int16), HackRF (int8), USRP (float32/complex64),
          NumPy arrays, CSV, WAV files.

API:
    POST /api/v1/analyze           - Analyze uploaded IQ file
    POST /api/v1/analyze/generate  - Generate test signal and analyze
    GET  /api/v1/bands             - Band database
    GET  /api/v1/bands/{gen}       - Bands by generation
    GET  /api/v1/identify?freq=    - Identify band by frequency
    GET  /api/v1/compare           - Compare generations
    GET  /api/v1/stats             - System stats
    GET  /                         - Interactive UI
"""

import json
import logging
import time

import numpy as np
from fastapi import FastAPI, File, UploadFile, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse


def _sanitize(obj):
    """Recursively convert numpy types to Python natives for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj

from signal_processing.iq_reader import read_iq_data, generate_test_signal
from signal_processing.spectral_analyzer import analyze_spectrum
from signal_processing.spectrogram_analyzer import analyze_spectrogram
from detector.technology_classifier import classify_signal
from bands.spectrum_db import (
    get_all_bands, get_bands_by_generation, identify_band_by_frequency, search_bands
)
from analyzer.frequency_analyzer import (
    get_generation_summary, compare_generations, find_band_overlaps, get_bands_for_region
)

logging.basicConfig(level="INFO", format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="2G/3G/4G/5G Spectrum Identifier - IQ Analysis", version="2.0.0")


@app.on_event("startup")
async def startup():
    logger.info("Spectrum Identifier v2.0 started | %d bands | IQ analysis ready | Port 8005",
                len(get_all_bands()))


@app.post("/api/v1/analyze")
async def analyze_iq_file(
    file: UploadFile = File(...),
    sample_rate: float = Form(20e6, description="Sample rate in Hz"),
    center_freq: float = Form(0, description="Center frequency in Hz (tuned freq)"),
    fmt: str = Form("auto", description="IQ format: auto, complex64, int16, int8, uint8, npy, csv, wav"),
    fft_size: int = Form(4096),
    threshold_db: float = Form(6, description="Signal detection threshold above noise floor"),
):
    """Analyze uploaded IQ data: detect signals, identify technology, find center frequency."""
    start = time.time()
    data = await file.read()

    # Read IQ data
    iq = read_iq_data(data, fmt=fmt, sample_rate=sample_rate, center_freq=center_freq)

    # Spectral analysis
    spectrum = analyze_spectrum(iq["samples"], sample_rate, center_freq, fft_size, threshold_db)

    # Classify each detected signal
    classifications = []
    for sig in spectrum.detected_signals:
        result = classify_signal(sig, iq["samples"], sample_rate)
        sig.technology = result.technology
        sig.band_info = {"generation": result.generation, "confidence": result.confidence}
        classifications.append({
            "technology": result.technology,
            "generation": result.generation,
            "confidence": result.confidence,
            "center_freq_mhz": result.center_freq_mhz,
            "center_freq_hz": result.center_freq_hz,
            "bandwidth_khz": result.bandwidth_khz,
            "matched_standard_bw_khz": result.matched_standard_bw_khz,
            "spectral_type": result.spectral_type,
            "snr_db": sig.snr_db,
            "power_db": sig.power_db,
            "decoding_hint": result.decoding_hint,
            "band_matches": result.band_matches[:3],
            "reasoning": result.reasoning,
        })

    # PSD for visualization (downsample for JSON)
    psd_len = len(spectrum.psd_db)
    step = max(1, psd_len // 1000)
    psd_json = {
        "freq_mhz": (spectrum.freq_axis_hz[::step] / 1e6 + center_freq / 1e6).tolist(),
        "power_db": spectrum.psd_db[::step].tolist(),
    }

    duration_ms = int((time.time() - start) * 1000)

    return JSONResponse(_sanitize({
        "filename": file.filename,
        "iq_info": {
            "format": iq["format"],
            "num_samples": iq["num_samples"],
            "sample_rate_hz": sample_rate,
            "center_freq_hz": center_freq,
            "center_freq_mhz": center_freq / 1e6,
            "duration_sec": round(iq["duration_sec"], 4),
        },
        "spectrum": {
            "noise_floor_db": round(spectrum.noise_floor_db, 1),
            "signals_detected": len(classifications),
            "fft_size": fft_size,
        },
        "signals": classifications,
        "psd": psd_json,
        "analysis_duration_ms": duration_ms,
    }))


@app.post("/api/v1/analyze/generate")
async def analyze_generated_signal(
    signal_type: str = Query("lte", description="gsm, umts, lte, 5g_nr, multi, noise"),
    center_freq: float = Query(1842.5e6, description="Center frequency in Hz"),
    sample_rate: float = Query(20e6, description="Sample rate in Hz"),
    duration_sec: float = Query(0.01, description="Duration in seconds"),
    snr_db: float = Query(20, description="SNR in dB"),
    fft_size: int = Query(4096),
):
    """Generate a synthetic test signal and analyze it."""
    start = time.time()

    iq = generate_test_signal(signal_type, center_freq, sample_rate, duration_sec, snr_db)
    spectrum = analyze_spectrum(iq["samples"], sample_rate, center_freq, fft_size)

    classifications = []
    for sig in spectrum.detected_signals:
        result = classify_signal(sig, iq["samples"], sample_rate)
        classifications.append({
            "technology": result.technology,
            "generation": result.generation,
            "confidence": result.confidence,
            "center_freq_mhz": result.center_freq_mhz,
            "bandwidth_khz": result.bandwidth_khz,
            "matched_standard_bw_khz": result.matched_standard_bw_khz,
            "spectral_type": result.spectral_type,
            "snr_db": sig.snr_db,
            "decoding_hint": result.decoding_hint,
            "reasoning": result.reasoning,
        })

    psd_len = len(spectrum.psd_db)
    step = max(1, psd_len // 500)

    return JSONResponse(_sanitize({
        "generated_signal": signal_type,
        "iq_info": {
            "num_samples": iq["num_samples"],
            "sample_rate_hz": sample_rate,
            "center_freq_mhz": center_freq / 1e6,
            "duration_sec": duration_sec,
            "snr_db": snr_db,
        },
        "spectrum": {
            "noise_floor_db": round(spectrum.noise_floor_db, 1),
            "signals_detected": len(classifications),
        },
        "signals": classifications,
        "psd": {
            "freq_mhz": (spectrum.freq_axis_hz[::step] / 1e6 + center_freq / 1e6).tolist(),
            "power_db": spectrum.psd_db[::step].tolist(),
        },
        "analysis_duration_ms": int((time.time() - start) * 1000),
    }))


@app.post("/api/v1/analyze/spectrogram")
async def analyze_spectrogram_data(
    file: UploadFile = File(...),
    center_freq_khz: float = Form(..., description="Center frequency in kHz"),
    bandwidth_khz: float = Form(..., description="Total bandwidth in kHz"),
    num_chunks: int = Form(1, description="Number of frequency chunks"),
    overlap_khz: float = Form(10000),
    threshold_db: float = Form(6),
):
    """Analyze pre-computed spectrogram data (same format as YOLO scanner input).

    Input: float32 array of spectrogram values (dBm power), not raw IQ.
    This is the same data format that the Ultralytics YOLO scanner processes.
    """
    start = time.time()
    data = await file.read()
    raw = np.frombuffer(data, dtype=np.float32)

    result = analyze_spectrogram(
        raw, center_freq_khz, bandwidth_khz,
        num_chunks=num_chunks, overlap_khz=overlap_khz,
        threshold_above_noise_db=threshold_db,
    )

    signals_out = []
    for sig in result["signals"]:
        signals_out.append({
            "technology": sig.technology,
            "generation": sig.band_info.get("generation", ""),
            "center_freq_mhz": round(sig.absolute_center_freq_hz / 1e6, 1),
            "center_freq_khz": round(sig.absolute_center_freq_hz / 1e3, 1),
            "bandwidth_khz": round(sig.bandwidth_hz / 1000, 1),
            "power_db": round(sig.power_db, 1),
            "snr_db": sig.snr_db,
            "spectral_flatness": sig.spectral_flatness,
            "is_gap_detected": sig.is_2g_gap_detection,
        })

    return JSONResponse(_sanitize({
        "signals": signals_out,
        "noise_floor_db": result["noise_floor_db"],
        "n_time_rows": result["n_time_rows"],
        "n_freq_bins": result["n_freq_bins"],
        "analysis_duration_ms": int((time.time() - start) * 1000),
    }))


# --- Band database endpoints (kept from v1) ---

@app.get("/api/v1/bands")
async def list_bands(generation: str = None):
    if generation:
        bands = get_bands_by_generation(generation)
        return {"generation": generation, "count": len(bands), "bands": [b.to_dict() for b in bands]}
    return {"count": len(get_all_bands()), "bands": [b.to_dict() for b in get_all_bands()]}

@app.get("/api/v1/bands/{generation}")
async def bands_by_gen(generation: str):
    return get_generation_summary(generation.upper())

@app.get("/api/v1/identify")
async def identify_freq(freq: float = Query(...)):
    m = identify_band_by_frequency(freq)
    return {"frequency_mhz": freq, "matches": len(m), "bands": m}

@app.get("/api/v1/search")
async def search(q: str = Query(...)):
    r = search_bands(q)
    return {"query": q, "results": len(r), "bands": r}

@app.get("/api/v1/compare")
async def compare():
    return compare_generations()

@app.get("/api/v1/overlaps")
async def overlaps():
    o = find_band_overlaps()
    return {"overlaps": len(o), "data": o}

@app.get("/api/v1/region/{region}")
async def region(region: str):
    return get_bands_for_region(region)

@app.get("/api/v1/stats")
async def stats():
    all_b = get_all_bands()
    by_gen = {}
    for b in all_b:
        by_gen[b.generation] = by_gen.get(b.generation, 0) + 1
    return {"total_bands": len(all_b), "by_generation": by_gen,
            "capabilities": ["iq_analysis", "fft_psd", "signal_detection", "technology_classification",
                           "band_identification", "ofdm_detection", "center_freq_estimation"]}


@app.get("/", response_class=HTMLResponse)
async def ui():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Spectrum Identifier v2</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.c{max-width:1100px;margin:0 auto;padding:1.5rem}
h1{font-size:1.8rem;color:#22d3ee;margin-bottom:.3rem}
.sub{color:#94a3b8;margin-bottom:1.5rem;font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-bottom:1rem}
.card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:.75rem;text-align:center}
.card .val{font-size:1.3rem;font-weight:700;color:#22d3ee}.card .lbl{font-size:.7rem;color:#94a3b8}
.section{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1.2rem;margin-bottom:1rem}
h2{color:#22d3ee;margin-bottom:.75rem;font-size:1rem}
button{padding:.4rem 1rem;border:none;border-radius:6px;background:#0891b2;color:white;font-size:.8rem;cursor:pointer;font-weight:600;margin:.2rem}
button:hover{background:#0e7490}button.gen{background:#7c3aed}button.gen:hover{background:#6d28d9}
select,input[type="number"]{padding:.4rem;border:1px solid #334155;border-radius:6px;background:#0f172a;color:#e2e8f0;margin:.2rem;font-size:.85rem}
#output{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:1rem;min-height:200px;white-space:pre-wrap;font-family:monospace;font-size:.78rem;margin-top:.5rem;overflow:auto;max-height:500px}
canvas{width:100%;height:200px;background:#0f172a;border:1px solid #334155;border-radius:8px;margin-top:.5rem}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:.7rem;margin:1px;font-weight:600}
.tag-2g{background:#374151;color:#9ca3af}.tag-3g{background:#78350f;color:#fbbf24}
.tag-4g{background:#164e63;color:#22d3ee}.tag-5g{background:#3b0764;color:#a78bfa}
</style></head>
<body><div class="c">
<h1>IQ Signal Analyzer &amp; Band Identifier</h1>
<p class="sub">Feed raw IQ data from any SDR → auto-detect 2G/3G/4G/5G → get center frequency for decoding</p>

<div class="grid">
<div class="card"><div class="val" id="nBands">84</div><div class="lbl">Bands in DB</div></div>
<div class="card"><div class="val" id="nSigs">-</div><div class="lbl">Signals Found</div></div>
<div class="card"><div class="val" id="nTech">-</div><div class="lbl">Technology</div></div>
<div class="card"><div class="val" id="nFreq">-</div><div class="lbl">Center MHz</div></div>
</div>

<div class="section">
<h2>1. Generate Test Signal &amp; Analyze</h2>
<select id="sigType">
<option value="lte">LTE (10MHz OFDM)</option>
<option value="gsm">GSM (200kHz GMSK)</option>
<option value="umts">UMTS (5MHz CDMA)</option>
<option value="5g_nr">5G NR (50MHz OFDM)</option>
<option value="multi">Multi (GSM + LTE)</option>
</select>
<label>Center MHz: <input type="number" id="cfreq" value="1842.5" step="0.1" style="width:100px"></label>
<label>SR MHz: <input type="number" id="sr" value="20" step="1" style="width:60px"></label>
<label>SNR dB: <input type="number" id="snr" value="20" step="1" style="width:50px"></label>
<button class="gen" onclick="analyzeGenerated()">Generate &amp; Analyze</button>
</div>

<div class="section">
<h2>2. Upload IQ File</h2>
<p style="font-size:.8rem;color:#94a3b8;margin-bottom:.5rem">Supports: RTL-SDR (uint8), HackRF (int8), USRP (float32), .npy, .csv, .wav</p>
<input type="file" id="iqFile" style="font-size:.8rem">
<label>SR Hz: <input type="number" id="fileSR" value="20000000" style="width:120px"></label>
<label>Center Hz: <input type="number" id="fileFC" value="0" style="width:120px"></label>
<button onclick="analyzeFile()">Upload &amp; Analyze</button>
</div>

<canvas id="psdCanvas"></canvas>
<div id="output">Click "Generate & Analyze" to see IQ signal analysis with technology identification.

Supported signal types:
  • GSM:   200kHz single carrier (GMSK) — identifiable by narrow bandwidth
  • UMTS:  5MHz wideband CDMA — flat spectrum, no OFDM subcarriers
  • LTE:   1.4-20MHz OFDM — 15kHz subcarrier spacing, cyclic prefix correlation
  • 5G NR: up to 100MHz OFDM — 30/60/120kHz SCS, wider bandwidth
</div>

<div class="section">
<h2>3. Band Database</h2>
<label>Freq MHz: <input type="number" id="freqLookup" value="3500" step="0.1" style="width:100px"></label>
<button onclick="lookupFreq()">Identify Band</button>
<button onclick="loadGen('2G')">2G</button><button onclick="loadGen('3G')">3G</button>
<button onclick="loadGen('4G')">4G</button><button onclick="loadGen('5G')">5G</button>
<button onclick="loadCompare()">Compare All</button>
</div>
</div>

<script>
const canvas=document.getElementById('psdCanvas');
const ctx=canvas.getContext('2d');

function drawPSD(psd){
  const w=canvas.width=canvas.offsetWidth;const h=canvas.height=200;
  ctx.fillStyle='#0f172a';ctx.fillRect(0,0,w,h);
  if(!psd||!psd.freq_mhz||!psd.freq_mhz.length)return;
  const freqs=psd.freq_mhz,powers=psd.power_db;
  const minP=Math.min(...powers),maxP=Math.max(...powers);
  const range=maxP-minP||1;
  ctx.strokeStyle='#22d3ee';ctx.lineWidth=1;ctx.beginPath();
  for(let i=0;i<freqs.length;i++){
    const x=i/freqs.length*w;
    const y=h-(powers[i]-minP)/range*h*0.85-h*0.05;
    i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }
  ctx.stroke();
  // Axis labels
  ctx.fillStyle='#94a3b8';ctx.font='10px monospace';
  ctx.fillText(freqs[0].toFixed(1)+' MHz',5,h-5);
  ctx.fillText(freqs[freqs.length-1].toFixed(1)+' MHz',w-80,h-5);
  ctx.fillText(maxP.toFixed(0)+' dB',5,15);
}

async function analyzeGenerated(){
  const type=document.getElementById('sigType').value;
  const cf=document.getElementById('cfreq').value*1e6;
  const sr=document.getElementById('sr').value*1e6;
  const snr=document.getElementById('snr').value;
  document.getElementById('output').textContent='Generating '+type+' signal and analyzing...';
  try{
    const r=await fetch('/api/v1/analyze/generate?signal_type='+type+'&center_freq='+cf+'&sample_rate='+sr+'&snr_db='+snr+'&duration_sec=0.01',{method:'POST'});
    const d=await r.json();
    drawPSD(d.psd);
    let out='IQ Analysis: '+type.toUpperCase()+' signal @ '+d.iq_info.center_freq_mhz+' MHz\\n';
    out+='Samples: '+d.iq_info.num_samples+' | SR: '+(d.iq_info.sample_rate_hz/1e6)+'MHz | Duration: '+d.iq_info.duration_sec+'s\\n';
    out+='Noise floor: '+d.spectrum.noise_floor_db+' dB | Signals detected: '+d.spectrum.signals_detected+'\\n';
    out+='Analysis time: '+d.analysis_duration_ms+'ms\\n';
    out+='\\n'+'='.repeat(60)+'\\n';
    if(d.signals.length===0){out+='\\nNo signals detected above noise floor.\\n';}
    d.signals.forEach((s,i)=>{
      out+='\\nSIGNAL '+(i+1)+': '+s.technology+' ('+s.generation+')\\n';
      out+='  Confidence: '+(s.confidence*100).toFixed(1)+'%\\n';
      out+='  Center Frequency: '+s.center_freq_mhz+' MHz ('+s.center_freq_hz+' Hz)\\n';
      out+='  Bandwidth: '+s.bandwidth_khz+' kHz';
      if(s.matched_standard_bw_khz)out+=' (standard: '+s.matched_standard_bw_khz+' kHz)';
      out+='\\n  Spectral type: '+s.spectral_type+'\\n';
      out+='  SNR: '+s.snr_db+' dB\\n';
      out+='  DECODING: '+s.decoding_hint+'\\n';
      out+='  Reasoning:\\n';
      s.reasoning.forEach(r=>out+='    • '+r+'\\n');
    });
    document.getElementById('output').textContent=out;
    if(d.signals.length>0){
      document.getElementById('nSigs').textContent=d.signals.length;
      document.getElementById('nTech').textContent=d.signals[0].technology;
      document.getElementById('nFreq').textContent=d.signals[0].center_freq_mhz;
    }
  }catch(e){document.getElementById('output').textContent='Error: '+e.message;}
}

async function analyzeFile(){
  const f=document.getElementById('iqFile').files[0];if(!f)return;
  const fd=new FormData();fd.append('file',f);
  fd.append('sample_rate',document.getElementById('fileSR').value);
  fd.append('center_freq',document.getElementById('fileFC').value);
  fd.append('fmt','auto');fd.append('fft_size','4096');fd.append('threshold_db','6');
  document.getElementById('output').textContent='Analyzing '+f.name+'...';
  try{const r=await fetch('/api/v1/analyze',{method:'POST',body:fd});
  const d=await r.json();drawPSD(d.psd);
  let out='File: '+d.filename+' | Format: '+d.iq_info.format+'\\n';
  out+='Samples: '+d.iq_info.num_samples+' | Signals: '+d.spectrum.signals_detected+'\\n\\n';
  d.signals.forEach((s,i)=>{
    out+='SIGNAL '+(i+1)+': '+s.technology+' ('+s.generation+') conf='+(s.confidence*100).toFixed(0)+'%\\n';
    out+='  Center: '+s.center_freq_mhz+' MHz | BW: '+s.bandwidth_khz+' kHz | SNR: '+s.snr_db+' dB\\n';
    out+='  DECODE: '+s.decoding_hint+'\\n\\n';
  });
  document.getElementById('output').textContent=out;}catch(e){document.getElementById('output').textContent='Error: '+e.message;}
}

async function lookupFreq(){
  const f=document.getElementById('freqLookup').value;
  const r=await fetch('/api/v1/identify?freq='+f);const d=await r.json();
  let out='Frequency '+d.frequency_mhz+' MHz → '+d.matches+' band(s):\\n\\n';
  d.bands.forEach(b=>{out+=b.generation+' '+b.name+' (Band '+b.band_number+') ['+b.match_type+'] mid='+b.downlink_mhz.mid+' MHz\\n';});
  document.getElementById('output').textContent=out;
}
async function loadGen(g){
  const r=await fetch('/api/v1/bands/'+g);const d=await r.json();
  let out=g+': '+d.total_bands+' bands\\n\\n';
  (d.bands||[]).forEach(b=>{out+='Band '+b.band_number+' '+b.name+': DL '+b.downlink_mhz.low+'-'+b.downlink_mhz.high+' MHz (mid='+b.downlink_mhz.mid+') '+b.duplex+'\\n';});
  document.getElementById('output').textContent=out;
}
async function loadCompare(){
  const r=await fetch('/api/v1/compare');const d=await r.json();
  let out='Generation Comparison:\\n\\n';
  ['2G','3G','4G','5G'].forEach(g=>{const s=d[g];out+=g+': '+s.band_count+' bands | '+s.total_downlink_spectrum_mhz+' MHz total | '+s.lowest_freq_mhz+'-'+s.highest_freq_mhz+' MHz | max BW='+s.max_channel_bw_mhz+'MHz\\n';});
  document.getElementById('output').textContent=out;
}
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=False)
