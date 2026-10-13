# 🕌 ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı

**İslami sorularınızı ücretsiz ve sınırsız sorabileceğiniz bir soru-cevap danışmanı.**

> Namaz, abdest, gusül, oruç, zekât, hac, dua, iman esasları, aile, helâl-haram, ahlâk,
> günlük hayat… Aklınıza gelen her İslami soruyu doğal bir dille yazın; cevabı kaynaklarıyla alın.

---

## ✨ Neden "ücretsiz ve sınırsız"?

| Özellik | Durum |
|---|---|
| 💸 Ücret / abonelik | **Yok** |
| 🔑 API anahtarı / hesap açma | **Gerekmez** |
| 📊 Soru limiti / kota | **Yok** |
| 🌐 İnternet bağlantısı | **Gerekmez** (bilgi bankası tamamen yerel) |
| 🕵️ Veri toplama / kayıt | **Yok** — sohbetler yalnızca tarayıcınızda saklanır |
| 🧠 Harici yapay zekâ servisi | **Kullanılmaz** |

Uygulama; yapay zekâ API'si çağırmaz. Cevaplar, **Kur'an âyetleri, sahih hadisler ve klasik fıkıh
kaynaklarına dayanılarak hazırlanmış yerel bir bilgi bankasından** gelir ve her cevabın altında
kaynakları listelenir. Yani: aynı soruya her zaman aynı, denetlenebilir cevap; ağ kesintisinde bile
çalışır, sıfır maliyetle istediğiniz kadar soru.

---

## 🚀 Hızlı Başlangıç

```bash
# 1) Bağımlılıklar (yalnızca FastAPI + Uvicorn)
pip install -r requirements.txt

# 2) Çalıştır
python -m app.main
# veya
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3) Tarayıcıda aç
http://localhost:8000
```

Port değiştirmek için: `PORT=9000 python -m app.main`

---

## 🧩 Neler Yapabilir?

- **90+ soru-cevap kaydı**, 13 konu başlığı: İnanç, Taharet, Namaz, Oruç, Zekât, Hac, Aile,
  Helâl-Haram, Ahlâk, Dua, Kur'an, Günlük Hayat, Genel
- **Doğal dil ile arama:** *"adetliyken namaz kılınır mı"*, *"faizli kredi caiz mi"*,
  *"namaz kılmıyorum nasıl başlarım"* gibi sorular anlaşılır
- **Yazım hatası toleransı** ve Türkçe ek/çekim farklılıklarına dayanıklı arama
- **Kaynak gösterimi:** her cevapta âyet/hadis/fıkıh referansları
- **İlgili sorular:** cevabın altında konuya yakın diğer başlıklar
- **İhtilaf farkındalığı:** fıkhî tartışmalı konularda "ihtilaf var, müftülüğe danışın" uyarısı
- **Acil durum desteği:** şiddet, istismar ve kendine zarar verme durumlarında öncelikli güvenlik
  yanıtı ve resmî destek hatları (**112**, **183**)
- **Konu gezintisi:** kenar çubuğundan konu seçip soru listesini görme, rastgele soru
- **Kısa / Ayrıntılı** cevap modu, kopyalama, sohbeti temizleme, mobil uyumlu arayüz
- **Hicrî tarih** gösterimi ve zümrüt-altın islamik tasarım

---

## 🔌 API

| Yöntem | Adres | Açıklama |
|---|---|---|
| `POST` | `/api/sor` | Soru sorar. Gövde: `{"soru": "...", "detay": "normal"\|"kisa"}` |
| `GET`  | `/api/kategoriler` | Konu başlıkları ve kayıt sayıları |
| `GET`  | `/api/sorular?kategori=Namaz` | Soru listesi (isteğe bağlı konu filtresi) |
| `GET`  | `/api/soru/{id}` | Belirli bir kaydın tam cevabı |
| `GET`  | `/api/rastgele` | Rastgele soru-cevap |
| `GET`  | `/api/istatistik` | Kayıt sayısı, motor bilgisi, ücret/limit bilgisi |
| `GET`  | `/api/saglik` | Servis durumu |
| `GET`  | `/docs` | Otomatik API dokümantasyonu (Swagger) |

Örnek:

```bash
curl -X POST http://localhost:8000/api/sor \
  -H 'Content-Type: application/json' \
  -d '{"soru":"Zekât kimlere verilir?"}'
```

```json
{
  "bulundu": true,
  "tip": "cevap",
  "guven": 0.93,
  "kategori": "Zekât",
  "soru": "Zekât kimlere verilir, kimlere verilmez?",
  "cevap": "Kur'an-ı Kerim zekâtın verileceği sekiz sınıfı açıkça sayar: ...",
  "kaynaklar": ["Kur'an: et-Tevbe 9/60", "Hadis: Buhârî, Zekât 1-3; Müslim, Zekât 79-99"],
  "ilgili": [{"id": "zekat-farz-nisap", "soru": "Zekât kimlere farzdır, nisap miktarı nedir?", "kategori": "Zekât"}],
  "notlar": ["Bu konu içtihat/ihtilaf içerir. Kişisel durumunuz için İl/İlçe Müftülüğü'ne danışmanız en doğrusudur.", "..."]
}
```

---

## 🗂 Proje Yapısı

```
.
├── app/
│   ├── main.py              # FastAPI uygulaması ve API uç noktaları
│   ├── engine.py            # Arama/cevaplama motoru (BM25 + ifade eşleştirme)
│   ├── data/                # Bilgi bankası (JSON) — yeni soru eklemek için buraya
│   │   ├── qa_itikad.json         # İnanç
│   │   ├── qa_taharet.json        # Abdest, gusül, teyemmüm, necaset, hayız
│   │   ├── qa_namaz.json          # Namaz, cuma, seferi, kaza, cenaze, bayram
│   │   ├── qa_oruc_zekat.json     # Oruç, itikâf, zekât, fitre, sadaka
│   │   ├── qa_hac.json            # Hac, umre, ihram, kurban
│   │   ├── qa_ahlak.json          # Gıybet, yalan, öfke, sabır, iş ahlakı
│   │   ├── qa_aile.json           # Nikâh, boşanma, eş-çocuk hakları, helâl-haram
│   │   ├── qa_genel.json          # Dua, Kur'an, günlük hayat, ilmihal
│   │   └── qa_modern.json         # Tesettür, müzik, sigara, dijital hayat, kripto, teknoloji
│   └── static/              # Arayüz (index.html, style.css, app.js, favicon.svg)
├── tests/test_smoke.py      # Duman testleri
└── requirements.txt
```

---

## 🧪 Testler

```bash
python tests/test_smoke.py
# veya
pytest -q
```

Testler; veri bütünlüğünü, her kaydın kendi anahtar kelimeleriyle bulunabilmesini,
70+ örnek sorunun **doğru kayda** yönlenmesini, güvenlik yanıtlarını ve "ücretsiz/sınırsız"
sözleşmesini doğrular.

---

## ➕ Yeni Soru Nasıl Eklenir?

`app/data/` altındaki JSON dosyalarına aşağıdaki biçimde kayıt ekleyin (uygulamayı yeniden başlatın):

```json
{
  "id": "benzersiz-kisa-id",
  "kategori": "Namaz",
  "soru": "Sorunun başlığı?",
  "anahtar": ["kullanıcıların yazabileceği ifadeler", "eş anlamlılar", "varyantlar"],
  "cevap": "Cevap metni. **Kalın**, madde listeleri ve | tablolar | desteklenir.",
  "kaynaklar": ["Kur'an: ...", "Hadis: ..."]
}
```

> İpucu: `anahtar` alanına, insanların soruyu sorarken kullanacağı **doğal ifadeleri** yazmak,
> cevap isabetini en çok artıran şeydir.

---

## ⚠️ Önemli Uyarı

Bu uygulama bir **fetva mercii değildir**; bir bilgilendirme ve öğrenme aracıdır.
Cevaplar genel bilgilendirme içindir ve kişisel durumlar için bağlayıcı hüküm yerine geçmez.
Kişisel, hassas ve hukukî sonuç doğuran konularda **İl/İlçe Müftülüğü'ne** veya ehline danışınız.

**Acil durumlarda:** Şiddet, istismar veya kendine zarar verme düşüncesi varsa lütfen
**112 Acil**'i veya **183 Sosyal Destek Hattı**'nı arayın. Bir uzmandan yardım almak dinen de
tavsiye edilen bir tedbirdir.

---

## 🤲 Küçük Bir Not

> «Rabbiniz buyurdu: Bana dua edin, size cevap vereyim.» — *Gâfir 40/60*

Bu proje, ilim öğrenmeyi kolaylaştırmak niyetiyle hazırlanmıştır. Hatalar bizden, doğrular
Allah'tandır. Gördüğünüz eksik veya yanlışı düzeltmekten çekinmeyin: bilgi bankası büyüdükçe
uygulama güzelleşir.
