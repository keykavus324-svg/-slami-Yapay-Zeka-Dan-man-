"""
ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı
=========================================
FastAPI uygulaması.

Çalıştırma:
    python -m app.main              (veya)
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Ücretsiz ve sınırsız: harici yapay zeka API'si, API anahtarı, üyelik veya kota YOKTUR.
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import engine
from .llm import KULLANICI_SABLONU, SISTEM_PROMPTU, baglam_metni, model_bilgisi
from .yerel_model import ONERILEN_MODELLER, yerel_model

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı",
    description=(
        "Ücretsiz ve sınırsız İslami soru-cevap uygulaması.\n\n"
        "**İki katman:** (1) 152 kayıtlık yerel bilgi bankası — çevrimdışı, anahtarsız; "
        "(2) isteğe bağlı yüksek parametreli dil modeli (Gemini/Groq/OpenRouter/Ollama) — "
        "çağrı kullanıcının tarayıcısından yapılır, anahtar sunucuya gitmez."
    ),
    version="3.0.0",
)

# Önizleme/tarayıcı erişimi için geniş CORS (herkese açık, kimlik doğrulamasız araç)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SoruIstegi(BaseModel):
    soru: str = Field(..., min_length=1, max_length=1000, description="Kullanıcının sorusu")
    detay: str = Field("normal", description="'normal' veya 'kisa'")


# --------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------

@app.get("/api/saglik")
def saglik() -> Dict[str, Any]:
    """Servis sağlık kontrolü ve uygulama kimliği."""
    return {
        "durum": "calisiyor",
        "uygulama": "ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı",
        "ucret": "Ücretsiz",
        "sinir": "Sınırsız",
        "kayit_gerekli": False,
        "api_anahtari_gerekli": False,
        "harici_yapayzeka": False,
        "llm_destegi": True,
        "yerel_model": yerel_model.durum(),
        "mod": "yerel bilgi bankası (varsayılan) + isteğe bağlı dil modeli (tarayıcıdan)",
        "bilgi_bankasi_kayit": engine.N,
        "zaman": time.time(),
    }


@app.post("/api/sor")
def sor(istek: SoruIstegi) -> Dict[str, Any]:
    """Kullanıcının İslami sorusunu bilgi bankasından cevaplar. Sınırsız kullanım."""
    detay = "kisa" if istek.detay == "kisa" else "normal"
    sonuc = engine.ask(istek.soru, detay=detay)
    sonuc["istek_zamani"] = time.time()
    return sonuc


@app.post("/api/baglam")
def baglam(istek: SoruIstegi) -> Dict[str, Any]:
    """
    Dil modeline (LLM) verilecek **kaynaklı bağlam paketi** + yerel motorun cevabı.

    Tarayıcı bu uç noktadan bilgi bankası bağlamını alır, ardından seçili yüksek
    parametreli modele (Gemini/Groq/OpenRouter/Ollama) soruyu bu bağlamla birlikte sorar.
    """
    sonuc = engine.baglam(istek.soru)
    sonuc["baglam_metni"] = baglam_metni(sonuc["kayitlar"], sonuc["pasajlar"])
    sonuc["kullanici_mesaji"] = KULLANICI_SABLONU.format(
        kayit_sayisi=sonuc["bilgi_bankasi"]["kayit"],
        pasaj_sayisi=sonuc["bilgi_bankasi"]["pasaj"],
        baglam=sonuc["baglam_metni"],
        soru=istek.soru.strip(),
    )
    sonuc["istek_zamani"] = time.time()
    return sonuc


@app.get("/api/model")
def model() -> Dict[str, Any]:
    """Dil modeli ayarları: sistem yönergesi, sağlayıcılar ve ücretsiz model listeleri."""
    return model_bilgisi()


@app.get("/api/yerel-model")
def yerel_model_durumu(zorla: bool = False) -> Dict[str, Any]:
    """Sistem içi (yerel) dil modelinin durumu. Anahtar gerekmez, dış servis kullanılmaz."""
    return yerel_model.kesfet(zorla=zorla)


def _kisa_baglam(veri: Dict[str, Any], kayit_sinir: int = 2, pasaj_sinir: int = 3) -> str:
    """Küçük bağlam pencereli modeller için sıkıştırılmış bağlam metni."""
    parcalar: List[str] = []
    for i, k in enumerate((veri.get("kayitlar") or [])[:kayit_sinir], 1):
        cevap = (k.get("cevap") or "")[:1100]
        kaynak = "; ".join(k.get("kaynaklar") or [])
        parcalar.append("[KAYIT %d] (%s) %s\n%s\nKaynaklar: %s" % (i, k.get("kategori", ""), k.get("soru", ""), cevap, kaynak))
    for i, pz in enumerate((veri.get("pasajlar") or [])[:pasaj_sinir], 1):
        parcalar.append("[BÖLÜM %d] (%s) %s\n%s" % (i, pz.get("kategori", ""), pz.get("soru", ""), (pz.get("metin") or "")[:700]))
    return "\n\n".join(parcalar)


@app.post("/api/sor-yerel")
def sor_yerel(istek: SoruIstegi):
    """
    Cevabı **sistem içindeki** dil modeli üretir ve kelime kelime akıtır (SSE).

    Anahtar yok, dış servis yok: model aynı makinede koşar (Ollama / llama.cpp /
    llama-cpp-python). Model yoksa ya da hata verirse aynı akış içinde yerel bilgi
    bankası cevabı gönderilir — soru asla cevapsız kalmaz.
    """
    def olay(tip: str, **ek: Any) -> str:
        return "data: " + json.dumps({"tip": tip, **ek}, ensure_ascii=False) + "\n\n"

    def akis():
        try:
            veri = engine.baglam(istek.soru)
        except Exception as hata:  # pragma: no cover
            yield olay("hata", mesaj="Bağlam üretilemedi: %s" % hata)
            yield "data: [DONE]\n\n"
            return

        yerel_yanit = veri["yerel"]
        if veri["tip"] in ("guvenlik", "sohbet", "bos"):
            yield olay("yedek", cevap=yerel_yanit, sebep="ozel-yanit")
            yield "data: [DONE]\n\n"
            return

        durum = yerel_model.kesfet()
        if not durum["hazir"]:
            yield olay("yedek", cevap=yerel_yanit, sebep="model-yok", model_durum=durum)
            yield "data: [DONE]\n\n"
            return

        baglam = yerel_model.baglami_kirp(_kisa_baglam(veri))
        kullanici_mesaji = KULLANICI_SABLONU.format(
            kayit_sayisi=veri["bilgi_bankasi"]["kayit"],
            pasaj_sayisi=veri["bilgi_bankasi"]["pasaj"],
            baglam=baglam,
            soru=istek.soru.strip(),
        )
        mesajlar = [
            {"role": "system", "content": SISTEM_PROMPTU},
            {"role": "user", "content": kullanici_mesaji},
        ]

        yield olay(
            "meta",
            motor=durum["arka_uc"],
            model=durum["model"],
            kayitlar=veri["kayitlar"][:3],
            pasajlar=veri["pasajlar"][:3],
            bilgi_bankasi=veri["bilgi_bankasi"],
            baglam_karakter=len(baglam),
        )

        basla = time.time()
        toplam = 0
        try:
            for parca in yerel_model.uret(mesajlar):
                toplam += len(parca)
                yield olay("parca", metin=parca)
            if toplam == 0:
                raise RuntimeError("model boş yanıt döndürdü")
            yield olay("son", sure=round(time.time() - basla, 2), karakter=toplam)
        except Exception as hata:
            yield olay("hata", mesaj="Yerel model hatası: %s" % hata)
            yield olay("yedek", cevap=yerel_yanit, sebep="model-hatasi")
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        akis(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/api/kategoriler")
def kategoriler() -> Dict[str, Any]:
    return {"kategoriler": engine.kategoriler()}


@app.get("/api/sorular")
def sorular(kategori: Optional[str] = Query(None)) -> Dict[str, Any]:
    return {"sorular": engine.sorular(kategori)}


@app.get("/api/soru/{soru_id}")
def soru_detay(soru_id: str, detay: str = "normal") -> Dict[str, Any]:
    entry = engine.by_id(soru_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Soru bulunamadı")
    cevap = engine._shorten(entry.cevap) if detay == "kisa" else entry.cevap
    return {
        "bulundu": True,
        "tip": "cevap",
        "guven": 1.0,
        "kategori": entry.kategori,
        "soru": entry.soru,
        "cevap": cevap,
        "kaynaklar": entry.kaynaklar,
        "ilgili": [
            {"id": e.id, "soru": e.soru, "kategori": e.kategori}
            for e in engine.entries
            if e.kategori == entry.kategori and e.id != entry.id
        ][:4],
        "notlar": [
            "Bu bilgi genel bilgilendirme içindir; kişisel durumunuz için bir müftülüğe danışın. "
            "Ben bir müftü değilim."
        ],
    }


@app.get("/api/rastgele")
def rastgele() -> Dict[str, Any]:
    entry = random.choice(engine.entries)
    return soru_detay(entry.id)


@app.get("/api/bosluklar")
def bosluklar() -> Dict[str, Any]:
    """Cevaplanamayan soruları listeler — içerik geliştirme listesi (en çok sorulanlar önce)."""
    kayitlar = engine.bosluklar()
    return {"adet": len(kayitlar), "bosluklar": kayitlar[:100]}


@app.get("/api/istatistik")
def istatistik() -> Dict[str, Any]:
    return {
        **engine.istatistik(),
        "surum": "3.0.0",
        "yerel_model": yerel_model.durum(),
        "aciklama": "Yerel bilgi bankası her zaman çalışır (ücretsiz, kotasız). İsteğe bağlı olarak "
                    "yüksek parametreli bir dil modeli tarayıcıdan bağlanabilir.",
    }


# --------------------------------------------------------------------------------------
# Arayüz (statik dosyalar)
# --------------------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"mesaj": "ŞEYH TUĞRUL API çalışıyor. Arayüz için /static/index.html hazırlanmalı."})


@app.get("/favicon.ico")
def favicon():
    f = STATIC_DIR / "favicon.svg"
    if f.exists():
        return FileResponse(str(f), media_type="image/svg+xml")
    raise HTTPException(status_code=404)


def run() -> None:  # pragma: no cover
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    run()
