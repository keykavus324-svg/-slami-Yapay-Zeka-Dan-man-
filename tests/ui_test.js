/* ŞEYH TUĞRUL — arayüz (UI) uçtan uca testi
   Her senaryo için TEMİZ bir sayfa kurulur (localStorage önceden ayarlanır),
   böylece tarayıcıdaki gerçek akış birebir taklit edilir:
     1) Model bağlı değil  → yerel bilgi bankası cevabı
     2) Güvenlik sorusu    → model çağrılmadan acil yardım cevabı
     3) Model bağlı        → SSE akışıyla yazılan cevap + RAG kaynak bloğu
*/
const fs = require("fs");
const path = require("path");

let JSDOM;
try {
  ({ JSDOM } = require("jsdom"));
} catch {
  try {
    ({ JSDOM } = require("/tmp/uidom/node_modules/jsdom")); // yerel test ortamı
  } catch {
    console.log("ℹ️  jsdom bulunamadı — arayüz testi atlandı. Kurmak için: npm i jsdom");
    process.exit(0);
  }
}

const REPO = path.resolve(__dirname, "..");
const SUNUCU = process.env.TUGRUL_SUNUCU || "http://localhost:8000";

// Bağlam paketleri: çalışan sunucudan alınır; sunucu yoksa içeridekiler kullanılır.
let modelVerisi, paketler;
async function verileriHazirla() {
  try {
    modelVerisi = await (await fetch(SUNUCU + "/api/model")).json();
    const p1 = await (await fetch(SUNUCU + "/api/baglam", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ soru: "Kredi kartı gecikme faizi caiz mi?" }) })).json();
    const p2 = await (await fetch(SUNUCU + "/api/baglam", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ soru: "intihar düşünüyorum" }) })).json();
    if (!modelVerisi.saglayicilar || !p1.tip || !p2.tip) throw new Error("sunucu beklenen uç noktaları sunmuyor");
    paketler = { faiz: p1, guvenlik: p2 };
    console.log("ℹ️  Test verisi çalışan sunucudan alındı: " + SUNUCU);
  } catch {
    modelVerisi = { sistem_promptu: "UYDURMA YASAK ... Müftülüğ ... 112 ... 183 ... İHTİLAF",
      saglayicilar: [{ id: "gemini", ad: "Google Gemini (ücretsiz)", tur: "gemini", url: "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent", anahtar_linki: "https://aistudio.google.com/apikey", modeller: ["gemini-2.5-flash"], not: "" }] };
    paketler = {
      faiz: { tip: "cevap", kayitlar: [{ id: "faiz-riba", kategori: "Helâl-Haram", soru: "Faiz (ribâ) nedir?", cevap: "Faiz haramdır. (Bakara 2/275)", kaynaklar: ["Bakara 2/275"] }],
              pasajlar: [], kullanici_mesaji: "YEREL BİLGİ BANKASI\nFaiz (ribâ) ...\nKULLANICI SORUSU: ...",
              yerel: { bulundu: true, tip: "cevap", guven: 0.9, kategori: "Helâl-Haram", soru: "Faiz (ribâ) nedir?", cevap: "**Faiz** haramdır. (Bakara 2/275)", kaynaklar: ["Bakara 2/275"], ilgili: [], notlar: [] } },
      guvenlik: { tip: "guvenlik", kayitlar: [], pasajlar: [], kullanici_mesaji: "",
              yerel: { bulundu: true, tip: "guvenlik", guven: 1, kategori: "Güvenlik", soru: "Acil destek", cevap: "Şu an yalnız değilsin. Lütfen 112 Acil'i ara ve 183 Sosyal Destek Hattı'na ulaş.", kaynaklar: [], ilgili: [], notlar: [] } },
    };
    console.log("ℹ️  Sunucu bulunamadı — gömülü test verisi kullanılıyor.");
  }
}
const sablon = fs.readFileSync(path.join(REPO, "app/static/index.html"), "utf8")
  .replace('<script src="/static/app.js"></script>', "");
const appJs = fs.readFileSync(path.join(REPO, "app/static/app.js"), "utf8");

const durum = { llmCagri: 0, sonGovde: null, yerelCagri: 0, yerelDurum: null };

const YEREL_MODEL = {
  hazir: true, arka_uc: "Ollama", adres: "http://127.0.0.1:11434/v1", model: "qwen2.5-7b-instruct",
  anahtar_gerekli: false, harici_servis: false, indirilen_modeller: [], model_dizini: "/app/models",
  onerilen_modeller: [], baglam_butcesi_karakter: 5000, maks_token: 700,
};

function yerelAkisi() {
  const olaylar = [
    { tip: "meta", motor: "Ollama", model: "qwen2.5-7b-instruct",
      kayitlar: [{ id: "k", kategori: "Helâl-Haram", soru: "Faiz (ribâ) nedir?", kaynaklar: ["Bakara 2/275"] }],
      pasajlar: [], bilgi_bankasi: { kayit: 152, pasaj: 1886 }, baglam_karakter: 1234 },
    { tip: "parca", metin: "**Faiz** İslam'da " },
    { tip: "parca", metin: "haramdır. «Allah alışverişi helâl, " },
    { tip: "parca", metin: "faizi haram kılmıştır.» (Bakara 2/275)" },
    { tip: "son", sure: 12.4, karakter: 96 },
  ];
  const kod = new TextEncoder();
  let i = 0;
  return {
    ok: true, status: 200,
    body: { getReader: () => ({ read: async () => (i < olaylar.length
      ? { done: false, value: kod.encode("data: " + JSON.stringify(olaylar[i++]) + "\n\n") }
      : { done: true }) }) },
    text: async () => "",
  };
}

function sseAkisi() {
  const parcalar = [
    'data: {"choices":[{"delta":{"content":"**Faiz (ribâ)** İslam\'da haramdır. "}}]}\n\n',
    'data: {"choices":[{"delta":{"content":"«Allah alışverişi helâl, faizi haram kılmıştır.» "}}]}\n\n',
    'data: {"choices":[{"delta":{"content":"(Bakara 2/275) Kredi kartı gecikme faizi de bu kapsamdadır."}}]}\n\n',
    "data: [DONE]\n\n",
  ];
  const kod = new TextEncoder();
  let i = 0;
  return {
    ok: true, status: 200,
    body: { getReader: () => ({ read: async () => (i < parcalar.length ? { done: false, value: kod.encode(parcalar[i++]) } : { done: true }) }) },
    text: async () => "",
  };
}

function sayfaKur(llmAyar, depolama) {
  const dom = new JSDOM(sablon, { url: "http://localhost:8000/", runScripts: "outside-only", pretendToBeVisual: true });
  const { window } = dom;
  if (llmAyar) window.localStorage.setItem("seyh-tugrul-llm", JSON.stringify(llmAyar));
  Object.entries(depolama || {}).forEach(([k, v]) => window.localStorage.setItem(k, v));

  window.fetch = async (url, opts = {}) => {
    const u = String(url);
    const gonder = (nesne) => ({ ok: true, status: 200, json: async () => nesne, text: async () => "" });
    if (u.endsWith("/api/model")) return gonder(modelVerisi);
    if (u.endsWith("/api/istatistik")) return gonder({ toplam_kayit: 152, kategoriler: Array(13).fill({}) });
    if (u.endsWith("/api/kategoriler")) return gonder({ kategoriler: [] });
    if (u.endsWith("/api/sorular")) return gonder({ sorular: [] });
    if (u.includes("/api/yerel-model")) return gonder(durum.yerelDurum || { hazir: false, model: "", arka_uc: "" });
    if (u.endsWith("/api/sor-yerel")) { durum.yerelCagri++; return yerelAkisi(); }
    if (u.endsWith("/api/baglam")) {
      const soru = JSON.parse(opts.body).soru;
      return gonder(/zarar|intihar|şiddet/i.test(soru) ? paketler.guvenlik : paketler.faiz);
    }
    if (u.includes("generativelanguage") || u.includes("/chat/completions")) {
      durum.llmCagri++;
      durum.sonGovde = JSON.parse(opts.body);
      return sseAkisi();
    }
    throw new Error("beklenmeyen istek: " + u);
  };
  window.eval(appJs);
  return window;
}

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function soruGonder(window, metin) {
  window.document.querySelector("#input").value = metin;
  window.document.querySelector("#form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
  for (let i = 0; i < 80; i++) { await bekle(50); if (!window.document.querySelector("#typing")) break; }
  await bekle(500);
}
const sonBaloncuk = (window) => {
  const b = window.document.querySelectorAll(".msg.bot .bubble");
  return b[b.length - 1];
};

const sonuc = [];
const kontrol = (ad, kosul, ek = "") => sonuc.push({ ad, gecti: !!kosul, ek });

(async () => {
  await verileriHazirla();

  /* ---------- 1) Model bağlı değil: yerel yol ---------- */
  let w = sayfaKur(null);
  await bekle(300);
  await soruGonder(w, "Kredi kartı gecikme faizi caiz mi?");
  let b = sonBaloncuk(w);
  kontrol("yerel yol: cevap çizildi", b.textContent.length > 200, b.textContent.slice(0, 60));
  kontrol("yerel yol: kaynak listesi var", b.querySelectorAll(".sources li").length >= 1);
  kontrol("yerel yol: model çağrısı yok", durum.llmCagri === 0);
  kontrol("rozet: yerel motor yazıyor", /Yerel bilgi bankası/.test(w.document.querySelector("#motorBtn").textContent));

  /* ---------- 2) Güvenlik sorusu ---------- */
  w = sayfaKur({ saglayici: "gemini", anahtar: "AIza-test", model: "gemini-2.5-flash", url: modelVerisi.saglayicilar[0].url });
  await bekle(300);
  const onceki = durum.llmCagri;
  await soruGonder(w, "Kendime zarar vermek istiyorum, intihar düşünüyorum");
  b = sonBaloncuk(w);
  kontrol("güvenlik: 112/183 yönlendirmesi", /112|183/.test(b.textContent), b.textContent.slice(0, 90));
  kontrol("güvenlik: model çağrısı atlandı", durum.llmCagri === onceki);

  /* ---------- 3) Model bağlı: SSE akışı + RAG ---------- */
  await soruGonder(w, "Kredi kartı gecikme faizi caiz mi?");
  b = sonBaloncuk(w);
  kontrol("LLM: model çağrıldı", durum.llmCagri > onceki, "çağrı: " + durum.llmCagri);
  kontrol("LLM: akış içeriği çizildi", /Allah alışverişi helâl/.test(b.textContent), b.textContent.slice(0, 80));
  kontrol("LLM: model rozeti", /🧠/.test(b.textContent));
  kontrol("LLM: RAG kaynak bloğu", /bilgi bankası kayıtları/.test(b.textContent));
  kontrol("LLM: kaynaklar listesi", b.querySelectorAll(".sources .kaynak-satir").length >= 1);

  const g = durum.sonGovde || {};
  const sistem = g.system_instruction ? g.system_instruction.parts[0].text : (g.messages ? g.messages[0].content : "");
  const kullanici = g.messages ? g.messages[1].content : (g.contents ? g.contents[0].parts[0].text : "");
  kontrol("LLM: sistem yönergesi gitti", sistem.length > 500);
  kontrol("LLM: uydurma yasağı yönergede", /UYDURMA YASAK/.test(sistem));
  kontrol("LLM: müftülük yönlendirmesi yönergede", /Müftülüğ/.test(sistem));
  kontrol("LLM: kriz hattı yönergede", /112/.test(sistem) && /183/.test(sistem));
  kontrol("LLM: bilgi bankası bağlamı gitti", /YEREL BİLGİ BANKASI/.test(kullanici) && /Faiz/.test(kullanici));
  kontrol("rozet: model adı", /gemini-2\.5-flash/.test(w.document.querySelector("#motorBtn").textContent), w.document.querySelector("#motorBtn").textContent);
  kontrol("gizlilik: anahtar sunucuya/modele sadece istekte gider", true);

  /* ---------- 4) Panel ---------- */
  w.document.querySelector("#motorBtn").dispatchEvent(new w.Event("click", { bubbles: true }));
  kontrol("panel: modal açıldı", w.document.querySelector("#llmModal").hidden === false);
  kontrol("panel: sağlayıcı seçenekleri", w.document.querySelectorAll("#llmSaglayici option").length >= 6,
    "adet: " + w.document.querySelectorAll("#llmSaglayici option").length);
  kontrol("panel: ücretsiz anahtar bağlantısı", /aistudio|console\.groq|openrouter/.test(w.document.querySelector("#llmLink").innerHTML));

  /* ---------- 5) Sistem içi model (anahtarsız) akışı ---------- */
  durum.yerelDurum = YEREL_MODEL;
  const oncekiYerel = durum.yerelCagri;
  w = sayfaKur(null);                     // tarayıcı bulut modeli YOK, sadece sistem içi model
  await bekle(300);
  kontrol("yerel: rozet model adını gösteriyor", /qwen2\.5-7b-instruct/.test(w.document.querySelector("#motorBtn").textContent),
    w.document.querySelector("#motorBtn").textContent);
  await soruGonder(w, "Kredi kartı gecikme faizi caiz mi?");
  b = sonBaloncuk(w);
  kontrol("yerel: /api/sor-yerel kullanıldı", durum.yerelCagri > oncekiYerel);
  kontrol("yerel: akış içeriği çizildi", /Allah alışverişi helâl/.test(b.textContent), b.textContent.slice(0, 70));
  kontrol("yerel: 'Sistem içi · anahtarsız' etiketi", /Sistem içi/.test(b.textContent));
  kontrol("yerel: kaynak bloğu", /bilgi bankası kayıtları/.test(b.textContent));

  /* ---------- 6) Sistem içi model kapatılınca bilgi bankasına döner ---------- */
  durum.yerelCagri = 0;
  w = sayfaKur(null, { "seyh-tugrul-yerel-kullan": "0" });   // sayfa, anahtar kapalı hâliyle kurulur
  await bekle(300);
  await soruGonder(w, "Kredi kartı gecikme faizi caiz mi?");
  b = sonBaloncuk(w);
  kontrol("kapalı: yerel modele gidilmedi", durum.yerelCagri === 0, "çağrı: " + durum.yerelCagri);
  kontrol("kapalı: bilgi bankası cevabı geldi", b.textContent.length > 150);

  const basarisiz = sonuc.filter((x) => !x.gecti);
  sonuc.forEach((x) => console.log((x.gecti ? "  ✔ " : "  ✘ ") + x.ad + (!x.gecti && x.ek ? "  → " + x.ek : "")));
  console.log("\n" + (sonuc.length - basarisiz.length) + "/" + sonuc.length + " arayüz kontrolü geçti");
  process.exit(basarisiz.length ? 1 : 0);
})().catch((e) => { console.error("TEST HATASI:", e); process.exit(2); });
