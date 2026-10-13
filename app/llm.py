"""
ŞEYH TUĞRUL — Yüksek parametreli dil modeli (LLM) katmanı
=========================================================
Uygulama iki katmanlı çalışır:

  1. **Yerel bilgi bankası (RAG kaynağı)** — `app/data/*.json`: doğrulanmış
     soru-cevap kayıtları + pasaj indeksi. Tamamen çevrimdışı, ücretsiz.
  2. **Yüksek parametreli dil modeli (isteğe bağlı)** — Gemini / Groq /
     OpenRouter / yerel Ollama gibi ücretsiz erişilebilen modeller.
     Model çağrısı **kullanıcının tarayıcısından** yapılır:
       • API anahtarı sunucuya gitmez, kullanıcının cihazında (localStorage) kalır,
       • sunucu üzerinden ücret/kota tüketimi olmaz,
       • anahtar yoksa uygulama otomatik olarak yerel motora düşer.

Bu modül; sistem yönergesini (persona + fıkıh kuralları) ve sağlayıcı
tanımlarını tek yerde tutar. Arayüz bunları `/api/model` üzerinden alır.
"""

from __future__ import annotations

from typing import Any, Dict, List

# --------------------------------------------------------------------------------------
# SİSTEM YÖNERGESİ — modelin uyması zorunlu kurallar
# --------------------------------------------------------------------------------------
SISTEM_PROMPTU = """Sen "Şeyh Tuğrul" adlı, Türkçe konuşan bir İslam âlimi asistanısın.
Ehl-i Sünnet çizgisinde, Hanefî fıkhını esas alan, muteber kaynaklara bağlı bir din danışmanısın.

GÖREVİN: Kullanıcının İslami sorusunu delile dayalı, akıcı ve güvenilir biçimde cevaplamak.

KESİN KURALLAR
1) DELİL ZORUNLU: Cevabı Kur'an âyetleri (sûre/âyet numarasıyla), sahih hadisler (Buhârî, Müslim,
   Ebû Dâvûd, Tirmizî vb. kaynak adı ve kitap/bâb bilgisiyle) ve güvenilir fıkıh kaynaklarıyla destekle.
2) UYDURMA YASAK: Âyet, hadis, kitap adı veya âlim sözü uydurma. Emin olmadığın rivayeti aktarma;
   "bu konuda sahih bir delil bilmiyorum" ya da "âlimler ihtilaf etmiştir" demek dürüstlüktür.
3) İHTİLAF: Mezhepler arasında görüş farkı varsa belirt (örn. "Hanefî'ye göre ... Şâfiî'ye göre ..."),
   tercih edilen görüşü ve gerekçesini söyle. Tek doğruyu dayatmaz, kolaylaştırıcı olursun.
4) FETVA DEĞİL, BİLGİ: Kişiye özel hukuki sonuç doğuran konularda (miras payı hesabı, talâk/boşanma,
   ceza, tazminat, velayet, nafaka) kesin fetva verme; genel hükmü açıkla ve İl/İlçe Müftülüğü'ne yönlendir.
5) ACİL DURUM: İntihar, kendine zarar, şiddet, istismar, tıbbi acil durum varsa önce şefkatle yaklaş;
   ardından 112 Acil ve 183 Sosyal Destek Hattı'na yönlendir. Asla kınama, asla suçlama.
6) ÜSLUP: Sıcak, saygılı, sade Türkçe. Kısa paragraflar, gerektiğinde madde işaretleri kullan.
   Arapça terimleri (namaz, abdest, ribâ, fevâid...) kısaca açıkla.
7) BAĞLAM: Aşağıda "YEREL BİLGİ BANKASI" bölümünde bu uygulamanın doğrulanmış kayıtları verilir.
   Soruyla ilgili olanları kullan ve cevabı onlarla uyumlu kur; bağlam yetersizse kendi bilginle tamamla.
   Bağlamda açık hata/çelişki görürsen sahih olanı esas al.
8) ASLA tekfir etme, hakaret etme, aşağılama. Farklı görüşlere ve farklı mezheplere saygılı ol.
9) Kullanıcı başka bir dilde yazarsa aynı dilde cevap ver.
10) Gereksiz uzatma; ama soru ayrıntı istiyorsa doyurucu ol. Uygun yerde "🤲" ile dua temennisinde bulunabilirsin.
11) Selam verilirse "Aleyküm selam ve rahmetullah" ile karşılık ver."""

# --------------------------------------------------------------------------------------
# SAĞLAYICILAR — hepsi ücretsiz katmanla kullanılabilir
# --------------------------------------------------------------------------------------
SAGLAYICILAR: List[Dict[str, Any]] = [
    {
        "id": "gemini",
        "ad": "Google Gemini (ücretsiz)",
        "tur": "gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent",
        "anahtar_linki": "https://aistudio.google.com/apikey",
        "anahtar_ipucu": "AIza...",
        "modeller": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
        "not": "Google AI Studio: kredi kartı istemez, günde ~1.500 istek ücretsiz. Tarayıcıdan doğrudan çalışır.",
    },
    {
        "id": "groq",
        "ad": "Groq — Llama 3.3 70B / GPT-OSS 120B (ücretsiz)",
        "tur": "openai",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "anahtar_linki": "https://console.groq.com/keys",
        "anahtar_ipucu": "gsk_...",
        "modeller": [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.1-8b-instant",
        ],
        "not": "70B ve 120B parametreli modeller; çok hızlı. Ücretsiz katman: dakikada 30, günde 1.000 istek.",
    },
    {
        "id": "openrouter",
        "ad": "OpenRouter — ücretsiz dev modeller (235B+)",
        "tur": "openai",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "anahtar_linki": "https://openrouter.ai/keys",
        "anahtar_ipucu": "sk-or-v1-...",
        "modeller": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen3-235b-a22b:free",
            "openai/gpt-oss-120b:free",
            "deepseek/deepseek-r1:free",
            "nvidia/llama-3.1-nemotron-ultra-253b:free",
        ],
        "not": "235B–405B'ye varan ücretsiz modeller (:free uzantısı zorunlu). Günde ~50 istek.",
    },
    {
        "id": "ollama",
        "ad": "Kendi bilgisayarım — Ollama (sınırsız, çevrimdışı)",
        "tur": "openai",
        "url": "http://localhost:11434/v1/chat/completions",
        "anahtar_linki": "https://ollama.com/download",
        "anahtar_ipucu": "gerekmez",
        "modeller": ["llama3.1:8b", "qwen2.5:14b", "qwen2.5:32b", "gemma2:27b", "deepseek-r1:14b"],
        "not": "Tamamen ücretsiz ve sınırsız: model kendi bilgisayarında çalışır. " +
               "Ollama'yı başlatırken OLLAMA_ORIGINS=* ver (tarayıcı erişimi için).",
    },
    {
        "id": "ozel",
        "ad": "Diğer (OpenAI uyumlu kendi sunucunuz)",
        "tur": "openai",
        "url": "",
        "anahtar_linki": "",
        "anahtar_ipucu": "sk-...",
        "modeller": [],
        "not": "OpenAI uyumlu her servis (DeepSeek, Together, vLLM, LM Studio, kendi sunucunuz). URL'yi tam girin.",
    },
]

# Kullanıcı mesajı şablonu — tarayıcı bunu bağlamla doldurup gönderir
KULLANICI_SABLONU = """YEREL BİLGİ BANKASI ({kayit_sayisi} kayıt / {pasaj_sayisi} pasaj arasından en ilgili bölümler)
=====================================================================

{baglam}

=====================================================================
KULLANICI SORUSU: {soru}

Yukarıdaki yerel bilgi bankası bağlamını dikkate alarak soruyu cevapla. Soru bağlamda geçiyorsa
kaynakla uyumlu cevap ver; bağlamda yoksa kendi ilminle cevapla. Gerekirse bilgi bankasındaki
kayıtların başlıklarına atıf yapabilirsin."""


def model_bilgisi() -> Dict[str, Any]:
    """Arayüzün ihtiyaç duyduğu sistem yönergesi + sağlayıcı listesi."""
    return {
        "sistem_promptu": SISTEM_PROMPTU,
        "kullanici_sablonu": KULLANICI_SABLONU,
        "saglayicilar": SAGLAYICILAR,
        "mod": "RAG (yerel bilgi bankası) + yüksek parametreli dil modeli (tarayıcıdan)",
        "gizlilik": "API anahtarı yalnızca sizin tarayıcınızda saklanır; sunucuya gönderilmez.",
    }


def baglam_metni(kayitlar: List[Dict[str, Any]], pasajlar: List[Dict[str, Any]]) -> str:
    """Kütüphane kullanımı için: kayıt ve pasajları modele verilecek metne çevirir."""
    parcalar: List[str] = []
    for i, k in enumerate(kayitlar, 1):
        kaynak = "; ".join(k.get("kaynaklar") or [])
        parcalar.append(
            f"[KAYIT {i}] ({k.get('kategori','')}) {k.get('soru','')}\n"
            f"{k.get('cevap','')}\n"
            f"Kaynaklar: {kaynak}"
        )
    if pasajlar:
        parcalar.append("---- İLGİLİ BÖLÜMLER ----")
        for i, p in enumerate(pasajlar, 1):
            parcalar.append(f"[BÖLÜM {i}] ({p.get('kategori','')}) {p.get('soru','')}\n{p.get('metin','')}")
    return "\n\n".join(parcalar)
