"""
ŞEYH TUĞRUL — Sistem içi (yerel) dil modeli katmanı
===================================================
Amaç: **hiçbir API anahtarı ve hiçbir dış servis olmadan**, cevapları uygulamanın
kendi makinesinde koşan bir dil modelinin üretmesi.

Desteklenen yerel çalıştırma yolları (hepsi anahtarsız, hepsi çevrimdışı):

  1. **Ollama**            → `ollama pull qwen2.5:7b`  (en kolay kurulum)
  2. **llama.cpp sunucusu** → `llama-server -m qwen2.5-7b-instruct-q4_k_m.gguf`
  3. **llama-cpp-python**  → süreç içinde (in-process) GGUF çıkarımı
  4. **Herhangi bir OpenAI uyumlu yerel sunucu** (LM Studio, vLLM, text-generation-webui…)

Uygulama açılışta bu arka uçları otomatik arar. Bulunan ilk arka uç "motordur";
hiçbiri yoksa cevaplar yerel bilgi bankasından (RAG) gelir — uygulama asla cevapsız kalmaz.

Ortam değişkenleri:
    TUGRUL_YEREL_URL        → örn. http://127.0.0.1:11434/v1  (zorla seçim)
    TUGRUL_YEREL_MODEL      → örn. qwen2.5:7b
    TUGRUL_YEREL_BAGLAM     → bağlam karakter bütçesi (varsayılan 5000)
    TUGRUL_YEREL_MAKS_TOKEN → cevap başına üst sınır (varsayılan 700)
    TUGRUL_YEREL_SICAKLIK   → sıcaklık (varsayılan 0.6)
    TUGRUL_YEREL_SAHTE      → 1 ise ağ olmadan sahte (deterministik) model: testler için
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIZIN = Path(os.environ.get("TUGRUL_MODEL_DIZIN", BASE_DIR.parent / "models"))

# Otomatik aranacak yerel arka uçlar (sırayla)
ADAY_ARKA_UCLAR: List[Tuple[str, str, str]] = [
    ("Ollama", "http://127.0.0.1:11434/v1", "qwen2.5:7b"),
    ("llama.cpp sunucusu", "http://127.0.0.1:8080/v1", "yerel-gguf"),
    ("llama.cpp sunucusu", "http://127.0.0.1:8081/v1", "yerel-gguf"),
    ("LM Studio", "http://127.0.0.1:1234/v1", "yerel-gguf"),
    ("Yerel sunucu", "http://127.0.0.1:8001/v1", "yerel-gguf"),
]

# İyi bilinen, ücretsiz dağıtılan GGUF modelleri (indirme betiği bunları kullanır)
ONERILEN_MODELLER: List[Dict[str, str]] = [
    {
        "kisa": "qwen2.5:0.5b",
        "ad": "Qwen2.5 0.5B Instruct (Q4_K_M)",
        "boyut": "~400 MB",
        "ram": "1 GB",
        "repo": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "dosya": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "not": "Deneme/test için. Hızlı, ama bilgisi sınırlı.",
    },
    {
        "kisa": "qwen2.5:3b",
        "ad": "Qwen2.5 3B Instruct (Q4_K_M)",
        "boyut": "~2.0 GB",
        "ram": "4 GB",
        "repo": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "dosya": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "not": "Zayıf donanım için dengeli seçim.",
    },
    {
        "kisa": "qwen2.5:7b",
        "ad": "Qwen2.5 7B Instruct (Q4_K_M)",
        "boyut": "~4.7 GB",
        "ram": "8 GB",
        "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "dosya": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "not": "Önerilen: kalite/hız dengesi en iyi olan model.",
    },
    {
        "kisa": "qwen2.5:14b",
        "ad": "Qwen2.5 14B Instruct (Q4_K_M)",
        "boyut": "~9.0 GB",
        "ram": "16 GB",
        "repo": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "dosya": "qwen2.5-14b-instruct-q4_k_m.gguf",
        "not": "Güçlü bilgisayarlar için; yüksek kaliteli fıkhî cevaplar.",
    },
    {
        "kisa": "qwen3:8b",
        "ad": "Qwen3 8B (Q4_K_M)",
        "boyut": "~5.0 GB",
        "ram": "9 GB",
        "repo": "Qwen/Qwen3-8B-GGUF",
        "dosya": "Qwen3-8B-Q4_K_M.gguf",
        "not": "Qwen'in yeni nesli; akıl yürütme yeteneği daha güçlü.",
    },
]


class YerelModel:
    """Sistem içi dil modeli köprüsü (HTTP arka uçları + isteğe bağlı süreç içi çıkarım)."""

    def __init__(self) -> None:
        self.arka_uc: Optional[str] = None      # örn. http://127.0.0.1:11434/v1
        self.arka_uc_adi: str = "yok"
        self.model_adi: str = ""
        self.sahte = os.environ.get("TUGRUL_YEREL_SAHTE") == "1"
        self._llama = None                       # llama-cpp-python örneği (tembel yüklenir)
        self._gguf: Optional[Path] = None
        self._son_kontrol = 0.0
        self._hazir_mesaj = ""

    # ------------------------------------------------------------------ ayarlar
    @property
    def baglam_butcesi(self) -> int:
        return int(os.environ.get("TUGRUL_YEREL_BAGLAM", "5000"))

    @property
    def maks_token(self) -> int:
        return int(os.environ.get("TUGRUL_YEREL_MAKS_TOKEN", "700"))

    @property
    def sicaklik(self) -> float:
        return float(os.environ.get("TUGRUL_YEREL_SICAKLIK", "0.6"))

    # ------------------------------------------------------------------ keşif
    def gguf_dosyalari(self) -> List[Path]:
        if not MODEL_DIZIN.exists():
            return []
        return sorted(MODEL_DIZIN.glob("*.gguf"))

    def _http_uygun(self, adres: str, zaman: float = 2.0) -> bool:
        try:
            with urllib.request.urlopen(adres.rstrip("/") + "/models", timeout=zaman) as y:
                return y.status == 200
        except Exception:
            return False

    def _model_adi_bul(self, taban: str) -> str:
        try:
            with urllib.request.urlopen(taban.rstrip("/") + "/models", timeout=3) as y:
                veri = json.loads(y.read().decode("utf-8"))
            kayitlar = veri.get("data") or []
            if kayitlar:
                return str(kayitlar[0].get("id") or kayitlar[0].get("name") or "yerel-model")
        except Exception:
            pass
        return ""

    def kesfet(self, zorla: bool = False) -> Dict[str, Any]:
        """Yerel arka uçları arar (sonuç önbelleğe alınır; 15 sn'de bir yenilenir)."""
        if self.sahte:
            self.arka_uc, self.arka_uc_adi, self.model_adi = "sahte://yerel", "Sahte model (test)", "sahte-qwen"
            return self.durum()
        simdi = time.time()
        if not zorla and self.arka_uc and simdi - self._son_kontrol < 15:
            return self.durum()
        self._son_kontrol = simdi

        # 1) Ortam değişkeniyle zorlanan adres
        zorlanan = os.environ.get("TUGRUL_YEREL_URL", "").strip()
        if zorlanan:
            if self._http_uygun(zorlanan):
                self.arka_uc = zorlanan.rstrip("/")
                self.arka_uc_adi = "Yerel sunucu (TUGRUL_YEREL_URL)"
                self.model_adi = os.environ.get("TUGRUL_YEREL_MODEL") or self._model_adi_bul(self.arka_uc) or "yerel-model"
            else:
                self.arka_uc, self.arka_uc_adi, self.model_adi = None, "yok (adres yanıt vermiyor)", ""
            return self.durum()

        # 2) Bilinen yerel arka uçlar
        for ad, taban, varsayilan_model in ADAY_ARKA_UCLAR:
            if self._http_uygun(taban):
                self.arka_uc = taban
                self.arka_uc_adi = ad
                self.model_adi = (os.environ.get("TUGRUL_YEREL_MODEL")
                                  or self._model_adi_bul(taban) or varsayilan_model)
                return self.durum()

        # 3) Süreç içi (llama-cpp-python) — models/*.gguf varsa
        gguf = self.gguf_dosyalari()
        if gguf:
            self.arka_uc = "surec-ici://llama-cpp"
            self.arka_uc_adi = "Süreç içi (llama-cpp-python)"
            self._gguf = gguf[0]
            self.model_adi = self._gguf.stem
            return self.durum()

        self.arka_uc, self.arka_uc_adi, self.model_adi = None, "yok", ""
        return self.durum()

    # ------------------------------------------------------------------ durum
    def hazir(self) -> bool:
        if self.arka_uc is None:
            self.kesfet()
        return bool(self.arka_uc)

    def durum(self) -> Dict[str, Any]:
        return {
            "hazir": bool(self.arka_uc),
            "arka_uc": self.arka_uc_adi,
            "adres": self.arka_uc or "",
            "model": self.model_adi,
            "anahtar_gerekli": False,
            "harici_servis": False,
            "indirilen_modeller": [p.name for p in self.gguf_dosyalari()],
            "model_dizini": str(MODEL_DIZIN),
            "onerilen_modeller": ONERILEN_MODELLER,
            "baglam_butcesi_karakter": self.baglam_butcesi,
            "maks_token": self.maks_token,
        }

    # ------------------------------------------------------------------ çıkarım
    def _govde(self, mesajlar: List[Dict[str, str]], akis: bool = True) -> bytes:
        return json.dumps({
            "model": self.model_adi or "yerel-model",
            "messages": mesajlar,
            "temperature": self.sicaklik,
            "max_tokens": self.maks_token,
            "stream": akis,
        }, ensure_ascii=False).encode("utf-8")

    def _sse_parcalari(self, satir: str) -> Optional[str]:
        """OpenAI uyumlu SSE satırından metin parçasını çıkarır."""
        satir = satir.strip()
        if not satir.startswith("data:"):
            return None
        veri = satir[5:].strip()
        if not veri or veri == "[DONE]":
            return None
        try:
            j = json.loads(veri)
        except Exception:
            return None
        secim = (j.get("choices") or [{}])[0]
        parca = (secim.get("delta") or {}).get("content")
        if parca is None:
            parca = (secim.get("message") or {}).get("content")
        return parca or None

    def uret(self, mesajlar: List[Dict[str, str]]) -> Iterator[str]:
        """Verilen mesajlara karşılık metin parçalarını üretir (senkron jeneratör)."""
        if self.sahte:
            yield from self._sahte_uret(mesajlar)
            return

        if not self.hazir():
            raise RuntimeError("Yerel model bulunamadı")

        # --- Süreç içi (llama-cpp-python) ---
        if self.arka_uc and self.arka_uc.startswith("surec-ici://"):
            yield from self._surec_ici_uret(mesajlar)
            return

        # --- HTTP (Ollama / llama.cpp / LM Studio …) ---
        istek = urllib.request.Request(
            self.arka_uc.rstrip("/") + "/chat/completions",
            data=self._govde(mesajlar, akis=True),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(istek, timeout=600) as y:
            for ham in y:
                parca = self._sse_parcalari(ham.decode("utf-8", "ignore"))
                if parca:
                    yield parca

    def _surec_ici_uret(self, mesajlar: List[Dict[str, str]]) -> Iterator[str]:
        """llama-cpp-python ile, Python sürecinin İÇİNDE çıkarım (harici sunucu yok)."""
        if self._llama is None:
            try:
                from llama_cpp import Llama  # type: ignore
            except Exception as hata:  # pragma: no cover - kurulum gerektirir
                raise RuntimeError(
                    "Süreç içi çıkarım için llama-cpp-python gerekli: "
                    "pip install llama-cpp-python"
                ) from hata
            if not self._gguf:
                raise RuntimeError("GGUF dosyası bulunamadı (models/ klasörü)")
            self._llama = Llama(
                model_path=str(self._gguf),
                n_ctx=int(os.environ.get("TUGRUL_YEREL_BAGLAM_PENCERE", "4096")),
                n_threads=int(os.environ.get("TUGRUL_YEREL_IS_PARCA", "0")) or None,
                verbose=False,
            )
        akis = self._llama.create_chat_completion(
            messages=mesajlar,
            temperature=self.sicaklik,
            max_tokens=self.maks_token,
            stream=True,
        )
        for parca in akis:
            secim = (parca.get("choices") or [{}])[0]
            metin = (secim.get("delta") or {}).get("content")
            if metin:
                yield metin

    def _sahte_uret(self, mesajlar: List[Dict[str, str]]) -> Iterator[str]:
        """Testler için deterministik sahte çıktı (ağ erişimi gerekmez)."""
        soru = next((m["content"] for m in reversed(mesajlar) if m["role"] == "user"), "")
        cevap = ("**Sahte yerel model yanıtı.** " + soru[:60] +
                 " — Bu çıktı, yerel model hattını (RAG bağlamı + akış) doğrulamak için üretilmiştir. "
                 "«Allah alışverişi helâl, faizi haram kılmıştır.» (Bakara 2/275)")
        for kelime in cevap.split(" "):
            yield kelime + " "
            time.sleep(0.0)

    # ------------------------------------------------------------------ yardımcılar
    def baglami_kirp(self, metin: str) -> str:
        """Küçük bağlam pencereli modellerde taşmayı önlemek için bağlamı kısaltır."""
        sinir = self.baglam_butcesi
        if len(metin) <= sinir:
            return metin
        return metin[:sinir] + "\n\n[…bağlam kısaltıldı…]"


yerel_model = YerelModel()
