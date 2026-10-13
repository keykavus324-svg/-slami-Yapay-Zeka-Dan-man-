"""
ŞEYH TUĞRUL — tarayıcı modeli kütüphanesini yerele alma (vendor)
================================================================
Tarayıcıda çalışan model için gereken JavaScript/WASM dosyalarını npm deposundan
indirip `app/static/vendor/transformers/` klasörüne koyar. Böylece:

  • tarayıcı, kütüphaneyi CDN'den değil kendi sunucumuzdan yükler (daha hızlı, daha güvenli),
  • onnxruntime'ın WebGPU/WASM çekirdekleri de yerelden servis edilir,
  • CDN erişimi olmayan ortamlarda da çalışır.

Kullanım:
    python -m scripts.vendor_indir            # indir + kur
    python -m scripts.vendor_indir --kontrol  # sadece durumu göster

Not: Model AĞIRLIKLARI (Qwen) burada indirilmez; onları tarayıcı ilk kullanımda
Hugging Face'ten indirir ve önbelleğe alır (~450 MB).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

KOK = Path(__file__).resolve().parents[1]
HEDEF = KOK / "app" / "static" / "vendor" / "transformers"
REGISTRY = "https://registry.npmjs.org"

# transformers.js v4.3.1'in bağımlılık olarak sabitlediği sürümler
TRANSFORMERS_SURUM = "4.3.1"
ORT_SURUM = "1.31.0-dev.20260914-8d85527a0"
ORT_COMMON_SURUM = "1.31.0-dev.20260911-2a43ec07e"

# Kopyalanacak dosyalar: (paket içi yol, hedef ad)
DOSYALAR: Dict[str, List[str]] = {
    f"@huggingface/transformers@{TRANSFORMERS_SURUM}": [
        "package/dist/transformers.web.min.js",
    ],
    f"onnxruntime-web@{ORT_SURUM}": [
        "package/dist/ort.webgpu.min.mjs",
        "package/dist/ort-wasm-simd-threaded.jsep.mjs",
        "package/dist/ort-wasm-simd-threaded.jsep.wasm",
        "package/dist/ort-wasm-simd-threaded.mjs",
        "package/dist/ort-wasm-simd-threaded.wasm",
    ],
    f"onnxruntime-common@{ORT_COMMON_SURUM}": [],  # dist/esm/* tamamı kopyalanır
}


def tarball_url(paket: str) -> str:
    ad, surum = paket.rsplit("@", 1)
    with urllib.request.urlopen(f"{REGISTRY}/{ad.replace('/', '%2f')}", timeout=60) as y:
        veri = json.loads(y.read().decode("utf-8"))
    return veri["versions"][surum]["dist"]["tarball"]


def indir_tar(paket: str) -> tarfile.TarFile:
    url = tarball_url(paket)
    print(f"  ↓ {paket}")
    with urllib.request.urlopen(url, timeout=300) as y:
        veri = y.read()
    return tarfile.open(fileobj=io.BytesIO(veri), mode="r:gz")


def kopyala(tar: tarfile.TarFile, ic_yol: str, hedef: Path, yeni_ad: Optional[str] = None) -> bool:
    try:
        uye = tar.getmember(ic_yol)
    except KeyError:
        print(f"    ⚠️  bulunamadı: {ic_yol}")
        return False
    hedef.mkdir(parents=True, exist_ok=True)
    dosya = hedef / (yeni_ad or Path(ic_yol).name)
    kaynak = tar.extractfile(uye)
    if kaynak is None:
        return False
    with open(dosya, "wb") as f:
        shutil.copyfileobj(kaynak, f)
    print(f"    ✓ {dosya.name}  ({dosya.stat().st_size/1e6:.1f} MB)")
    return True


def yamala(dosya: Path) -> None:
    """Çıplak modül adlarını yerel dosyalara, CDN wasm adresini yerel klasöre çevirir."""
    s = dosya.read_text(encoding="utf-8")
    onceki = s
    s = s.replace('from"onnxruntime-web/webgpu"', 'from"./ort.webgpu.min.mjs"')
    s = s.replace("from'onnxruntime-web/webgpu'", "from'./ort.webgpu.min.mjs'")
    s = s.replace('from"onnxruntime-common"', 'from"./onnxruntime-common/index.js"')
    s = s.replace("from'onnxruntime-common'", "from'./onnxruntime-common/index.js'")
    # onnxruntime wasm çekirdeği: CDN yerine kendi sunucumuz
    s = re.sub(r"https://cdn\.jsdelivr\.net/npm/onnxruntime-web@\$\{[^}]*\}/dist/",
               "/static/vendor/transformers/", s)
    if s != onceki:
        dosya.write_text(s, encoding="utf-8")
        print("    ✓ modül adları ve wasm yolu yamalandı")


def kur(zorla: bool = False) -> int:
    HEDEF.mkdir(parents=True, exist_ok=True)
    print("Kütüphane dosyaları indiriliyor (npm):")

    tar = indir_tar(f"@huggingface/transformers@{TRANSFORMERS_SURUM}")
    kopyala(tar, "package/dist/transformers.web.min.js", HEDEF)
    yamala(HEDEF / "transformers.web.min.js")

    tar = indir_tar(f"onnxruntime-web@{ORT_SURUM}")
    for yol in DOSYALAR[f"onnxruntime-web@{ORT_SURUM}"]:
        kopyala(tar, yol, HEDEF)

    tar = indir_tar(f"onnxruntime-common@{ORT_COMMON_SURUM}")
    ort_hedef = HEDEF / "onnxruntime-common"
    ort_hedef.mkdir(parents=True, exist_ok=True)
    adet = 0
    for uye in tar.getmembers():
        if uye.name.startswith("package/dist/esm/") and uye.isfile():
            goreli = Path(uye.name).relative_to("package/dist/esm")
            hedef_dosya = ort_hedef / goreli
            hedef_dosya.parent.mkdir(parents=True, exist_ok=True)
            kaynak = tar.extractfile(uye)
            if kaynak:
                with open(hedef_dosya, "wb") as f:
                    shutil.copyfileobj(kaynak, f)
                adet += 1
    print(f"    ✓ onnxruntime-common: {adet} dosya")

    (HEDEF / "surum.json").write_text(json.dumps({
        "transformers": TRANSFORMERS_SURUM,
        "onnxruntime_web": ORT_SURUM,
        "onnxruntime_common": ORT_COMMON_SURUM,
        "kaynak": "registry.npmjs.org",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    toplam = sum(f.stat().st_size for f in HEDEF.rglob("*") if f.is_file())
    print(f"\n✔ Kuruldu: {HEDEF}  ({toplam/1e6:.1f} MB)")
    print("  Uygulamayı yeniden başlatın; tarayıcı motoru artık yerelden yüklenir.")
    return 0


def kontrol() -> int:
    gerekli = ["transformers.web.min.js", "ort.webgpu.min.mjs",
               "ort-wasm-simd-threaded.jsep.wasm", "onnxruntime-common/index.js"]
    eksik = [g for g in gerekli if not (HEDEF / g).exists()]
    if eksik:
        print("✘ Kütüphane kurulu değil ya da eksik:")
        for e in eksik:
            print("   -", e)
        print("\nKurmak için:  python -m scripts.vendor_indir")
        return 1
    toplam = sum(f.stat().st_size for f in HEDEF.rglob("*") if f.is_file())
    print(f"✔ Kurulu: {HEDEF}  ({toplam/1e6:.1f} MB)")
    surum = HEDEF / "surum.json"
    if surum.exists():
        print("  " + surum.read_text(encoding="utf-8").replace("\n", " "))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Tarayıcı modeli kütüphanesini yerele al")
    ap.add_argument("--kontrol", action="store_true", help="sadece durum")
    a = ap.parse_args()
    sys.exit(kontrol() if a.kontrol else kur())
