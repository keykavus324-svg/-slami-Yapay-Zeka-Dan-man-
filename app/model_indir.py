"""
ŞEYH TUĞRUL — yerel model indirici
==================================
Uygulamanın **kendi makinesine** bir GGUF dil modeli indirir; böylece sistem
hiçbir API anahtarı ve hiçbir dış servis olmadan, kendi modeliyle cevap verir.

Kullanım:
    python -m app.model_indir --liste                 # hazır model listesi
    python -m app.model_indir qwen2.5:7b              # önerilen modeli indir
    python -m app.model_indir qwen2.5:3b --dizin models
    python -m app.model_indir --url https://.../model.gguf

İndirilen dosyalar `models/` klasörüne yazılır ve uygulama açılışta otomatik bulur.
Yarıda kalan indirmeler kaldığı yerden devam eder.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.yerel_model import MODEL_DIZIN, ONERILEN_MODELLER  # noqa: E402

HF_KOK = "https://huggingface.co"


def liste_yazdir() -> None:
    print("İndirilebilir modeller (hepsi ücretsiz, anahtarsız):\n")
    print(f"  {'kısa ad':<14} {'boyut':<10} {'RAM':<8} açıklama")
    print("  " + "-" * 78)
    for m in ONERILEN_MODELLER:
        print(f"  {m['kisa']:<14} {m['boyut']:<10} {m['ram']:<8} {m['ad']}")
        print(f"  {'':<14} {m['not']}")
    print("\nÖrnek:  python -m app.model_indir qwen2.5:7b")
    print("Alternatif (en kolay):  ollama pull qwen2.5:7b  &&  ollama serve")


def model_bul(kisa: str) -> Optional[dict]:
    kisa = kisa.strip().lower()
    for m in ONERILEN_MODELLER:
        if m["kisa"].lower() == kisa:
            return m
    # "qwen2.5:7b" → "qwen2.5:7b-instruct" gibi esnek eşleşme
    for m in ONERILEN_MODELLER:
        if kisa and (kisa in m["kisa"].lower() or m["kisa"].lower() in kisa):
            return m
    return None


def indir(url: str, hedef: Path, yeniden_dene: int = 5) -> Path:
    hedef.parent.mkdir(parents=True, exist_ok=True)
    kalan = hedef.stat().st_size if hedef.exists() else 0
    deneme = 0
    while deneme < yeniden_dene:
        deneme += 1
        try:
            basliklar = {"User-Agent": "sehy-tugrul/3.0"}
            if kalan:
                basliklar["Range"] = f"bytes={kalan}-"
            istek = urllib.request.Request(url, headers=basliklar)
            with urllib.request.urlopen(istek, timeout=60) as yanit:
                toplam = kalan + int(yanit.headers.get("Content-Length") or 0)
                mod = "ab" if kalan and yanit.status == 206 else "wb"
                if mod == "wb":
                    kalan = 0
                yazilan = kalan
                basla = time.time()
                with open(hedef, mod) as f:
                    while True:
                        parca = yanit.read(1024 * 512)
                        if not parca:
                            break
                        f.write(parca)
                        yazilan += len(parca)
                        if toplam:
                            oran = yazilan / toplam * 100
                            hiz = yazilan / max(time.time() - basla, 0.1) / 1e6
                            print(f"\r  indiriliyor: %{oran:5.1f}  ({yazilan/1e6:.0f}/{toplam/1e6:.0f} MB, {hiz:.1f} MB/sn)",
                                  end="", flush=True)
                print()
            return hedef
        except (urllib.error.URLError, TimeoutError, ConnectionError) as hata:
            print(f"\n  ⚠️  indirme kesildi ({hata}); {deneme}/{yeniden_dene} — kaldığı yerden devam ediliyor…")
            kalan = hedef.stat().st_size if hedef.exists() else 0
            time.sleep(2 * deneme)
    raise SystemExit("İndirme tamamlanamadı. İnternet bağlantısını kontrol edip tekrar deneyin.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Şeyh Tuğrul — yerel GGUF model indirici")
    ap.add_argument("model", nargs="?", help="kısa ad (örn. qwen2.5:7b)")
    ap.add_argument("--liste", action="store_true", help="modelleri listele")
    ap.add_argument("--dizin", default=str(MODEL_DIZIN), help="hedef klasör (varsayılan: models/)")
    ap.add_argument("--url", help="doğrudan GGUF bağlantısı")
    ap.add_argument("--dosya", help="kaydedilecek dosya adı")
    a = ap.parse_args()

    if a.liste or not (a.model or a.url):
        liste_yazdir()
        return

    dizin = Path(a.dizin)
    if a.url:
        ad = a.dosya or os.path.basename(a.url.split("?")[0]) or "model.gguf"
        hedef = dizin / ad
        print(f"→ {a.url}\n→ {hedef}")
        indir(a.url, hedef)
    else:
        m = model_bul(a.model)
        if not m:
            print(f"❌ '{a.model}' listede yok. `--liste` ile seçenekleri görebilirsiniz.")
            raise SystemExit(1)
        url = f"{HF_KOK}/{m['repo']}/resolve/main/{m['dosya']}?download=true"
        hedef = dizin / m["dosya"]
        print(f"→ {m['ad']}  ({m['boyut']}, ~{m['ram']} RAM)")
        print(f"→ {hedef}")
        indir(url, hedef)

    boyut = hedef.stat().st_size / 1e6
    print(f"\n✔ Hazır: {hedef}  ({boyut:.0f} MB)")
    print("  Şimdi uygulamayı başlatın:  python -m app.main")
    print("  Uygulama modeli otomatik bulur (Dil Modeli panelinde 'Sistem içi model').")


if __name__ == "__main__":  # pragma: no cover
    main()
