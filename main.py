import anthropic
import feedparser
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import asyncio
import os

app = FastAPI()

FEEDS = [
    {"id": "lavoz", "name": "La Voz del Interior", "region": "Centro", "url": "https://news.google.com/rss/search?q=site:lavoz.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "lagaceta", "name": "La Gaceta", "region": "NOA", "url": "https://news.google.com/rss/search?q=site:lagaceta.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "rionegro", "name": "Río Negro", "region": "Patagonia", "url": "https://news.google.com/rss/search?q=site:rionegro.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "losandes", "name": "Los Andes", "region": "Cuyo", "url": "https://news.google.com/rss/search?q=site:losandes.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "lacapital", "name": "La Capital Rosario", "region": "Litoral", "url": "https://news.google.com/rss/search?q=site:lacapital.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "cadena3", "name": "Cadena 3", "region": "Centro", "url": "https://news.google.com/rss/search?q=site:cadena3.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "rosario3", "name": "Rosario3", "region": "Litoral", "url": "https://news.google.com/rss/search?q=site:rosario3.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "ellitoral", "name": "El Litoral SF", "region": "Litoral", "url": "https://news.google.com/rss/search?q=site:ellitoral.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "unoentrerios", "name": "UNO Entre Ríos", "region": "Litoral", "url": "https://news.google.com/rss/search?q=site:unoentrerios.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "mdzonline", "name": "MDZ Online", "region": "Cuyo", "url": "https://news.google.com/rss/search?q=site:mdzol.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "diariocuyo", "name": "Diario de Cuyo", "region": "Cuyo", "url": "https://news.google.com/rss/search?q=site:diariodecuyo.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "eltribuno", "name": "El Tribuno", "region": "NOA", "url": "https://news.google.com/rss/search?q=site:eltribuno.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "elliberal", "name": "El Liberal", "region": "NOA", "url": "https://news.google.com/rss/search?q=site:elliberal.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "todojujuy", "name": "Todo Jujuy", "region": "NOA", "url": "https://news.google.com/rss/search?q=site:todojujuy.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "elterritorio", "name": "El Territorio", "region": "NEA", "url": "https://news.google.com/rss/search?q=site:elterritorio.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "datachaco", "name": "DataChaco", "region": "NEA", "url": "https://news.google.com/rss/search?q=site:datachaco.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "lmneuquen", "name": "LM Neuquén", "region": "Patagonia", "url": "https://news.google.com/rss/search?q=site:lmneuquen.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "lanueva", "name": "La Nueva Bahía Blanca", "region": "Bonaerense", "url": "https://news.google.com/rss/search?q=site:lanueva.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "eldia", "name": "El Día La Plata", "region": "Bonaerense", "url": "https://news.google.com/rss/search?q=site:eldia.com&hl=es-419&gl=AR&ceid=AR:es"},
    {"id": "n0223", "name": "0223 Mar del Plata", "region": "Bonaerense", "url": "https://news.google.com/rss/search?q=site:0223.com.ar&hl=es-419&gl=AR&ceid=AR:es"},
]

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

async def fetch_feed(feed: dict) -> List[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(feed["url"], headers={"User-Agent": "Mozilla/5.0"})
            parsed = feedparser.parse(resp.text)
            items = []
            for entry in parsed.entries[:6]:
                items.append({
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "source": feed["name"],
                    "region": feed["region"],
                })
            return items
    except Exception:
        return []

class AnalyzeRequest(BaseModel):
    regions: Optional[List[str]] = None
    top: int = 15

class TrendRequest(BaseModel):
    context: Optional[str] = ""

@app.get("/api/feeds")
def get_feeds():
    return FEEDS

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    selected_feeds = FEEDS
    if req.regions:
        selected_feeds = [f for f in FEEDS if f["region"] in req.regions]
    tasks = [fetch_feed(f) for f in selected_feeds]
    results = await asyncio.gather(*tasks)
    all_items = [item for sublist in results for item in sublist]
    if not all_items:
        return {"error": "No se pudieron cargar los feeds", "items": []}
    titles_text = "\n".join([f"[{i}] {it['source']} | {it['title']}" for i, it in enumerate(all_items)])
    prompt = f"""Sos el editor jefe de La Aurora, medio federal argentino enfocado en provincias del interior. Priorizás: abuso de poder provincial, corrupción, conflictos sociales, protestas, casos judiciales, salud, infraestructura, política local real. No te interesan noticias porteñas que replican Clarín/Infobae ni chimento político sin impacto local.\n\nNoticias disponibles:\n{titles_text}\n\nSeleccioná las {req.top} más importantes. Devolvé SOLO JSON válido sin markdown:\n{{\"seleccionadas\": [{{\"idx\": número, \"score\": \"alta\"|\"media\"|\"baja\", \"resumen\": \"una oración del tema\", \"porque\": \"por qué importa en máximo 15 palabras\"}}]}}"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    raw = message.content[0].text.replace("```json", "").replace("```", "").strip()
    parsed_result = json.loads(raw)
    output = []
    for s in parsed_result["seleccionadas"]:
        item = all_items[s["idx"]]
        output.append({**item, "score": s["score"], "resumen": s["resumen"], "porque": s["porque"]})
    return {"items": output, "total_leidas": len(all_items)}

@app.post("/api/tendencias")
async def tendencias(req: TrendRequest):
    from datetime import datetime
    hoy = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""Hoy es {hoy}. Buscá qué temas están en tendencia en Argentina ahora mismo en redes sociales y medios digitales. {f'Contexto: {req.context}.' if req.context else ''}\n\nDevolvé SOLO JSON válido sin markdown:\n{{\"tendencias\": [{{\"titulo\": \"nombre del tema\", \"volumen\": \"nivel de conversación\", \"descripcion\": \"qué pasa en 2-3 oraciones\", \"angulos\": [\"ángulo 1\", \"ángulo 2\", \"ángulo 3\"]}}]}}\n\nIncluí entre 5 y 8 tendencias reales de hoy en Argentina."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    raw = message.content[0].text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
