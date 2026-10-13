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
from datetime import datetime, timezone
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
        self.passages: List[Dict[str, Any]] = []
        self.pass_avg: float = 1.0
        self._build_index()
        self._build_passages()

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

    # ---- paragraf (pasaj) araması ---------------------------------------------------
    K1P, BP = 1.2, 0.6

    def _build_passages(self) -> None:
        """Her cevabı anlamlı parçalara (pasajlara) böler ve indeksler.

        Böylece tam karşılığı olmayan bir soruda bile, bilgi bankasındaki en ilgili
        bölümler kaynağıyla birlikte gösterilebilir.
        """
        self.passages = []
        for e in self.entries:
            bloklar = [b.strip() for b in re.split(r"\n\s*\n", e.cevap) if b.strip()]
            parcalar: List[str] = []
            for b in bloklar:
                if "\n" in b or len(b) > 650:
                    parcalar.extend(x.strip() for x in b.split("\n") if x.strip())
                else:
                    parcalar.append(b)
            for b in parcalar:
                temiz = re.sub(r"[*|#>•\-]+", " ", b)
                toks = [stem(t) for t in tokens(temiz) if t not in STOPWORDS and len(t) > 2]
                if len(toks) < 3:
                    continue
                self.passages.append({
                    "entry": e,
                    "metin": b,
                    "toks": Counter(toks),
                    "uzunluk": len(toks),
                    "norm": normalize(temiz),
                })
        toplam = sum(p["uzunluk"] for p in self.passages) or 1
        self.pass_avg = toplam / max(len(self.passages), 1)

    def _pasaj_puan(self, pas: Dict[str, Any], q_weighted: List[Tuple[str, float]]) -> Tuple[float, int]:
        score, hits = 0.0, 0
        for q, qw in q_weighted:
            tf = pas["toks"].get(q, 0)
            if not tf:
                continue
            hits += 1
            norm_len = pas["uzunluk"] / (self.pass_avg or 1)
            denom = tf + self.K1P * (1 - self.BP + self.BP * norm_len)
            score += qw * self.idf(q) * (tf * (self.K1P + 1)) / denom
        if hits >= 2:
            score *= 1.3
        return score, hits

    def ilgili_pasajlar(self, q_weighted: List[Tuple[str, float]],
                        haric: Optional[set] = None, limit: int = 3,
                        esik: float = 1.4) -> List[Dict[str, Any]]:
        """Soruya en yakın paragrafları (farklı kayıtlardan) döndürür."""
        haric = haric or set()
        bulunan: List[Tuple[float, int, Dict[str, Any]]] = []
        for pas in self.passages:
            if pas["entry"].id in haric:
                continue
            sc, hits = self._pasaj_puan(pas, q_weighted)
            if sc >= esik and hits >= 1:
                bulunan.append((sc, hits, pas))
        bulunan.sort(key=lambda x: -x[0])
        secilen: List[Dict[str, Any]] = []
        kullanilan: Dict[str, int] = {}
        for sc, hits, pas in bulunan:
            eid = pas["entry"].id
            if kullanilan.get(eid, 0) >= 2:      # aynı kayıttan en fazla 2 pasaj
                continue
            kullanilan[eid] = kullanilan.get(eid, 0) + 1
            secilen.append({"kayit": pas["entry"], "metin": pas["metin"], "puan": round(sc, 2)})
            if len(secilen) >= limit:
                break
        return secilen

    # ---- genel usul / ilke cevapları (tam kayıt bulunamazsa) ------------------------
    ILKELER = [
        {
            "ad": "hukum",
            "re": r"(caiz mi|caizmidir|caiz olur mu|caiz midir|haram mi|helal mi|gunah mi|gunahi var mi|"
                  r"yasak mi|hukmu nedir|hukmu ne|fetva|dinen uygun mu|dinen dogru mu|"
                  r"dinen sakincali|buna izin var mi|olmaz mi|seriat|dinen)",
            "cevap": (
                "Bu sorunun **özel hükmünü** bilgi bankamda bulamadım; ama sana hükmü doğru şekilde "
                "öğrenmenin yolunu vereyim — böylece her yeni meseleyi kendin de değerlendirebilirsin:\n\n"
                "**1. Aslolan mübahlıktır (helâllik):** «Yeryüzünde olan şeylerin hepsini sizin için yarattı.» "
                "(Bakara 2/29) Bir şeyin haram olduğu **açık bir delille** sabit olmadıkça haram sayılmaz.\n"
                "**2. Haram ancak nass ile sabit olur:** Kur'an, sahih sünnet veya kesin icmâ. Kulaktan dolma "
                "«filanca haram demiş» sözü hüküm kurmaz.\n"
                "**3. Şüpheli şeylerden kaçın (takva):** «Helâl apaçık, haram apaçık; ikisi arasında şüpheli "
                "şeyler vardır.» (Buhârî, Müslim)\n"
                "**4. Zarûret, haramı geçici olarak kaldırır:** «Kim zarûrette kalırsa, saldırmamak ve haddi "
                "aşmamak şartıyla (haramdan) yiyebilir.» (Bakara 2/173)\n"
                "**5. İhtilafları bil:** Âlimler bazı konularda farklı içtihat eder; «en zoru» seçmek de "
                "«en kolayı» seçmek de doğru yöntem değildir — ehline sormak esastır: «Bilmediğinizde ehline "
                "sorun.» (Nahl 16/43)\n\n"
                "**Şimdi ne yapabilirsin?**\n"
                "- Sorunu konu ve durum olarak açık yaz (örnek: *«kredi kartıyla taksitli alışveriş, gecikme "
                "faizi işlemeden caiz mi?»*) — o zaman ilgili kaydı daha isabetli bulabilirim.\n"
                "- Benzer başlıklardaki cevapların içinde yer alan **genel ölçüler** çoğu zaman bu soruya da "
                "uygulanır.\n"
                "- Kişisel ve hukukî sonuç doğuran meselelerde **İl/İlçe Müftülüğü'ne** danış. Bu araç fetva "
                "mercii değildir."
            ),
        },
        {
            "ad": "hikmet",
            "re": r"(neden (haram|yasak|farz|gunah|boyle|oluyor)|hikmeti nedir|hikmeti ne|neden yapilir|"
                  r"neden var|ne anlami var|manasi ne|neden boyle|ne faydasi|ne ise yarar)",
            "cevap": (
                "Bu konunun hikmetini özel olarak bilgi bankamda bulamadım; ama genel çerçeveyi paylaşayım:\n\n"
                "**1. Her hükümde hikmet aranır, ama hüküm hikmete bağlı değildir.** Bir emir/yasak, görünen "
                "faydası bulunamadı diye düşmez: «O, kendi hevesinden konuşmaz; o ancak vahyedilen bir "
                "vahiydir.» (Necm 53/3-4)\n"
                "**2. Hükümlerin çoğunun hikmeti açıktır:** koruma (can, mal, nesil, akıl, din), adalet, "
                "kolaylık, temizlik, toplumsal huzur. «Allah size kolaylık ister, zorluk istemez.» (Bakara 2/185)\n"
                "**3. Bazı hükümlerin hikmeti tam bilinmeyebilir** — bu, teslimiyetin sınavıdır: «İşitiriz ve "
                "itaat ederiz.» (Bakara 2/285)\n"
                "**4. Hikmet ile illet (gerekçe) karıştırılmamalıdır:** âlim illeti bulunca hüküm değişmez; "
                "illet, **kıyas** yapmak için kullanılır.\n\n"
                "Sorunu biraz açarsan (örnek: *«içki neden kademeli yasaklandı?»*, *«faizin hikmeti nedir?»*) "
                "hangisini kastettiğini anlayıp en yakın kaydı getirebilirim. Daha derin tefsir/fıkıh "
                "çalışması için ehlinden ders almak en güzelidir."
            ),
        },
        {
            "ad": "nasil",
            "re": r"(nasil (yapilir|olur|kilarim|kilinir|baslarim|baslanir|ederim|edilir|ogrenirim|yaparim)|"
                  r"adim adim|ogrenmek istiyorum|bilmiyorum nasil|nasil yapmam)",
            "cevap": (
                "Bu konunun adımlarını bilgi bankamda bulamadım; ama genel yöntem şudur ve çoğu ibadet "
                "için geçerlidir:\n\n"
                "**1. Önce çerçeveyi öğren:** Bu ibadet *farz mı, vacip mi, sünnet mi?* Zamanı ve şartları "
                "neler? Bir ilmihalin ilgili bölümü yeterlidir.\n"
                "**2. Küçükten başla:** Tamamını bir günde öğrenmeye çalışma. Örnek: namaz → önce abdest, "
                "sonra 2 rekâtlık bir namaz, sonra diğer vakitler.\n"
                "**3. Taklit, öğrenmeyi hızlandırır:** Bir hocayla/cami cemaatiyle yan yana kılmak, "
                "kitaptan okumaktan çok daha hızlı öğretir.\n"
                "**4. Hata senden, kabul Allah'tandır:** «Amellerin en hayırlısı, az da olsa devamlı olanıdır.» "
                "(Buhârî, Müslim) Öğrenirken yapılan hatalar seni yoldan çıkarmasın.\n"
                "**5. Vesveseye kapılma:** Şüphelerle ameli bırakmak, şeytanın en sevdiği tuzaktır.\n\n"
                "Hangi ibadet/konu için sorduğunu tam yaz (örnek: *«vitir namazı nasıl kılınır»*, *«adak nasıl "
                "yerine getirilir»*) — ilgili kaydı bulup adım adım anlatayım."
            ),
        },
    ]

    def _ilke_yaniti(self, q_norm: str, q_base: List[str]) -> Optional[Dict[str, Any]]:
        # Çok kısa/çok genel sorularda ilke cevabı verme (onlar konu listesine gitsin)
        if len(q_base) < 2:
            return None
        for ilke in self.ILKELER:
            if re.search(ilke["re"], q_norm):
                return {
                    "bulundu": False,
                    "tip": "ilke",
                    "guven": 0.35,
                    "kategori": "Genel Usul",
                    "soru": "Genel çerçeve",
                    "cevap": ilke["cevap"],
                    "kaynaklar": ["Kur'an: el-Bakara 2/29, 173, 185; en-Nahl 16/43",
                                  "Hadis: Buhârî, İman 39; Müslim, Müsâkât 107"],
                    "ilgili": [], "notlar": [],
                }
        return None

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
            self._bosluk_kaydet(question, [])
            ilke = self._ilke_yaniti(q_norm, q_base)
            if ilke:
                ilke["pasajlar"] = [
                    {"id": pz["kayit"].id, "kategori": pz["kayit"].kategori,
                     "soru": pz["kayit"].soru, "metin": pz["metin"], "puan": pz["puan"]}
                    for pz in self.ilgili_pasajlar(q_weighted, limit=3, esik=1.2)
                ]
                return ilke
            return self._belirsiz(question, self._fuzzy_candidates(q_norm), q_weighted)

        best_score, best = scores[0]

        # Güven dönüşümü (0-1)
        guven = best_score / (best_score + 5.5) if best_score > 0 else 0.0

        if best_score < 1.6:
            overview = self._category_overview(q_base, q_norm)
            if overview:
                return overview
            self._bosluk_kaydet(question, [(s, e) for s, e in scores[:4]])
            ilke = self._ilke_yaniti(q_norm, q_base)
            if ilke:
                ilke["pasajlar"] = [
                    {"id": pz["kayit"].id, "kategori": pz["kayit"].kategori,
                     "soru": pz["kayit"].soru, "metin": pz["metin"], "puan": pz["puan"]}
                    for pz in self.ilgili_pasajlar(q_weighted, limit=3, esik=1.2)
                ]
                ilke["ilgili"] = self._ilgili_sozluk([e for _, e in scores[:4]])
                return ilke
            return self._belirsiz(question, [e for _, e in scores[:4]], q_weighted)

        if len(q_base) <= 1:
            overview = self._category_overview(q_base, q_norm)
            if overview:
                return overview

        related = [e for _, e in scores[1:top_k + 1] if _ > best_score * 0.35] or self._same_category(best)

        # Kullanıcı, en iyi kaydın kapsamadığı ek ayrıntılar sorduysa: cevap metinlerinden
        # paragraf düzeyinde ek bilgi getir (kapsamı genişletir).
        q_set = {t for t, _ in q_weighted}
        kapsanan = set(best.field_tokens["soru"]) | set(best.field_tokens["anahtar"]) | set(best.field_tokens["kategori"])
        eksik = [t for t, _ in q_weighted if t not in kapsanan and t not in LOW_SIGNAL]
        pasajlar: List[Dict[str, Any]] = []
        if len(eksik) >= 2 or (q_set and 1 - len(eksik) / len(q_set) < 0.6):
            pasajlar = self.ilgili_pasajlar(q_weighted, haric={best.id}, limit=3)

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
            "pasajlar": [
                {
                    "id": pz["kayit"].id,
                    "kategori": pz["kayit"].kategori,
                    "soru": pz["kayit"].soru,
                    "metin": pz["metin"],
                    "puan": pz["puan"],
                }
                for pz in pasajlar
            ],
            "notlar": notlar,
        }

    @staticmethod
    def _ilgili_sozluk(entries: List[Entry]) -> List[Dict[str, str]]:
        return [{"id": e.id, "soru": e.soru, "kategori": e.kategori} for e in entries]

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

    def _belirsiz(self, question: str, candidates: Optional[List[Entry]] = None,
                  q_weighted: Optional[List[Tuple[str, float]]] = None) -> Dict[str, Any]:
        if not candidates:
            candidates = self._fuzzy_candidates(normalize(question))
        ilgili: List[Any] = candidates or self._popular(5)
        if ilgili and isinstance(ilgili[0], dict):
            ilgili = [self.by_id(x["id"]) or x for x in ilgili]
        ilgili = [e for e in ilgili if isinstance(e, Entry)]
        pasajlar = self.ilgili_pasajlar(q_weighted or [], haric={e.id for e in ilgili[:1]},
                                        limit=3, esik=1.3)
        if pasajlar:
            ek = (
                "Yine de bilgi bankamda sorunuza **en yakın bölümleri** aşağıda kaynağıyla paylaşıyorum; "
                "bunlar sorunuzun bir kısmına cevap verebilir."
            )
        else:
            ek = (
                "Sorunuzu şu şekilde yeniden yazarsanız çok daha isabetli cevap verebilirim:\n\n"
                "- Konu adını söyleyin: *\"zekât\"*, *\"abdest\"*, *\"cuma namazı\"*\n"
                "- Ne öğrenmek istediğinizi belirtin: *\"... nasıl yapılır?\"*, *\"... caiz mi?\"*, "
                "*\"... kaç rekât?\"*\n\n"
                "**Örnek:** *\"Namaz kılmıyorum, yeniden nasıl başlarım?\"*"
            )
        metin = (
            "Bilgi bankamda bu sorunun **tam karşılığını** bulamadım. " + ek + "\n\n"
            "Ayrıca sorunuzu *geliştirme listesine* kaydettim; ileride bu konu da eklenecek. 🤲"
        )
        return {
            "bulundu": False,
            "tip": "belirsiz",
            "guven": 0.0,
            "kategori": "Genel",
            "soru": question.strip()[:120],
            "cevap": metin,
            "kaynaklar": [],
            "ilgili": self._ilgili_sozluk(ilgili[:5]),
            "pasajlar": [
                {"id": pz["kayit"].id, "kategori": pz["kayit"].kategori, "soru": pz["kayit"].soru,
                 "metin": pz["metin"], "puan": pz["puan"]} for pz in pasajlar
            ],
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

    # ---- geliştirme listesi: cevaplanamayan sorular --------------------------------
    BOSLUK_DOSYA = Path(__file__).parent / "runtime" / "bosluklar.json"

    def _bosluk_kaydet(self, soru: str, adaylar: List[Tuple[float, Entry]]) -> None:
        """Cevaplanamayan soruları (tekrar sayısıyla) kaydeder — içerik büyütme listesi."""
        try:
            self.BOSLUK_DOSYA.parent.mkdir(parents=True, exist_ok=True)
            veri: Dict[str, Any] = {}
            if self.BOSLUK_DOSYA.exists():
                veri = json.loads(self.BOSLUK_DOSYA.read_text(encoding="utf-8"))
            anahtar = normalize(soru)[:120]
            kayit = veri.get(anahtar, {"soru": soru.strip()[:200], "adet": 0, "ilk": None,
                                       "en_yakin": [e.soru for _, e in adaylar[:3]]})
            kayit["adet"] = int(kayit.get("adet", 0)) + 1
            kayit["son"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            kayit.setdefault("ilk", kayit["son"])
            veri[anahtar] = kayit
            self.BOSLUK_DOSYA.write_text(
                json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass  # kayıt tutulamazsa cevaplama akışı bozulmasın

    def bosluklar(self) -> List[Dict[str, Any]]:
        try:
            if not self.BOSLUK_DOSYA.exists():
                return []
            veri = json.loads(self.BOSLUK_DOSYA.read_text(encoding="utf-8"))
            kayitlar = list(veri.values())
            kayitlar.sort(key=lambda k: -int(k.get("adet", 0)))
            return kayitlar
        except Exception:
            return []

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
            "motor": "Yerel bilgi bankası (BM25 + ifade eşleştirme + paragraf arama)",
            "internet_gerekli": False,
            "pasaj_sayisi": len(self.passages),
            "bosluk_sayisi": len(self.bosluklar()),
        }


# Tekil motor örneği
engine = Engine()
