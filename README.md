# 🕌 ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı

**İslami sorularınızı ücretsiz ve sınırsız sorabileceğiniz bir soru-cevap danışmanı.**

> Namaz, abdest, gusül, oruç, zekât, hac, dua, iman esasları, aile, helâl-haram, ahlâk,
> günlük hayat… Aklınıza gelen her İslami soruyu doğal bir dille yazın; cevabı kaynaklarıyla alın.

**İki katmanlı yapay zekâ:**

1. **Yerel bilgi bankası (RAG kaynağı)** — 152 doğrulanmış kayıt + ~1.900 pasaj. Anahtarsız, kotasız,
   çevrimdışı çalışır. Her zaman açıktır.
2. **Yüksek parametreli dil modeli (isteğe bağlı)** — Gemini 2.5 Flash, Llama 3.3 **70B**,
   GPT-OSS **120B**, Qwen3 **235B** gibi modeller; ücretsiz anahtarla. Model, **1. katmandaki
   kaynaklarla beslenir** ve cevabı özgürce, akıcı biçimde yazar. Arayüzden tek tıkla bağlanır.

> Model çağrısı **doğrudan tarayıcınızdan** yapılır: API anahtarınız sunucuya gitmez, sunucu
> üzerinden ücret/kota tüketilmez.

---

## ✨ Neden "ücretsiz ve sınırsız"?

| Özellik | Durum |
|---|---|
| 💸 Ücret / abonelik | **Yok** |
| 🔑 API anahtarı / hesap açma | **Gerekmez** |
| 📊 Soru limiti / kota | **Yok** |
| 🌐 İnternet bağlantısı | **Gerekmez** (bilgi bankası tamamen yerel) |
| 🕵️ Veri toplama / kayıt | **Yok** — sohbetler yalnızca tarayıcınızda saklanır |
| 🧠 Yapay zekâ | Yerel motor **her zaman**; dil modeli **isteğe bağlı ve ücretsiz** |
| 💾 Anahtarın saklandığı yer | **Yalnızca sizin tarayıcınız** (localStorage) |

Anahtarsız kullanımda cevaplar, **Kur'an âyetleri, sahih hadisler ve klasik fıkıh kaynaklarına
dayanılarak hazırlanmış yerel bilgi bankasından** gelir; her cevabın altında kaynakları listelenir.
Dil modeli bağladığınızda ise model, aynı bilgi bankası kaynaklarıyla beslenir (RAG) ve soruyu
serbestçe, akıcı bir dille cevaplar. Sıfır maliyet, sıfır kayıt.

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

## 🧠 Gerçek Yapay Zekâ (Dil Modeli) Nasıl Bağlanır?

Arayüzde sağ üstteki **"📚 Yerel bilgi bankası"** rozetine tıklayın → sağlayıcıyı seçin → ücretsiz
anahtarınızı yapıştırın → **Kaydet**. Hepsi bu kadar; anahtarınız cihazınızdan çıkmaz.

| Sağlayıcı | Örnek modeller | Ücretsiz katman | Anahtar adresi |
|---|---|---|---|
| **Google Gemini** | `gemini-2.5-flash`, `gemini-2.5-flash-lite` | Günde ~1.500 istek, kredi kartı yok | https://aistudio.google.com/apikey |
| **Groq** | `llama-3.3-70b-versatile`, `openai/gpt-oss-120b` | Dakikada 30 / günde 1.000 istek | https://console.groq.com/keys |
| **OpenRouter** | `qwen/qwen3-235b-a22b:free`, `llama-3.3-70b-instruct:free`, `deepseek-r1:free` | Günde ~50 istek (`:free` uzantısı şart) | https://openrouter.ai/keys |
| **Ollama (yerel)** | `llama3.1:8b`, `qwen2.5:32b`, `gemma2:27b` | **Sınırsız ve tamamen ücretsiz** | https://ollama.com/download |
| **Diğer** | OpenAI uyumlu her servis | — | — |

### Tam sınırsızlık istiyorsanız: Ollama
```bash
# Modeli indirip çalıştırın (kendi bilgisayarınızda)
ollama pull qwen2.5:14b
OLLAMA_ORIGINS=* ollama serve        # tarayıcı erişimi için
```
Sonra arayüzden **Sağlayıcı: Kendi bilgisayarım — Ollama**, model: `qwen2.5:14b` seçin.
İnternet gerekmez, kota yok, ücret yok; veriler cihazınızdan hiç çıkmaz.

### Nasıl çalışır? (RAG akışı)
```
Soru ──► Sunucu (yerel): 152 kayıt + ~1.900 pasaj taranır
          └─► en ilgili 4 kayıt + 6 bölüm "kaynaklı bağlam" olarak paketlenir
                    │
                    ▼
      Tarayıcınız ──► Seçtiğiniz dil modeli (Gemini/Groq/OpenRouter/Ollama)
                       │  sistem yönergesi: Ehl-i Sünnet, delil zorunlu,
                       │  uydurma yasak, ihtilafta görüşleri belirt, müftülüğe yönlendir,
                       │  kriz durumunda 112/183
                       ▼
              Akışlı (yazı yazılarak gelen) cevap + bilgi bankası kaynakları
```
Anahtar yoksa ya da ağ kesilirse uygulama **otomatik olarak yerel motora düşer** — hiçbir soru
cevapsız kalmaz. Kriz/güvenlik soruları (intihar, şiddet, istismar) model çağrılmadan yerel
güvenlik yanıtıyla karşılanır.

---

## 🧩 Neler Yapabilir?

- **152 soru-cevap kaydı**, 13 konu başlığı: İnanç, Taharet, Namaz, Oruç, Zekât, Hac, Aile,
  Helâl-Haram, Ahlâk, Dua, Kur'an, Günlük Hayat, Genel
- **~1.900 pasaj indeksi:** Tam karşılığı olmayan sorularda bile, tüm cevap metinleri
  **paragraf paragraf** taranır ve en ilgili bölümler kaynağıyla sunulur
- **Doğal dil ile arama:** *"adetliyken namaz kılınır mı"*, *"faizli kredi caiz mi"*,
  *"namaz kılmıyorum nasıl başlarım"* gibi sorular anlaşılır
- **Yazım hatası toleransı** ve Türkçe ek/çekim farklılıklarına dayanıklı arama
- **"Bilmiyorum" yerine usul cevabı:** Bilinmeyen *"…caiz mi?"*, *"…hikmeti nedir?"*,
  *"…nasıl yapılır?"* sorularında genel fıkhî ölçüler (aslolan mübahlık, nass, zaruret, ihtilaf) anlatılır
- **Boşluk kaydı:** Cevaplanamayan sorular listelenir (`/api/bosluklar`) — içerik bu listeye göre büyür
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
| `POST` | `/api/baglam` | LLM için **kaynaklı bağlam paketi** (4 kayıt + 6 pasaj + hazır mesaj) |
| `GET`  | `/api/model` | Sistem yönergesi + ücretsiz sağlayıcı/model listesi |
| `GET`  | `/api/istatistik` | Kayıt sayısı, pasaj sayısı, boşluk sayısı, motor bilgisi |
| `GET`  | `/api/bosluklar` | Cevaplanamayan sorular (içerik geliştirme listesi) |
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
│   │   ├── qa_modern.json         # Tesettür, müzik, sigara, dijital hayat, kripto, teknoloji
│   │   ├── qa_miras_ticaret.json  # Miras, vasiyet, sigorta, ortaklık, kira, işçi hakları, vergi, borsa
│   │   ├── qa_evlilik_genis.json  # Evlilik engelleri, mehir, çok eşlilik, kadın hakları, Nisâ 4/34, velayet
│   │   ├── qa_ibadet_ek.json      # Tilâvet/şükür secdesi, adak, yemin, tesbih namazı, nafile oruç, zikir, hatim
│   │   ├── qa_akaid_lim.json      # Bidat, tasavvuf, keramet, rüya, kıyamet alâmetleri, siyer, tekfir, hadis ilmi
│   │   ├── qa_ek2.json            # Üreme sağlığı, fıtrat bakımı, spor, döviz, parfüm, kayınvalide, nişan, askerlik…
│   │   └── qa_ek3.json            # Tutulma (kusûf) namazı, evcil hayvan, kandiller, tecvid
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

**Python testleri (13 adet):** veri bütünlüğü, her kaydın kendi anahtar kelimeleriyle bulunabilmesi,
**120+ örnek sorunun doğru kayda** yönlenmesi, paragraf araması, usul (ilke) cevapları, güvenlik
yanıtları, LLM bağlam uç noktası (`/api/baglam`), sistem yönergesinin kritik kuralları ve
"ücretsiz/sınırsız" sözleşmesi.

**Arayüz testi (21 kontrol, tarayıcı taklidi):**
```bash
npm i jsdom          # bir kez
python -m app.main & # sunucu açıkken gerçek veriyle çalışır
node tests/ui_test.js
```
Bu test; cevabın akışlı yazımını, kaynak bloğunu, güvenlik sorusunda modelin devre dışı kalmasını,
rozetin güncellenmesini ve ayar penceresini doğrular.

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
