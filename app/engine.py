"""
ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı
=========================================
Arama / cevaplama motoru.

TAMAMEN ÜCRETSİZ ve SINIRSIZ çalışır:
  * Harici bir yapay zeka API'si, anahtar (API key), abonelik veya kota YOKTUR.
  * İnternet bağlantısı olmadan da çalışır (bilgi bankası yerel JSON dosyalarındadır).
  * İstenildiği kadar soru sorulabilir; sınır, ücret, kayıt veya üyelik yoktur.

Yöntem:
  1. Türkçe metin normalizasyonu (büyük/küçük harf, aksan, ek soyma)
  2. BM25 tabanlı alan ağırlıklı arama (soru / anahtar kelime / kategori / cevap)
  3. Kalıp (ifade) eşleştirme + yazım hatası toleransı (fuzzy)
  4. Güvenilirlik ölçüsü ve "ilgili sorular" önerisi
  5. Hassas/kişisel konularda müftülüğe yönlendirme notu
  6. Acil durumlar (şiddet, kendine zarar) için özel güvenlik yanıtları
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).parent / "data"

# --------------------------------------------------------------------------------------
# 1) TÜRKÇE METİN NORMALİZASYONU
# --------------------------------------------------------------------------------------

_TR_LOWER = str.maketrans({
    "İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç", "Â": "â",
    "Î": "î", "Û": "û", "É": "é", "Ê": "ê",
})

# aksan sadeleştirme (arama kolaylığı için)
_FOLD = str.maketrans({
    "â": "a", "î": "i", "û": "u", "é": "e", "ê": "e", "ô": "o", "ä": "a",
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
})

_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """Metni arama için sadeleştirir: küçük harf + aksansız, tek boşluklu."""
    if not text:
        return ""
    text = text.translate(_TR_LOWER).lower()
    text = text.translate(_FOLD)
    # Arapça/Kur'an ayraçları ve noktalama → boşluk
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokens(text: str) -> List[str]:
    return _WORD_RE.findall(normalize(text))


# Ek soyma (hafif Türkçe gövdeleme). Kelimenin anlamını bozmadan yaygın ekleri atar.
_SUFFIXES = (
    "larindan", "lerinden", "larimiz", "lerimiz", "lardan", "lerden", "lariyla", "leriyle",
    "larini", "lerini", "lari", "leri", "larla", "lerle", "lar", "ler",
    "imizden", "inizden", "imizi", "imiz", "iniz", "dirler", "dirlar",
    "dan", "den", "tan", "ten", "nin", "nun", "sin", "sın",
    "dir", "dır", "dur", "dür", "tir", "tır", "tur", "tür",
    "im", "ım", "um", "üm", "in", "ın", "un", "ün",
    "da", "de", "ta", "te", "ya", "ye", "yi", "yı", "yu", "yü",
    "si", "sı", "su", "sü", "ci", "cı", "lik", "lık", "siz", "sız",
    "la", "le", "a", "e", "i", "ı", "u", "ü",
    "ken", "yken", "daki", "deki", "taki", "teki", "inci", "imsi",
    "diginde", "digi", "ecek", "acak", "mis", "mıs", "mek", "mak",
)


def stem(word: str) -> str:
    """Kelimeden yaygın Türkçe ekleri soyar (kaba fakat etkili)."""
    if len(word) <= 4:
        return word
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[: len(word) - len(suf)]
    return word


STOPWORDS = {
    "ve", "ile", "bir", "bu", "su", "o", "da", "de", "mi", "mu", "mı", "mü", "ne", "nedir",
    "nasil", "nasil", "neden", "nicin", "niye", "kac", "hangi", "kim", "nerede", "mi",
    "icin", "gore", "kadar", "daha", "en", "cok", "az", "var", "yok", "olur", "olurmu",
    "miyim", "miyiz", "misin", "misiniz", "bana", "ben", "benim", "biz", "bizim", "sen",
    "sizin", "onun", "onlar", "ise", "ama", "fakat", "ancak", "eger", "ya", "yani",
    "pek", "ise", "olan", "olarak", "oldugu", "hakkinda", "dair", "ilgili", "acaba",
    "cevap", "soru", "lutfen", "simdi", "aynen", "biliyorum", "soyle", "anlat",
}

# Çok sık geçen, ayırt ediciliği düşük kelimeler: puanlamada yarı ağırlıkla sayılır
LOW_SIGNAL = {
    "musluman", "muslumanlar", "islam", "islami", "islamda", "din", "dini", "dinimiz",
    "dinimizde", "dinen", "hukum", "hukmu", "meselesi", "konusu", "durum", "bilgi",
    "yapmak", "yapilir", "yapmali", "olmak", "olsun", "kisi", "kisinin",
}


def keywords(text: str) -> List[str]:
    out = []
    for w in tokens(text):
        if w in STOPWORDS or len(w) < 2:
            continue
        out.append(w)
        st = stem(w)
        if st != w and st not in STOPWORDS:
            out.append(st)
    return out


# Kavram yakınlıkları: sorgu tokenı → ek olarak aranacak tokenlar
SYNONYMS: Dict[str, List[str]] = {
    "tovbe": ["tevbe"], "tevbe": ["tovbe", "istigfar"],
    "istigfar": ["tevbe", "bagislanma"], "af": ["bagislanma", "tevbe"],
    "gasil": ["gusul"], "gusul": ["gasil", "boyabdesti"], "cenabet": ["cunup", "gusul"],
    "cunup": ["gusul"], "ihtilam": ["gusul"],
    "adet": ["hayiz"], "adetli": ["hayiz"], "regl": ["hayiz"], "hayiz": ["adet", "regl"],
    "lohusa": ["nifas"], "nifas": ["lohusa"],
    "namaz": ["salat"], "salat": ["namaz"],
    "abdest": ["vudu"], "vudu": ["abdest"],
    "zekat": ["sadaka"], "sadaka": ["zekat", "infak"], "fitre": ["fidye"],
    "fidye": ["fitre"], "kefaret": ["fidye"],
    "oruç": ["savm", "ramazan"], "oruc": ["savm", "ramazan"],
    "hac": ["kabe", "umre"], "umre": ["hac"],
    "kurban": ["udhiye"], "akika": ["kurban"],
    "buyu": ["sihir"], "sihir": ["buyu"], "medyum": ["buyu", "fal"],
    "fal": ["gayb"], "burc": ["astroloji", "gayb"], "astroloji": ["burc"],
    "cin": ["seytan", "vesvese"], "seytan": ["cin", "vesvese"], "vesvese": ["seytan", "cin"],
    "nazar": ["kemgoz"],
    "kader": ["irade", "takdir"], "takdir": ["kader"], "irade": ["kader"],
    "ahiret": ["kabir", "kiyamet", "cennet", "cehennem", "olim"],
    "kiyamet": ["ahiret"], "kabir": ["ahiret"], "cennet": ["ahiret"], "cehennem": ["ahiret"],
    "iman": ["itikad", "amentu"], "itikad": ["iman"], "amentu": ["iman"],
    "tevhid": ["sirk", "iman"], "sirk": ["tevhid"],
    "peygamber": ["nebi", "resul", "vahiy"], "nebi": ["peygamber"], "resul": ["peygamber"],
    "melek": ["cebrail", "gabriel"], "cebrail": ["melek"],
    "kuran": ["kitap", "vahiy", "meal"], "meal": ["kuran", "tefsir"], "tefsir": ["kuran"],
    "hadis": ["sunnet"], "sunnet": ["hadis"],
    "faiz": ["riba", "kredi", "banka"], "riba": ["faiz"], "banka": ["faiz", "kredi"],
    "kredi": ["faiz", "banka"], "kart": ["kredi", "faiz"],
    "haram": ["helal", "caiz"], "helal": ["haram", "caiz"], "caiz": ["helal", "haram", "hukum"],
    "gunah": ["haram", "sevap"], "sevap": ["gunah"],
    "icki": ["alkol", "sarap"], "alkol": ["icki"], "sarap": ["icki"],
    "domuz": ["helal", "jelatin"], "jelatin": ["helal", "domuz"], "karmin": ["helal"],
    "tesettur": ["basortusu", "kapanmak", "ortu", "giyim"], "basortusu": ["tesettur"],
    "kapanmak": ["tesettur"], "ortu": ["tesettur"],
    "muzik": ["sarki", "ilaji", "eglence"], "sarki": ["muzik"], "eglence": ["muzik"],
    "sigara": ["tutun", "zarar"], "uyusturucu": ["sigara", "haram"],
    "dovme": ["estetik"], "estetik": ["dovme", "ameliyat"], "kas": ["estetik", "dovme"],
    "sosyal": ["medya", "internet"], "medya": ["sosyal", "internet"],
    "internet": ["sosyal", "medya", "telefon"], "telefon": ["internet", "oyun"],
    "piyango": ["kumar", "sans"], "kumar": ["piyango", "bahis"],
    "kripto": ["bitcoin", "borsa"], "bitcoin": ["kripto"], "borsa": ["hisse", "kripto"],
    "yapayzeka": ["teknoloji"], "teknoloji": ["bilim", "yapayzeka"],
    "hayvan": ["cevre", "kedi", "kopek"], "cevre": ["hayvan", "doga"],
    "mezhep": ["hanefi", "safii", "maliki", "hanbeli"], "hanefi": ["mezhep"],
    "gayrimuslim": ["ehli", "kitap", "hristiyan", "yahudi"], "hristiyan": ["gayrimuslim"],
    "kismet": ["evlilik", "dua", "istihare"], "istihare": ["kismet", "dua"],
    "evlilik": ["nikah", "evlenmek", "es"], "nikah": ["evlilik"], "evlenmek": ["evlilik"],
    "bosanma": ["talak"], "talak": ["bosanma"], "iddet": ["bosanma", "talak"],
    "giybet": ["dedikodu"], "dedikodu": ["giybet"], "iftira": ["giybet", "yalan"],
    "yalan": ["dogruluk", "durustluk"], "durustluk": ["yalan", "dogruluk"],
    "ofke": ["sinir", "hidde"], "sinir": ["ofke"], "sabir": ["imtihan", "musibet"],
    "hastalik": ["saglik", "tedavi"], "saglik": ["hastalik", "tedavi"],
    "tedavi": ["doktor", "sifa"], "depresyon": ["ruhsagligi", "hastalik"],
    "dua": ["niyaz", "istigfar"], "zikir": ["tesbih", "dua"],
    "selam": ["selamun", "merhaba"], "komşu": ["komsuluk"], "komsu": ["komsuluk"],
    "miras": ["vasiyet"], "vasiyet": ["miras"],
    "cocuk": ["terbiye", "evlat"], "terbiye": ["cocuk", "egitim"],
    "ozur": ["helallik", "hak"], "helallik": ["kulhakki", "ozur"], "hak": ["helallik"],
    "af": ["bagislanma", "affetmek"],
    "sirket": ["ticaret"], "ticaret": ["kazanc", "helal"],
    "is": ["meslek", "kazanc"], "meslek": ["is", "kazanc"], "kazanc": ["helal", "ticaret"],
    "vakit": ["namaz", "imam"], "imam": ["cemaat", "namaz"], "cemaat": ["imam", "namaz"],
    "cuma": ["hutbe", "namaz"], "hutbe": ["cuma"],
    "teravih": ["ramazan", "namaz"], "vitir": ["namaz", "yatsi"],
    "sehiv": ["namaz", "hata"], "kaza": ["namaz"],
    "sefer": ["yolculuk", "seferi"], "yolculuk": ["sefer", "seferi"], "seferi": ["yolculuk"],
    "hastane": ["hastalik", "tedavi"], "organ": ["bagis", "tedavi"],
    "hayiz": ["adet"], "istem": ["hayiz"],
    "olunce": ["ahiret", "kabir", "olim"], "olum": ["ahiret", "kabir", "olim"],
    "vefat": ["ahiret", "olim", "cenaze"], "oldugunde": ["ahiret", "kabir"],
    "kafir": ["gayrimuslim"], "ehli": ["gayrimuslim", "kitap"],
    "zina": ["namus", "iffet", "flort"], "iffet": ["zina", "flort", "tesettur"],
    "es": ["evlilik", "nikah"], "esim": ["evlilik", "aile"], "koca": ["evlilik", "aile"],
    "cocuklar": ["cocuk"], "evlat": ["cocuk"],
    "kalp": ["gonul", "kulhakki"], "gonul": ["kalp", "kulhakki"],
    "hastalikta": ["hastalik"], "ruh": ["psikoloji", "depresyon"],
    "ekran": ["sosyal", "internet", "telefon"], "oyun": ["sosyal", "internet"],
    "yemek": ["gida", "helal"], "gida": ["yemek", "helal"],
    "para": ["kazanc", "faiz"], "islem": ["ticaret", "faiz"],
    "tedbir": ["hastalik", "saglik"], "as": ["tedavi", "hastalik"],
}


def expand(words: List[str]) -> List[str]:
    """Sorgu kelimelerini Kavram yakınlıkları ile genişletir (tekrarsız)."""
    out = list(words)
    seen = set(out)
    for w in words:
        syns = SYNONYMS.get(w)
        if not syns:
            syns = SYNONYMS.get(stem(w), ())
        for syn in syns or ():
            for form in (syn, stem(syn)):
                if form not in seen:
                    seen.add(form)
                    out.append(form)
    return out


# --------------------------------------------------------------------------------------
# 2) BİLGİ BANKASI (VERİ KATMANI)
# --------------------------------------------------------------------------------------

FIELD_WEIGHTS = {"anahtar": 4.0, "soru": 3.0, "kategori": 1.6, "cevap": 1.0}


class Entry:
    __slots__ = ("id", "kategori", "soru", "cevap", "anahtar", "kaynaklar", "field_tokens",
                 "n_soru", "n_anahtar", "key_phrases", "norm_soru", "index")

    def __init__(self, raw: Dict[str, Any], index: int):
        self.index = index
        self.id = raw["id"]
        self.kategori = raw.get("kategori", "Genel")
        self.soru = raw["soru"]
        self.cevap = raw["cevap"]
        self.anahtar = list(raw.get("anahtar", []))
        self.kaynaklar = list(raw.get("kaynaklar", []))
        self.field_tokens: Dict[str, List[str]] = {
            "soru": keywords(self.soru),
            "anahtar": [t for k in self.anahtar for t in keywords(k)],
            "kategori": keywords(self.kategori),
            "cevap": keywords(self.cevap[:4000]),
        }
        for f in self.field_tokens:
            self.field_tokens[f] = [stem(t) if t not in STOPWORDS else t for t in self.field_tokens[f]]
        self.n_soru = len(self.field_tokens["soru"])
        self.n_anahtar = len(self.field_tokens["anahtar"])
        self.norm_soru = normalize(self.soru)
        self.key_phrases = [normalize(k) for k in self.anahtar] + [normalize(w) for w in re.split(r"[,·/]", self.soru) if w.strip()]
        self.key_phrases = [p for p in self.key_phrases if len(p) >= 4]


def load_entries() -> List[Entry]:
    entries: List[Entry] = []
    files = sorted(DATA_DIR.glob("qa_*.json"))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        for raw in data:
            entries.append(Entry(raw, len(entries)))
    return entries


class Engine:
    """BM25 + ifade eşleştirme tabanlı, tamamen yerel/ücretsiz soru-cevap motoru."""

    def __init__(self, data_dir: Optional[Path] = None):
        global DATA_DIR
        if data_dir:
            DATA_DIR = data_dir
        self.entries: List[Entry] = load_entries()
        self.N = len(self.entries)
        self.df: Counter = Counter()
        self.avg_len: Dict[str, float] = {}
        self._build_index()

    # ---- indeks -------------------------------------------------------------------
    def _build_index(self) -> None:
        for e in self.entries:
            seen = set()
            for field, toks in e.field_tokens.items():
                for t in toks:
                    seen.add(t)
            for t in seen:
                self.df[t] += 1
        for field in FIELD_WEIGHTS:
            total = sum(len(e.field_tokens[field]) for e in self.entries) or 1
            self.avg_len[field] = total / max(self.N, 1)

    def idf(self, token: str) -> float:
        df = self.df.get(token, 0)
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5))

    # ---- temel puanlama ------------------------------------------------------------
    K1 = 1.4
    B = 0.65

    def _bm25_field(self, q: str, field: str, entry: Entry) -> float:
        toks = entry.field_tokens[field]
        if not toks:
            return 0.0
        tf = toks.count(q)
        if tf == 0:
            return 0.0
        if field == "cevap":
            tf = 1.0 + math.log(tf)   # metin uzunluğu/tekrarı skoru şişirmesin
        norm_len = len(toks) / (self.avg_len.get(field, 1) or 1)
        denom = tf + self.K1 * (1 - self.B + self.B * norm_len)
        return self.idf(q) * FIELD_WEIGHTS[field] * (tf * (self.K1 + 1)) / denom

    def _phrase_bonus(self, norm_query: str, query_tokens: List[str], entry: Entry) -> float:
        """Sorgu ile anahtar ifade örtüşmesi (tam veya kısmi) için bonus."""
        best = 0.0
        for p in entry.key_phrases:
            if p and (p in norm_query or norm_query in p):
                # kısa/jenerik ifadeler ("caiz mi", "nedir") tek başına belirleyici olmasın
                bonus = (1.1 + 0.08 * len(p)) if len(p) < 9 else (3.0 + 0.12 * len(p))
                best = max(best, bonus)
                continue
            pt = set(p.split())
            if not pt:
                continue
            inter = len(pt & set(query_tokens))
            if inter:
                ratio = inter / max(len(pt), len(query_tokens))
                if ratio >= 0.5:
                    best = max(best, 2.2 * ratio + 0.04 * len(pt))
        # Soru metninin kendisi ile örtüşme
        if entry.norm_soru and entry.norm_soru in norm_query:
            best = max(best, 3.5)
        # Harf düzeyinde yakınlık (yazım hatası toleransı)
        ratio = SequenceMatcher(None, norm_query, entry.norm_soru).ratio()
        if ratio > 0.72:
            best = max(best, 2.0 * ratio)
        return best

    def _score(self, norm_query: str, q_tokens: List[str], entry: Entry,
               weighted: Optional[List[Tuple[str, float]]] = None) -> float:
        score = 0.0
        pairs = weighted if weighted else [(t, 1.0) for t in q_tokens]
        for q, qw in pairs:
            w = qw * (0.45 if q in LOW_SIGNAL else 1.0)
            for field in FIELD_WEIGHTS:
                score += w * self._bm25_field(q, field, entry)
        score += self._phrase_bonus(norm_query, q_tokens, entry)
        # kapsama oranı: sorgunun kaçta kaçı dokümanda geçiyor
        if q_tokens:
            hit = sum(1 for q in set(q_tokens) if self.df.get(q, 0))
            coverage = hit / len(set(q_tokens))
            score *= 0.55 + 0.45 * coverage
        return score

    # ---- acil & özel durumlar ------------------------------------------------------
    SAFETY = [
        {
            "ad": "intihar",
            "re": r"(intihar|kendimi (oldur|öldur|asmak|öldürmek|bitirmek)|yasamak istemiyorum|yaşamak istemiyorum|artik dayanamiyorum|hayatima son|kendime zarar|kendimi kesmek)",
            "cevap": (
                "Seni duyuyorum ve bu acıyı ciddiye alıyorum. Şu an böyle hissediyor olman güçsüzlük değil; "
                "taşıdığın yükün ağır olduğunun işaretidir. Lütfen şu adımları bugün at:\n\n"
                "1. **Yalnız kalma.** Şu anda güvendiğin birini (aile, arkadaş, hoca) ara ya da yanına git.\n"
                "2. **Acil destek al:** Türkiye'de **112 Acil** ve **Sosyal Destek Hattı 183**'ü arayabilirsin. "
                "Bir ruh sağlığı uzmanına (psikiyatr/psikolog) başvurmak, dinen de tavsiye edilir.\n"
                "3. **Kendine bugün için söz ver:** 'Bugün, bir kişiyle konuşacağım.' Küçük bir adım yeter.\n\n"
                "Dinen: Can, Allah'ın emanetidir ve kimsenin kendi canına kıyma hakkı yoktur. Ama İslam, "
                "ümitsizliği de yasaklar: «Allah'ın rahmetinden ümit kesmeyin.» (Zümer 39/53) — Çünkü kapılar "
                "kapanmaz, kapanan gözlerdir. En karanlık gecede bile sabah vardır: «Şüphesiz güçlükle beraber "
                "bir kolaylık vardır.» (İnşirah 94/5-6)\n\n"
                "Ve bil ki: bu yalnızca bir bilgi aracıdır, seninle konuşacak gerçek bir insanın yerini tutamaz. "
                "Bugün bir insana ulaşman, atacağın en hayırlı adımdır. Sen değerlisin."
            ),
            "kategori": "Özel Destek",
        },
        {
            "ad": "siddet",
            "re": r"(esim (beni )?(dovuyor|dövüyor|dovdu|dövdü|siddet|şiddet)|kocam (beni )?(dovuyor|dövüyor|dovdu|dövdü)|esim beni (dovuyor|dövüyor|dövdü)|ailede siddet|siddet gor(u|ü)yorum|dayak yiyorum|babam beni dovuyor|kocam vuruyor|tecavuz|istismar)",
            "cevap": (
                "Öncelikle şunu net söyleyeyim: **İslam'da kadına/kişiye şiddet yoktur.** Şiddet, hangi kılıfla "
                "sunulursa sunulsun bir zulümdür ve büyük bir kul hakkıdır.\n\n"
                "**Şimdi güvenliğin birinci sıradadır:**\n"
                "1. **112 Acil**'i ara (tehlikedeyse hiç çekinme).\n"
                "2. **Aile ve Sosyal Hizmetler**: **183** hattı, kadın konukevleri ve hukuki destek için ilk adım.\n"
                "3. Yanına bir **güvendiğin kişiyi** al; güvenli bir yerde kal.\n"
                "4. Yaşadıklarını **kayda geçir** (not, tarih, varsa rapor) — hukukî süreçte çok işine yarar.\n\n"
                "**Dinî çerçeve:** Kur'an'ın aile için önerdiği yol **arabuluculuk ve hakem**dir (Nisâ 4/35); "
                "Hz. Peygamber hayatında hiçbir hanımına el kaldırmamıştır. \"Dövmek\" asla dinî bir hak değildir; "
                "aksine, mazlumun hakkı zalimde kalır.\n\n"
                "Şiddet gördüğün bir evde kalman gerekmiyor. Boşanma, İslam'da meşru bir çıkış yoludur ve şiddet "
                "gören kişinin sığınma, hukuk ve psikolojik destek alması **dinî bir haktır**. Ne yaşadıysan senin "
                "suçun değil. Bugün 183'ü ara ve bir kişiye anlat; yalnız değilsin."
            ),
            "kategori": "Özel Destek",
        },
        {
            "ad": "istismar",
            "re": r"(cocuga (cinsel )?istismar|çocuğa (cinsel )?istismar|istismara ugruyorum|istismar ediliyorum|taciz ediliyor|tacize ugradim|tacize uğradım)",
            "cevap": (
                "Çok ağır bir durumdur ve senin suçun kesinlikle değil.\n\n"
                "**Yapılacaklar:**\n"
                "1. **183** (Aile ve Sosyal Hizmetler) veya **112**'yi ara; çocuk istismarında **155 Polis İmdat** "
                "da kullanılabilir. Bu bir \"şikâyet\" değil, **koruma**dur.\n"
                "2. Güvenli bir yetişkinden (öğretmen, rehberlik, aile dostu, doktor) destek iste.\n"
                "3. Delilleri koru; tek başına yüzleşmek zorunda değilsin.\n\n"
                "Dinen: Zulme uğrayanın yanında olmak, sessiz kalmamak farzdır. «Mazlumun duası» en güçlü duadır; "
                "ancak bu, **hakkını aramak ve korunmak** sorumluluğunu ortadan kaldırmaz. Ruhsal destek (psikolog) "
                "almak da bir tedbirdir. Yaşadığın şeyde kimsenin günahı senin üzerine yüklenmez; sen korunmayı, "
                "iyileşmeyi ve hayata devam etmeyi hak ediyorsun."
            ),
            "kategori": "Özel Destek",
        },
    ]

    SMALLTALK = [
        (r"^(selam|selamin aleykum|selamun aleykum|esselamu aleykum|merhaba|hey|hi|hello|gunaydin|iyi gunler|iyi aksamlar)[\s!.?]*$",
         "Aleyküm selam ve rahmetullah! 🌙 Hoş geldin. Ben **Şeyh Tuğrul** — İslami konularda sorularına bu bilgi "
         "bankasından cevap veriyorum. Namaz, abdest, oruç, zekât, hac, aile, helâl-haram, ahlâk… aklına ne gelirse "
         "sor. Ücretsiz ve sınırsız! (Yine de kişisel ve hassas durumlar için bir müftülüğe danışmanı öneririm.)"),
        (r"(tesekkur|teşekkür|sagol|sağol|allah razi olsun|allah razı olsun|eyvallah)",
         "Allah senden de razı olsun, bereket versin. 🤲 Başka bir sorun olursa her zaman buradayım. "
         "«Rabbiniz buyurdu: Bana dua edin, size cevap vereyim.» (Gâfir 40/60)"),
        (r"(sen kimsin|kimsin|adin ne|adın ne|nesin|sen bir (ai|yapay zeka)|yapay zeka misin|robot musun)",
         "Ben **ŞEYH TUĞRUL** — İslami Yapay Zeka Danışmanı. 🤖📖\n\n"
         "Beni farklı kılan şey şu:\n"
         "- **%100 ücretsiz** ve **sınırsız**: abonelik, kayıt, ücret, soru limiti yok.\n"
         "- **Tamamen yerel bir bilgi bankasından** cevap veriyorum: Kur'an, sahih hadis ve fıkıh esaslarına "
         "dayalı, hazırlanmış ilmi cevaplar. Harici bir yapay zeka servisi kullanmam.\n"
         "- Kaynak gösteririm, ihtilaflı konularda ihtilafı söylerim.\n\n"
         "**Önemli:** Ben bir müftü değilim; verdiğim bilgiler genel bilgilendirme içindir. Kişisel, hassas ve "
         "hukukî sonuç doğuran konularda mutlaka bir **müftülüğe** veya ehline danış."),
        (r"(ne yapabilirsin|nasil kullanilir|nasıl kullanılır|yardim|yardım|ne sorabilirim|konular|ornek soru|örnek soru)",
         "Şu konularda soru sorabilirsin:\n\n"
         "- **İbadet:** Namaz, abdest, gusül, oruç, zekât, hac, dua, Kur'an\n"
         "- **İnanç:** İman esasları, kader, tevbe, ahiret, cin-şeytan, büyü\n"
         "- **Aile:** Nikâh, boşanma, eş ve çocuk hakları, terbiye\n"
         "- **Helâl-Haram:** Faiz, helâl gıda, müzik, sigara, kumar, kripto\n"
         "- **Ahlâk:** Gıybet, yalan, öfke, sabır, anne-baba hakkı\n"
         "- **Günlük hayat:** Dua, zikir, sosyal medya, sağlık, iş ahlakı\n\n"
         "Sorunu doğal bir dille yaz: *\"Faizli kredi caiz mi?\"*, *\"Namaz kılmıyorum, nasıl başlarım?\"*, "
         "*\"Adetliyken Kur'an okunur mu?\"* gibi. Ne kadar net sorarsan o kadar isabetli cevap veririm."),
    ]

    CATEGORY_ALIASES: Dict[str, str] = {
        # Yalnızca "şemsiye" (üst başlık) kelimeler; özel kavramlar (kader, cin, faiz,
        # gusül gibi) kendi kayıtlarına yönlensin diye burada YER ALMAZ.
        "namaz": "Namaz", "salat": "Namaz", "namazlar": "Namaz",
        "abdest": "Taharet", "taharet": "Taharet", "temizlik": "Taharet",
        "oruc": "Oruç", "ramazan": "Oruç", "savm": "Oruç",
        "zekat": "Zekât", "sadaka": "Zekât", "infak": "Zekât",
        "hac": "Hac", "umre": "Hac",
        "aile": "Aile", "ailem": "Aile",
        "helal": "Helâl-Haram", "haram": "Helâl-Haram",
        "ahlak": "Ahlâk", "edep": "Ahlâk", "adab": "Ahlâk",
        "dua": "Dua", "zikir": "Dua",
        "kuran": "Kur'an", "meal": "Kur'an", "tefsir": "Kur'an",
        "iman": "İnanç", "itikad": "İnanç", "akaid": "İnanç", "inanc": "İnanç",
        "gunluk": "Günlük Hayat", "hayat": "Günlük Hayat",
    }

    def _category_overview(self, q_base: List[str], q_norm: str) -> Optional[Dict[str, Any]]:
        """'namaz', 'zekat gibi', 'oruç' gibi kısa jenerik sorularda konu listesi sunar."""
        if len(q_base) > 2:
            return None
        cat = None
        for t in q_base:
            if t in self.CATEGORY_ALIASES:
                cat = self.CATEGORY_ALIASES[t]
                break
        if not cat:
            for t in q_norm.split():
                if t in self.CATEGORY_ALIASES:
                    cat = self.CATEGORY_ALIASES[t]
                    break
        if not cat or cat == "Genel":
            return None
        items = [e for e in self.entries if e.kategori == cat][:8]
        baslik = {
            "Namaz": "🕌 **Namaz** hakkında en çok sorulanlar:",
            "Taharet": "💧 **Taharet (abdest, gusül, temizlik)** hakkında en çok sorulanlar:",
            "Oruç": "🌙 **Oruç ve Ramazan** hakkında en çok sorulanlar:",
            "Zekât": "💰 **Zekât, fitre ve sadaka** hakkında en çok sorulanlar:",
            "Hac": "🕋 **Hac, umre ve kurban** hakkında en çok sorulanlar:",
            "Aile": "🏡 **Aile ve evlilik** hakkında en çok sorulanlar:",
            "Helâl-Haram": "⚖️ **Helâl ve haram** hakkında en çok sorulanlar:",
            "Ahlâk": "🌿 **Ahlâk ve edep** hakkında en çok sorulanlar:",
            "Dua": "🤲 **Dua ve zikir** hakkında en çok sorulanlar:",
            "Kur'an": "📖 **Kur'an-ı Kerim** hakkında en çok sorulanlar:",
            "İnanç": "🕊️ **İnanç (akaid)** hakkında en çok sorulanlar:",
            "Günlük Hayat": "🌍 **Günlük hayat** hakkında en çok sorulanlar:",
        }.get(cat, f"**{cat}** hakkında en çok sorulanlar:")
        lines = [baslik, ""]
        for e in items:
            lines.append(f"- {e.soru}")
        lines.append("")
        lines.append("Aşağıdaki başlıklardan birine dokunarak ayrıntılı cevabı görebilirsin.")
        return {
            "bulundu": True, "tip": "kategori", "guven": 0.9, "kategori": cat,
            "soru": f"{cat} — konu listesi", "cevap": "\n".join(lines), "kaynaklar": [],
            "ilgili": [{"id": e.id, "soru": e.soru, "kategori": e.kategori} for e in items],
            "notlar": [],
        }

    def _safety(self, q_norm: str) -> Optional[Dict[str, Any]]:
        for rule in self.SAFETY:
            if re.search(rule["re"], q_norm):
                return {
                    "bulundu": True, "tip": "guvenlik", "guven": 1.0,
                    "kategori": rule["kategori"], "soru": "Destek", "cevap": rule["cevap"],
                    "kaynaklar": ["Öncelik: Güvenlik ve sağlık", "Kur'an: ez-Zümer 39/53, el-İnşirâh 94/5-6"],
                    "ilgili": [], "notlar": [
                        "Bu yanıt bir bilgi aracının verebileceği sınırlı destek içindir; gerçek bir insandan "
                        "yardım almanın yerini tutmaz.",
                    ],
                }
        return None

    def _smalltalk(self, q_norm: str) -> Optional[Dict[str, Any]]:
        for pattern, reply in self.SMALLTALK:
            if re.search(pattern, q_norm):
                return {
                    "bulundu": True, "tip": "sohbet", "guven": 1.0, "kategori": "Şeyh Tuğrul",
                    "soru": "Sohbet", "cevap": reply, "kaynaklar": [], "ilgili": self._popular(),
                    "notlar": [],
                }
        return None

    # ---- ana akış ------------------------------------------------------------------
    def ask(self, question: str, detay: str = "normal", top_k: int = 3) -> Dict[str, Any]:
        q_norm = normalize(question)
        if not q_norm:
            return {
                "bulundu": False, "tip": "bos", "guven": 0.0, "kategori": "", "soru": "",
                "cevap": "Sorunu yazmayı unutmuş olabilirsin 🙂 Aklındaki soruyu yaz, hemen cevaplayayım.",
                "kaynaklar": [], "ilgili": self._popular(), "notlar": [],
            }

        special = self._safety(q_norm) or self._smalltalk(q_norm)
        if special:
            return special

        q_base = keywords(question)
        q_tokens = expand(q_base)
        base_set = set(q_base)
        # Uzun cümlelerde yalnızca anlamlı tokenlar (sıra korunur)
        q_unique = list(dict.fromkeys(q_tokens))
        # Kullanıcının kendi yazdığı kelimeler tam, eşanlamlı ile eklenenler yarım ağırlıkta
        q_weighted = [(t, 1.0 if t in base_set else 0.45) for t in q_unique]

        scores: List[Tuple[float, Entry]] = []
        for e in self.entries:
            s = self._score(norm_query=q_norm, q_tokens=q_unique, entry=e, weighted=q_weighted)
            if s > 0:
                scores.append((s, e))
        scores.sort(key=lambda x: (-x[0], x[1].index))

        if not scores:
            return self._belirsiz(question, self._fuzzy_candidates(q_norm))

        best_score, best = scores[0]

        # Güven dönüşümü (0-1)
        guven = best_score / (best_score + 5.5) if best_score > 0 else 0.0

        if best_score < 1.6:
            overview = self._category_overview(q_base, q_norm)
            if overview:
                return overview
            return self._belirsiz(question, [e for _, e in scores[:4]])

        if len(q_base) <= 1:
            overview = self._category_overview(q_base, q_norm)
            if overview:
                return overview

        related = [e for _, e in scores[1:top_k + 1] if _ > best_score * 0.35] or self._same_category(best)

        cevap = best.cevap
        if detay == "kisa":
            cevap = self._shorten(cevap)

        notlar = []
        if guven < 0.55:
            notlar.append("Bu cevap, sorunuza en yakın kaydın özetidir; sorunuzu biraz daha "
                          "netleştirirsen daha isabetli cevap verebilirim.")
        if self._needs_fatwa(best, question):
            notlar.append("Bu konu **içtihat/ihtilaf** içerir. Kişisel durumunuz için İl/İlçe "
                          "Müftülüğü'ne danışmanız en doğrusudur.")
        notlar.append("Bu bilgi genel bilgilendirme içindir; kişisel durumunuz için bir müftülüğe danışın. "
                      "Ben bir müftü değilim.")

        return {
            "bulundu": True,
            "tip": "cevap",
            "guven": round(guven, 3),
            "kategori": best.kategori,
            "soru": best.soru,
            "cevap": cevap,
            "kaynaklar": best.kaynaklar,
            "ilgili": [{"id": e.id, "soru": e.soru, "kategori": e.kategori} for e in related],
            "notlar": notlar,
        }

    def _needs_fatwa(self, entry: Entry, question: str) -> bool:
        sensitive = {"Helâl-Haram", "Aile", "Genel"}
        q = normalize(question)
        triggers = ("bosanma", "talak", "faiz", "kripto", "miras", "iddet", "kefaret", "talâk")
        return entry.kategori in sensitive or any(t in q for t in triggers)

    @staticmethod
    def _shorten(cevap: str) -> str:
        parts = cevap.split("\n\n")
        if len(parts) <= 1:
            return cevap
        out = parts[0]
        for p in parts[1:]:
            if p.startswith("|") or p.startswith("-") or p.startswith("*"):
                out += "\n\n" + p
            if len(out) > 420:
                break
        return out

    # ---- yardımcılar ---------------------------------------------------------------
    def _popular(self, n: int = 4) -> List[Dict[str, str]]:
        ids = ["namaz-rekatlari", "abdest-nasil-alinir", "orucu-bozanlar", "tevbe-nasil-yapilir"]
        out = []
        for e in self.entries:
            if e.id in ids:
                out.append({"id": e.id, "soru": e.soru, "kategori": e.kategori})
        return out[:n] or [{"id": e.id, "soru": e.soru, "kategori": e.kategori} for e in self.entries[:n]]

    def _same_category(self, entry: Entry, n: int = 3) -> List[Entry]:
        return [e for e in self.entries if e.kategori == entry.kategori and e.id != entry.id][:n]

    def _belirsiz(self, question: str, candidates: Optional[List[Entry]] = None) -> Dict[str, Any]:
        if not candidates:
            candidates = self._fuzzy_candidates(normalize(question))
        ilgili: List[Any] = candidates or self._popular(5)
        if ilgili and isinstance(ilgili[0], dict):
            ilgili = [self.by_id(x["id"]) or x for x in ilgili]
        metin = (
            "Bilgi bankamda bu sorunun **tam karşılığını** bulamadım ama en yakın konuları aşağıda listeledim. "
            "Sorunu şu şekilde yeniden yazarsan çok daha isabetli cevap verebilirim:\n\n"
            "- Konu adını söyleyin: *\"zekât\"*, *\"abdest\"*, *\"cuma namazı\"*\n"
            "- Ne öğrenmek istediğinizi belirtin: *\"... nasıl yapılır?\"*, *\"... caiz mi?\"*, *\"... kaç rekât?\"*\n\n"
            "**Örnek:** *\"Namaz kılmıyorum, yeniden nasıl başlarım?\"*"
        )
        return {
            "bulundu": False,
            "tip": "belirsiz",
            "guven": 0.0,
            "kategori": "Genel",
            "soru": question.strip()[:120],
            "cevap": metin,
            "kaynaklar": [],
            "ilgili": [{"id": e.id, "soru": e.soru, "kategori": e.kategori}
                       if isinstance(e, Entry) else e for e in ilgili[:5]],
            "notlar": ["Sonuç bulunamadıysa, konu tek kelimeyle (örneğin *faiz*) yeniden yazabilirsin. "
                       "Cevap bulunamayan konular için müftülüğe danışman isabetli olur."],
        }

    def _fuzzy_candidates(self, q_norm: str, limit: int = 5) -> List[Entry]:
        """Yazım hatası / farklı ifade durumunda harf düzeyinde en yakın kayıtlar."""
        scored = []
        for e in self.entries:
            r1 = SequenceMatcher(None, q_norm, e.norm_soru).ratio()
            r2 = max((SequenceMatcher(None, q_norm, p).ratio() for p in e.key_phrases), default=0.0)
            qt = set(q_norm.split())
            et = set(e.norm_soru.split())
            jacc = len(qt & et) / max(len(qt | et), 1)
            scored.append((max(r1, r2, jacc * 1.4), e))
        scored.sort(key=lambda x: -x[0])
        return [e for s, e in scored[:limit] if s > 0.42]

    # ---- API yardımcı verileri ------------------------------------------------------
    def kategoriler(self) -> List[Dict[str, Any]]:
        counts = Counter(e.kategori for e in self.entries)
        order = ["İnanç", "Taharet", "Namaz", "Oruç", "Zekât", "Hac", "Aile", "Helâl-Haram",
                 "Ahlâk", "Dua", "Kur'an", "Günlük Hayat", "Genel"]
        cats = sorted(counts.items(), key=lambda kv: (order.index(kv[0]) if kv[0] in order else 99, kv[0]))
        return [{"kategori": k, "adet": v} for k, v in cats]

    def sorular(self, kategori: Optional[str] = None) -> List[Dict[str, str]]:
        out = []
        for e in self.entries:
            if kategori and e.kategori != kategori:
                continue
            out.append({"id": e.id, "kategori": e.kategori, "soru": e.soru})
        return out

    def by_id(self, entry_id: str) -> Optional[Entry]:
        for e in self.entries:
            if e.id == entry_id:
                return e
        return None

    def istatistik(self) -> Dict[str, Any]:
        return {
            "toplam_kayit": self.N,
            "kategoriler": self.kategoriler(),
            "ucret": "Ücretsiz ve sınırsız",
            "motor": "Yerel bilgi bankası (BM25 + ifade eşleştirme)",
            "internet_gerekli": False,
        }


# Tekil motor örneği
engine = Engine()
