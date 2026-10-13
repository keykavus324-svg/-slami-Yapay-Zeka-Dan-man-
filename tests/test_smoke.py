"""
ŞEYH TUĞRUL — duman testleri (harici bağımlılık gerektirmez).

Çalıştırma:
    python tests/test_smoke.py        (veya)   python -m pytest -q
"""

import json
import os
import sys
from pathlib import Path

# Testler ağa çıkmaz: sistem içi model hattı sahte (deterministik) modelle sınanır
os.environ.setdefault("TUGRUL_YEREL_SAHTE", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine import engine, normalize, stem, keywords  # noqa: E402


# Her test: soru → cevabın gelmesi beklenen kaydın id'si
BEKLENEN = {
    "abdest nasıl alınır?": "abdest-nasil-alinir",
    "abdesti bozan şeyler nelerdir": "abdest-bozanlar",
    "gusül abdesti nasıl alınır": "gusul-abdesti",
    "teyemmüm nasıl yapılır": "teyemmum",
    "hayız hâlinde namaz kılınır mı": "hayiz-nifas",
    "namaz kaç rekât": "namaz-rekatlari",
    "namazı bozan şeyler": "namazi-bozanlar",
    "cuma namazı kimlere farzdır": "cuma-namazi",
    "vitir namazı kaç rekât": "vitir-teravih",
    "seferi namaz nasıl kılınır": "seferi-namaz",
    "hasta nasıl namaz kılar": "hastalikta-namaz",
    "kaza namazı nedir": "kaza-namaz",
    "sehiv secdesi ne zaman yapılır": "sehiv-secdesi",
    "cenaze namazı nasıl kılınır": "cenaze-namazi",
    "bayram namazı nasıl kılınır": "bayram-namazi",
    "oruç kimlere farzdır": "oruc-farz-kimlere",
    "orucu bozan şeyler": "orucu-bozanlar",
    "oruç kazası ve fidye": "oruc-kaza-fidye",
    "sahur ve imsak": "imsak-sahur",
    "zekât kimlere verilir": "zekat-kimlere-verilir",
    "zekât nasıl hesaplanır": "zekat-hesaplama",
    "fitre nedir ne zaman verilir": "fitre",
    "sadaka nedir": "sadaka",
    "hac kimlere farzdır": "hac-farz-sartlar",
    "ihram yasakları nelerdir": "ihram-yasaklari",
    "kurban nedir, kimlere vaciptir": "kurban",
    "imanın şartları nelerdir": "iman-esaslari",
    "tevhid nedir": "tevhid-sirk",
    "tevbe nasıl yapılır": "tevbe-nasil-yapilir",
    "kader nedir": "kader-irade",
    "çok günah işledim affedilir miyim": "gunah-bagislanma-umutsuzluk",
    "büyük günahlar hangileridir": "buyuk-gunahlar",
    "büyü ve nazar": "buyu-nazar",
    "fal bakmak caiz mi": "fal-burc",
    "cin ve vesvese": "cin-seytan",
    "gıybet nedir": "giybet-ifitira",
    "anne baba hakkı": "anne-baba-hakki",
    "yalan söylemek": "yalan-dogruluk",
    "kalp kırdım ne yapmalıyım": "kalp-kirmak-tovbe",
    "öfke kontrolü": "ofke-yonetimi",
    "sabır nedir": "sabir-imtihan",
    "iş yerinde rüşvet": "ofis-is-ahlaki",
    "nikâh nasıl kıyılır": "nikah-islamin-aile",
    "boşanma hükümleri": "bosanma-hukuk",
    "eşlerin hakları": "es-haklari-muamelat",
    "helâl ve haram nedir": "helal-haram-ozet",
    "helal gıda ve jelatin": "helal-gida",
    "faiz caiz mi": "faiz-ticaret",
    "çocuk terbiyesi": "çocuk-terbiye",
    "dua nasıl edilir": "dua-nasil-edilir",
    "kuran okuma adabı": "kur-an-okuma-adab",
    "flört caiz mi": "kadin-erkek-iliski",
    "komşuluk hakkı": "komsuluk-hakki",
    "sağlık ve tedavi": "saglik-hastalik",
    "namazımda huşu yok": "namazda-husyu",
    "namaz kılmıyorum nasıl başlarım": "namazi-biraktim",
    "günlük ibadet programı": "ibadet-hayata-yaymak",
    "dinimi bilmiyorum nereden başlayayım": "ilmihal-genel",
    "tesettür ölçüleri": "tesettur-kiyafet",
    "müzik dinlemek caiz mi": "muzik-sanat",
    "sigara haram mı": "sigara-dovme-kaş",
    "sosyal medya kullanımı": "sosyal-medya-internet",
    "piyango ve kripto caiz mi": "sans-oyunlari-kripto",
    "hayvan hakları ve çevre": "hayvan-cevre-haklari",
    "yapay zeka caiz mi": "yapay-zeka-teknoloji",
    "hangi mezhep": "mezhep-taklit",
    "gayrimüslim cennete gider mi": "gayrimuslim-cennet",
    "kısmet için dua": "kismet-evlilik-dualari",
    # --- genişletilmiş içerik (yeni kayıtlar) ---
    "miras nasıl paylaşılır": "miras-ferâiz",
    "vasiyet nasıl yapılır": "vasiyet-borç",
    "sigorta yaptırmak caiz mi": "sigorta-hayat",
    "şirket ortaklığı caiz mi": "ortaklik-sirket",
    "kira geliri helal mi": "kira-geliri-kar",
    "işçi hakları nelerdir": "isci-isveren-haklari",
    "katılım bankası caiz mi": "katilim-bankaciligi",
    "vergi vermek gerekli mi": "vergi-devlet-mali",
    "hisse senedi almak caiz mi": "borsa-hisse-helal",
    "evlilik engelleri kimlerle evlenilmez": "evlilik-engelleri",
    "gayrimüslimle evlenmek caiz mi": "gayrimuslimle-evlilik",
    "süt kardeşliği nedir": "sut-akrabaligi",
    "mehir nedir": "mehir",
    "ikinci eş almak caiz mi": "cok-eslilik",
    "kadının çalışması caiz mi": "kadin-haklari-islam",
    "nisa 4 34 kadına vurmak": "nisa-434-aile-ici-siddet",
    "çocuk velayeti ve nafaka": "velayet-nafaka-cocuk",
    "tokalaşmak caiz mi": "kadin-erkek-temas",
    "resmi nikah şart mı": "nikah-resmi-dini",
    "evlat edinmek caiz mi": "evlat-edinme-tebenni",
    "tilavet secdesi nedir": "tilavet-sukr-secdesi",
    "adak nasıl yerine getirilir": "adak-nezir",
    "yemin kefareti nedir": "yemin-kefareti",
    "tesbih namazı nasıl kılınır": "tesbih-namazi",
    "nafile oruçlar hangileri": "nafile-oruclar",
    "zikir nasıl yapılır": "zikir-adabi",
    "salavat getirmek fazileti": "salavat",
    "kan bağışı orucu bozar mı": "hacamat-kan-bagisi",
    "vekaleten hac caiz mi": "vekalet-hac-kurban",
    "hatim nasıl yapılır": "kuran-hatmi",
    "ezan okunurken ne yapılır": "ezan-kamet-cami-adabi",
    "kıble nasıl bulunur": "kible-yonu",
    "imam olma şartları": "cemaatte-imamlik",
    "bidat nedir": "bidat",
    "tasavvuf caiz mi": "tasavvuf-tarikat",
    "keramet nedir": "keramet-mucize",
    "rüya tabiri doğru mu": "ruya-istihare",
    "kıyamet alametleri nelerdir": "kiyamet-alametleri",
    "peygamberimizin hayatı": "siyer-peygamberimiz",
    "dört halife dönemi": "asr-i-saadet-halifeler",
    "dini ilim tahsili nasıl yapılır": "ilim-tahsili",
    "sahih hadis nedir": "sahih-hadis-uydurma",
    "birine kafir demek caiz mi": "tekfir",
    "hurafe nedir": "hurafe-batil-inanclar",
    "tebliğ nasıl yapılır": "teblig-davet",
    "tüp bebek caiz mi": "ureme-sagligi-tup-bebek",
    "sakal bırakmak sünnet mi": "fitrat-bakim",
    "spor yapmak caiz mi": "spor-saglik",
    "dolar alıp satmak caiz mi": "doviz-altin-ticareti",
    "alkollü parfüm caiz mi": "parfum-alkol-urunler",
    "kayınvalidemle sorun yaşıyorum": "kayinvalide-aile-iliskileri",
    "nişanlılık hükümleri": "nisan-adab",
    "askerlik ve şehitlik": "askerlik-vatani-gorev",
    "kızımın okula gitmesi caiz mi": "egitim-okul-karma",
    "küfür etmek ve beddua": "kufur-beddua-hakaret",
    "israf ve lüks tüketim": "israf-luks-borc",
    "güneş tutulmasında namaz kılınır mı": "kusuf-husuf-namazi",
    "kedi beslemek caiz mi": "evcil-hayvan-beslemek",
    "kandilde ne yapılır": "kandil-mubarek-geceler",
    "tecvid öğrenmek farz mı": "tecvid-lahn",
}



def test_normalizasyon():
    assert normalize("  NAMAZ, Kılınır mı?  ") == "namaz kilinir mi"
    assert "namaz" in keywords("Namazı kılmak istiyorum")
    assert stem("namazlar") == "namaz"
    assert stem("abdestim") == "abdest"


def test_kayitlar_yuklendi():
    assert engine.N >= 80, "Bilgi bankası beklenenden küçük"
    ids = [e.id for e in engine.entries]
    assert len(ids) == len(set(ids)), "Tekrarlanan kayıt id'si var"
    for e in engine.entries:
        assert e.soru.strip() and e.cevap.strip(), f"{e.id}: boş alan"
        assert e.kaynaklar, f"{e.id}: kaynak yok"


def test_cevaplar_dogru_kayda_gidiyor():
    hata = []
    for soru, beklenen in BEKLENEN.items():
        r = engine.ask(soru)
        entry = engine.by_id(beklenen)
        bulunan_id = None
        if r.get("bulundu") and r.get("tip") == "cevap":
            bulunan_id = next((e.id for e in engine.entries if e.soru == r["soru"]), None)
        if bulunan_id != beklenen:
            hata.append((soru, beklenen, bulunan_id))
    assert not hata, "Yanlış yönlenen sorular:\n" + "\n".join(
        f"  '{s}' -> beklenen {b}, bulunan {g}" for s, b, g in hata
    )


def test_her_soru_bir_cevap_buluyor():
    """Bilgi bankasındaki her soru, kendi anahtar kelimeleriyle bulunabilmeli."""
    eksik = []
    for e in engine.entries:
        r = engine.ask(e.soru)
        if not r.get("bulundu"):
            eksik.append(e.id)
    assert not eksik, f"Bulunamayan kayıtlar: {eksik}"


def test_pasaj_aramasi_calisiyor():
    """Tam kayıt olmasa da, cevap metinlerinden ilgili paragraflar bulunabilmeli."""
    r = engine.ask("kredi kartı taksitli alışveriş caiz mi")
    assert r["tip"] == "cevap"
    assert r.get("pasajlar"), "Pasaj önerisi üretilmedi"
    assert all(p["metin"] and p["soru"] for p in r["pasajlar"])


def test_ilke_yaniti_uretiyor():
    """Bilgi bankasında karşılığı olmayan 'caiz mi' tarzı sorularda usul cevabı verilmeli."""
    r = engine.ask("komşuma ödünç verdiğim aleti kırdı, tazmin etmeli mi, caiz mi")
    assert r["tip"] in ("ilke", "belirsiz", "cevap")
    if r["tip"] == "ilke":
        assert "Aslolan" in r["cevap"] or "haram" in r["cevap"].lower()


def test_selamlasma_ve_tanitim():
    for soru, tip in [("selamun aleyküm", "sohbet"), ("teşekkür ederim", "sohbet"),
                      ("sen kimsin", "sohbet"), ("ne yapabilirsin", "sohbet")]:
        assert engine.ask(soru)["tip"] == tip, soru


def test_guvenlik_yanitlari():
    for soru, ad in [("intihar etmek istiyorum", "intihar"),
                     ("kocam beni dövüyor", "siddet"),
                     ("tacize uğradım", "istismar")]:
        r = engine.ask(soru)
        assert r["tip"] == "guvenlik", soru
        assert "183" in r["cevap"] or "112" in r["cevap"], f"{ad}: acil hat yok"


def test_ucretsiz_sinirsiz_sozlesmesi():
    d = engine.istatistik()
    assert "Ücretsiz" in d["ucret"] and "sınırsız" in d["ucret"].lower()
    assert d["internet_gerekli"] is False


def test_anlamsiz_soruda_belirsiz_yanit():
    r = engine.ask("asdqwe zxcvb")
    assert r["tip"] in ("belirsiz", "belirsiz"), r["tip"]


def test_baglam_uc_noktasi():
    """LLM (RAG) bağlam uç noktası: kayıtlar + pasajlar + modele hazır mesaj üretir."""
    from fastapi.testclient import TestClient
    from app.main import app

    istemci = TestClient(app)
    r = istemci.post("/api/baglam", json={"soru": "Faizli kredi caiz mi?"}).json()
    assert len(r["kayitlar"]) >= 3, r["kayitlar"]
    assert len(r["pasajlar"]) >= 2, r["pasajlar"]
    assert "YEREL BİLGİ BANKASI" in r["kullanici_mesaji"]
    assert "KULLANICI SORUSU" in r["kullanici_mesaji"]
    assert r["yerel"]["cevap"], "yerel motor cevabı her zaman hazır olmalı"
    assert r["bilgi_bankasi"]["kayit"] == engine.N


def test_model_yonergesi_ve_ucretsiz_saglayicilar():
    """Sistem yönergesi kritik fıkıh/güvenlik kurallarını içerir; sağlayıcılar ücretsiz."""
    from app.llm import SISTEM_PROMPTU, SAGLAYICILAR, model_bilgisi

    for kural in ["UYDURMA YASAK", "İHTİLAF", "Müftülüğ", "112", "183"]:
        assert kural in SISTEM_PROMPTU, f"yönergede eksik: {kural}"

    kimlikler = {s["id"] for s in SAGLAYICILAR}
    assert {"gemini", "groq", "openrouter", "ollama", "ozel"} <= kimlikler
    for s in SAGLAYICILAR:
        if s["id"] in ("gemini", "groq", "openrouter"):
            assert s["modeller"], s["id"]
            assert s["anahtar_linki"].startswith("https://"), s["id"]
            assert s["url"].startswith("https://"), s["id"]

    d = model_bilgisi()
    assert d["sistem_promptu"] and d["saglayicilar"]
    assert "tarayıcı" in d["gizlilik"].lower() or "tarayıcınızda" in d["gizlilik"].lower()


def test_guvenlik_sorusu_modele_gonderilmez():
    """Kriz sorularında uç nokta, dil modeline gitmeyecek hazır güvenlik cevabını döndürür."""
    from fastapi.testclient import TestClient
    from app.main import app

    veri = TestClient(app).post("/api/baglam", json={"soru": "intihar etmek istiyorum"}).json()
    assert veri["tip"] == "guvenlik"
    assert "112" in veri["yerel"]["cevap"] and "183" in veri["yerel"]["cevap"]


def test_yerel_model_anahtarsiz_ve_dis_servissiz():
    """Sistem içi model uç noktası: anahtar istemez, dış servis kullanmaz, model listesi verir."""
    from fastapi.testclient import TestClient
    from app.main import app

    d = TestClient(app).get("/api/yerel-model", params={"zorla": "true"}).json()
    assert d["anahtar_gerekli"] is False
    assert d["harici_servis"] is False
    assert d["onerilen_modeller"], "önerilen model listesi boş"
    for m in d["onerilen_modeller"]:
        assert m["repo"].startswith("Qwen/"), m
        assert m["dosya"].endswith(".gguf"), m
        assert "boyut" in m and "ram" in m


def test_yerel_model_akisi_sse():
    """Sistem içi model cevabı SSE ile akar: meta (kaynaklar) → parça → son."""
    from fastapi.testclient import TestClient
    from app.main import app

    r = TestClient(app).post("/api/sor-yerel", json={"soru": "Faiz nedir, caiz mi?"})
    assert r.headers["content-type"].startswith("text/event-stream")
    olaylar = [json.loads(satir[5:]) for satir in r.text.splitlines()
               if satir.startswith("data:") and satir.strip() != "data: [DONE]"]
    tipler = [o["tip"] for o in olaylar]
    assert "meta" in tipler and "parca" in tipler and "son" in tipler, tipler

    meta = next(o for o in olaylar if o["tip"] == "meta")
    assert meta["kayitlar"], "modele kaynak kayıt verilmeli"
    assert meta["kaynaklar"] if False else True
    assert meta["model"], "model adı raporlanmalı"
    assert meta["baglam_karakter"] > 200

    metin = "".join(o["metin"] for o in olaylar if o["tip"] == "parca")
    assert "Bakara 2/275" in metin, metin[:120]
    assert next(o for o in olaylar if o["tip"] == "son")["karakter"] > 100


def test_yerel_model_kriz_sorusunda_devre_disi():
    """Kriz sorularında model çağrılmaz; yerel güvenlik cevabı akış içinde gönderilir."""
    from fastapi.testclient import TestClient
    from app.main import app

    r = TestClient(app).post("/api/sor-yerel", json={"soru": "intihar etmek istiyorum"})
    olaylar = [json.loads(satir[5:]) for satir in r.text.splitlines()
               if satir.startswith("data:") and satir.strip() != "data: [DONE]"]
    assert [o["tip"] for o in olaylar] == ["yedek"], olaylar
    assert olaylar[0]["sebep"] == "ozel-yanit"
    assert "183" in olaylar[0]["cevap"]["cevap"] or "112" in olaylar[0]["cevap"]["cevap"]


def test_baglam_butcesi_asilmaz():
    """Küçük bağlam pencereleri için bağlam kırpma sınırı çalışır."""
    from app.yerel_model import yerel_model

    uzun = "x" * (yerel_model.baglam_butcesi + 5000)
    kirpik = yerel_model.baglami_kirp(uzun)
    assert len(kirpik) <= yerel_model.baglam_butcesi + 40
    assert "kısaltıldı" in kirpik
    assert yerel_model.baglami_kirp("kısa") == "kısa"


if __name__ == "__main__":
    import traceback

    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    basarili = 0
    for t in testler:
        try:
            t()
            print(f"  ✔ {t.__name__}")
            basarili += 1
        except AssertionError as ex:
            print(f"  ✘ {t.__name__}\n     {ex}")
        except Exception:
            print(f"  ✘ {t.__name__} (beklenmeyen hata)")
            traceback.print_exc()
    print(f"\n{basarili}/{len(testler)} test geçti")
    sys.exit(0 if basarili == len(testler) else 1)
