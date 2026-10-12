import asyncio

import edge_tts
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

app = FastAPI(title="Edge TTS Studio (Vercel)")

VOICES = {
    "Asad — Urdu (Pakistan, Male)": "ur-PK-AsadNeural",
    "Uzma — Urdu (Pakistan, Female)": "ur-PK-UzmaNeural",
    "Gul — Urdu (India, Female)": "ur-IN-GulNeural",
    "Salman — Urdu (India, Male)": "ur-IN-SalmanNeural",
    "Swara — Hindi (India, Female)": "hi-IN-SwaraNeural",
    "Madhur — Hindi (India, Male)": "hi-IN-MadhurNeural",
    "Aria — English (US, Female)": "en-US-AriaNeural",
    "Guy — English (US, Male)": "en-US-GuyNeural",
    "Ryan — English (UK, Male)": "en-GB-RyanNeural",
}

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Edge TTS Studio</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;background:#0e1117;color:#fafafa}
textarea{width:100%;height:200px;background:#262730;color:#fafafa;border:1px solid #444;border-radius:8px;padding:10px}
select,button{padding:10px;border-radius:8px;margin:8px 8px 8px 0}
button{background:#ff4b4b;color:#fff;border:0;font-weight:600;cursor:pointer}
audio{width:100%;margin-top:12px}
.small{color:#aaa;font-size:13px}
</style></head><body>
<h2>🔊 Edge TTS Studio</h2>
<p class="small">Free text-to-speech — Urdu, Hindi & English voices (Microsoft Edge TTS)</p>
<textarea id="t" placeholder="Type or paste text here… (Urdu, Hindi ya English)"></textarea>
<div id="c" class="small">0 characters</div>
<select id="v"></select>
<select id="vol"><option value="+0%">Normal</option><option value="+50%" selected>Loud (+50%)</option><option value="+100%">Extra loud (+100%)</option></select>
<br><button id="g">🎙️ Generate Audio</button>
<div id="s" class="small"></div>
<audio id="a" controls style="display:none"></audio>
<br><a id="d" style="display:none;color:#ffd166" download="speech.mp3">⬇️ Download MP3</a>
<script>
const voices = __VOICES__;
const vs = document.getElementById('v');
for (const name of Object.keys(voices)) { const o=document.createElement('option'); o.value=voices[name]; o.textContent=name; vs.appendChild(o); }
const t=document.getElementById('t'), c=document.getElementById('c');
t.addEventListener('input',()=>c.textContent=t.value.length+' characters');
document.getElementById('g').onclick = async () => {
  const s=document.getElementById('s'); s.textContent='Generating… (lamba text zyada time lega)';
  try {
    const r = await fetch('/generate', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text:t.value, voice:vs.value, volume:document.getElementById('vol').value})});
    if (!r.ok) { s.textContent='Error: '+await r.text(); return; }
    const blob = await r.blob(); const url = URL.createObjectURL(blob);
    const a=document.getElementById('a'); a.src=url; a.style.display='block';
    const d=document.getElementById('d'); d.href=url; d.style.display='inline';
    s.textContent='Done!';
  } catch(e) { s.textContent='Error: '+e; }
};
</script></body></html>"""


class GenRequest(BaseModel):
    text: str
    voice: str
    volume: str = "+50%"


@app.get("/", response_class=HTMLResponse)
async def home():
    import json

    return PAGE.replace("__VOICES__", json.dumps(VOICES))


@app.post("/generate")
async def generate(req: GenRequest):
    if req.voice not in VOICES.values():
        return Response(content="Unknown voice", status_code=400)
    text = req.text.strip()
    if not text:
        return Response(content="Empty text", status_code=400)

    async def run() -> bytes:
        communicate = edge_tts.Communicate(text, req.voice, volume=req.volume)
        parts = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                parts.append(chunk["data"])
        return b"".join(parts)

    try:
        audio = await asyncio.wait_for(run(), timeout=55)
    except Exception as exc:  # noqa: BLE001
        return Response(content=f"Generation failed: {exc}", status_code=502)
    if not audio:
        return Response(content="Generation failed: no audio", status_code=502)
    return Response(content=audio, media_type="audio/mpeg")
