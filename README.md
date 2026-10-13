# 🕌 ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı

**İslami sorularınızı ücretsiz ve sınırsız sorabileceğiniz bir soru-cevap danışmanı.**

> Namaz, abdest, gusül, oruç, zekât, hac, dua, iman esasları, aile, helâl-haram, ahlâk,
> günlük hayat… Aklınıza gelen her İslami soruyu doğal bir dille yazın; cevabı kaynaklarıyla alın.

**Dört katmanlı yapay zekâ (hepsi ücretsiz, hepsi sınırsız):**

1. **⚡ Tarayıcıda çalışan model (en hızlı)** — Model **sizin tarayıcınızda** koşar:
   WebGPU varsa ekran kartıyla, yoksa WebAssembly ile. Cevap kelime kelime saniyeler içinde
   akar; yazdığınız metin hiçbir sunucuya gitmez. İlk açılışta model bir kez indirilir
   (varsayılan **Qwen2.5 0.5B ≈ 450 MB**) ve tarayıcı önbelleğinde kalır.
2. **Yerel bilgi bankası (RAG kaynağı)** — 152 doğrulanmış kayıt + ~1.900 pasaj.
   Anahtarsız, kotasız, çevrimdışı; her cevaba kaynak sağlar. Her zaman açıktır.
3. **Sistem içi dil modeli** — Sunucunun makinesinde koşan model (Ollama / llama.cpp /
   llama-cpp-python). GPU'suz sunucular için. `scripts/kur.sh` ya da
   `python -m app.model_indir qwen2.5:7b`.
4. **Bulut modeli (isteğe bağlı)** — Ücretsiz anahtarla Gemini 2.5 Flash / Llama 70B bağlanır;
   çağrı tarayıcıdan yapılır, anahtar sunucuya gitmez.

> Kesintisizlik: hiçbiri yoksa cevaplar yerel bilgi bankasından gelir ve kriz/güvenlik
> soruları hiçbir zaman modele gönderilmez (112/183 yönlendirmesi korunur).

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

## ⚡ Tarayıcıda Çalışan Model (en hızlısı, kurulum yok)

Arayüzde **Dil Modeli Ayarları → ⚡ Tarayıcıda çalışan model → "Modeli başlat"** düğmesine basın.
Hepsi bu; sunucu tarafında hiçbir kurulum gerekmez.

| | |
|---|---|
| **Nerede çalışır?** | Sizin tarayıcınızda (WebGPU varsa GPU ile, yoksa WebAssembly) |
| **İlk indirme** | Varsayılan `Qwen2.5 0.5B` ≈ **450 MB** (tek seferlik, önbellekte kalır) |
| **Tipik hız** | WebGPU: **~40–90 kelime/sn** · WebAssembly: ~5–15 kelime/sn |
| **Gizlilik** | Metin cihazınızdan çıkmaz; sunucuya yalnızca "hangi kayıtlar ilgili" sorusu gider |
| **Ücret/kota** | Yok — model sizin cihazınızda çalışır |
| **Hangi modeller?** | `Qwen2.5 0.5B` (çok hızlı) · `1.5B` (dengeli) · `3B` (kaliteli) — hepsi insan onayıyla, değiştirilebilir |

Küçük modeller bilgi bankası bağlamıyla beslenir (RAG): soruyla ilgili 2 kayıt + 3 bölüm
modele kaynak olarak verilir, böylece 0.5B'lik bir model bile fıkha uygun, kaynaklı cevap üretir.

### Kütüphane yerelden servis edilsin (isteğe bağlı, önerilir)
Tarayıcı modeli, `transformers.js` kütüphanesini önce **kendi sunucumuzdan** yükler; kurulu
değilse otomatik olarak CDN'e düşer. Yerele almak için:
```bash
python -m scripts.vendor_indir          # ~43 MB indirir (transformers.js + onnxruntime WASM)
python -m scripts.vendor_indir --kontrol
```
Bu klasör (`app/static/vendor/`) sürüm takibine girmez; dağıtımda betikle kurulur.

---

## 🖥️ Alternatif: Modeli Sistemin İçine Kur (Ollama / llama.cpp)

Modeli **uygulamanın çalıştığı makineye** kurun; uygulama açılışta otomatik bulur ve kullanır.

### Yol 1 — Ollama (en kolay, Windows/macOS/Linux)
```bash
ollama pull qwen2.5:7b     # ~4.7 GB, tek seferlik
ollama serve               # 127.0.0.1:11434
python -m app.main         # uygulama modeli otomatik bulur
```

### Yol 2 — Tek komutluk kurulum betiği
```bash
./scripts/kur.sh           # Linux/macOS  (Windows: scripts\kur.bat)
```
Betik: bağımlılıkları kurar → modeli indirir → uygulamayı başlatır.

### Yol 3 — GGUF indirme betiği (sunucular için)
```bash
python -m app.model_indir --liste      # boyut/RAM bilgisiyle model listesi
python -m app.model_indir qwen2.5:7b   # models/ klasörüne indirir (kaldığı yerden devam eder)
python -m app.main
```
Elinizde GGUF varsa `models/` klasörüne koymanız yeterli (örn.
`models/qwen2.5-7b-instruct-q4_k_m.gguf`).

### Yol 4 — Docker
```bash
docker compose run --rm tugrul python -m app.model_indir qwen2.5:7b
docker compose up        # → http://localhost:8000
```

### Hangi modeli seçmeliyim?
| Model | Boyut | RAM | Tipik hız (CPU) | Not |
|---|---|---|---|---|
| `qwen2.5:0.5b` | ~400 MB | 1 GB | ~40 tok/sn | Test için; bilgisi sınırlı |
| `qwen2.5:3b` | ~2.0 GB | 4 GB | ~15 tok/sn | Zayıf donanım |
| **`qwen2.5:7b`** ⭐ | ~4.7 GB | 8 GB | ~7 tok/sn | **Önerilen** kalite/hız dengesi |
| `qwen2.5:14b` | ~9.0 GB | 16 GB | ~3 tok/sn | En yüksek kalite |
| `qwen3:8b` | ~5.0 GB | 9 GB | ~6 tok/sn | Güçlü akıl yürütme |

> GPU (NVIDIA/CUDA veya Apple Metal) varsa hız 5–20 kat artar; Ollama/llama.cpp bunu otomatik kullanır.

### Nasıl bulunur? (otomatik algılama sırası)
1. `TUGRUL_YEREL_URL` (varsa, zorlanan adres)
2. **Ollama** `127.0.0.1:11434` → 3. `llama.cpp sunucusu` `:8080` / `:8081` →
   4. **LM Studio** `:1234` → 5. `models/*.gguf` varsa **süreç içi** (llama-cpp-python)
6. Hiçbiri yoksa: yerel bilgi bankası (RAG) cevapları

Durum: `GET /api/yerel-model` · Arayüz: *Dil Modeli Ayarları → Sistem içi model*.
Küçük/demo modeller otomatik olarak **kapalı** başlar (kalite uyarısıyla birlikte açılabilir).

---

## 🧠 Alternatif: Bulut Modeli Bağlamak (isteğe bağlı, anahtarla)

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
| `POST` | `/api/baglam?kisa=true` | Tarayıcı modeli için **sıkıştırılmış** bağlam (2 kayıt + 3 bölüm) |
| `POST` | `/api/sor-yerel` | **Sistem içi model** cevabı — SSE ile kelime kelime akar (anahtarsız) |
| `GET`  | `/api/yerel-model` | Yerel model durumu + önerilen model listesi (boyut/RAM) |
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

**Python testleri (17 adet):** veri bütünlüğü, her kaydın kendi anahtar kelimeleriyle bulunabilmesi,
**120+ örnek sorunun doğru kayda** yönlenmesi, paragraf araması, usul (ilke) cevapları, güvenlik
yanıtları, LLM bağlam uç noktası (`/api/baglam`), **sistem içi model akışı** (`/api/sor-yerel`),
sistem yönergesinin kritik kuralları ve
"ücretsiz/sınırsız" sözleşmesi.

**Arayüz testi (43 kontrol, tarayıcı taklidi):**
```bash
npm i jsdom          # bir kez
python -m app.main & # sunucu açıkken gerçek veriyle çalışır
node tests/ui_test.js
```
Bu test; **tarayıcıda çalışan model akışını** (yükleme → akış → hız rozeti → kaynak bloğu),
sistem içi model akışını (SSE), bilgi bankası yolunu, güvenlik sorusunda modelin devre dışı
kalmasını, model yüklenemediğinde yedeğe düşmeyi ve ayar penceresini doğrular.

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

---

## 📌 Sürüm Notu

- **v4.0** — Cevaplar tarayıcıda çalışan modelle üretilebiliyor (WebGPU/WASM); kütüphane yerelden servis edilir.
- **v3.0** — Sistem içi model katmanı (Ollama / llama.cpp / llama-cpp-python) + GGUF indirici + Docker.
- **v2.0** — RAG katmanı (`/api/baglam`) ve bulut modeli desteği.
- **v1.0** — 152 kayıtlık bilgi bankası, pasaj araması, usul cevapları, boşluk takibi.
