"""
ŞEYH TUĞRUL — duman testleri (harici bağımlılık gerektirmez).

Çalıştırma:
    python tests/test_smoke.py        (veya)   python -m pytest -q
"""

import sys
from pathlib import Path

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
    "komşuluk hakkı": "temizlik-gunluk",
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
