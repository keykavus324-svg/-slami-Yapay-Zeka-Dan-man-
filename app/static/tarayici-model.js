/* ==========================================================================
   ŞEYH TUĞRUL — TARAYICIDA ÇALIŞAN MODEL (WebGPU / WASM)
   ==========================================================================
   Model, kullanıcının TARAYICISINDA koşar:
     • sunucuya yük binmez, saniyede onlarca kelime akar,
     • metin hiçbir yere gönderilmez (gizlilik),
     • ilk indirme bir kez yapılır ve tarayıcı önbelleğinde kalır.

   Kütüphane (transformers.js) önce yerel kopyadan, yoksa CDN'den yüklenir.
   Model dosyaları Hugging Face'ten (onnx-community) çekilir.
   ========================================================================== */

export const MODELLER = [
  {
    id: "onnx-community/Qwen2.5-0.5B-Instruct",
    ad: "⚡ Qwen2.5 0.5B — çok hızlı",
    boyut: "~450 MB",
    not: "En hızlısı: zayıf bilgisayarlarda ve telefonlarda bile akıcı. Bilgi bankası bağlamıyla birlikte iyi sonuç verir.",
  },
  {
    id: "onnx-community/Qwen2.5-1.5B-Instruct",
    ad: "⚖️ Qwen2.5 1.5B — dengeli",
    boyut: "~1.1 GB",
    not: "Kalite/hız dengesi. 8 GB RAM'li bilgisayarlar için iyi seçim.",
  },
  {
    id: "onnx-community/Qwen2.5-3B-Instruct",
    ad: "🎯 Qwen2.5 3B — kaliteli",
    boyut: "~2.2 GB",
    not: "Daha isabetli fıkhî cevaplar; GPU veya güçlü CPU önerilir.",
  },
];

/* Kütüphane kaynakları: önce yerel kopya (çevrimdışı), sonra CDN'ler. */
const KUTUPHANE_KAYNAKLARI = [
  { ad: "yerel kopya", url: "/static/vendor/transformers/transformers.web.min.js", yerel: true },
  { ad: "jsdelivr (ESM)", url: "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.1/+esm" },
  { ad: "esm.sh", url: "https://esm.sh/@huggingface/transformers@4.3.1" },
  { ad: "unpkg", url: "https://unpkg.com/@huggingface/transformers@4.3.1/dist/transformers.web.js" },
];

let kutuphane = null;
let boruHatti = null;      // yüklü transformers.js pipeline'ı
let yukluModel = null;     // model kimliği
let yukluCihaz = null;     // "webgpu" | "wasm"
let yukluDtype = null;
let yuklemeSurüyor = null; // devam eden yükleme sözü (aynı anda iki indirme olmasın)
let sonHiz = null;         // son cevabın hızı (kelime/sn)

/* ---------------------------------------------------------------- cihaz */
export function cihazSec() {
  const gpuVar = typeof navigator !== "undefined" && "gpu" in navigator && !!navigator.gpu;
  return gpuVar ? "webgpu" : "wasm";
}

export function cihazEtiketi(cihaz) {
  return cihaz === "webgpu" ? "WebGPU (ekran kartı)" : "WebAssembly (CPU)";
}

function dtypeAdaylari(cihaz) {
  return cihaz === "webgpu"
    ? ["q4f16", "q4", "fp16", "int8"]
    : ["q4", "int8", "uint8", "fp16"];
}

/* -------------------------------------------------------- kütüphane yükleme */
async function kutuphaneYukle(ilerleme) {
  if (kutuphane) return kutuphane;
  const hatalar = [];
  for (const kaynak of KUTUPHANE_KAYNAKLARI) {
    try {
      if (ilerleme) ilerleme({ asama: "kutuphane", mesaj: "Model motoru yükleniyor (" + kaynak.ad + ")…" });
      const mod = await import(/* @vite-ignore */ kaynak.url);
      if (!mod || !mod.pipeline) throw new Error("pipeline bulunamadı");
      kutuphane = mod;
      try {
        kutuphane.env.allowLocalModels = false;
        kutuphane.env.useBrowserCache = true;
      } catch { /* sürüm farkı */ }
      return kutuphane;
    } catch (e) {
      hatalar.push(kaynak.ad + ": " + (e && e.message ? e.message : e));
    }
  }
  throw new Error("Model motoru yüklenemedi. " + hatalar.join(" | "));
}

/* --------------------------------------------------------- model dosyaları */
/** Hugging Face deposunda hangi ONNX sürümleri var? (dtype seçimini isabetli yapar) */
async function onnxDosyalari(modelId) {
  try {
    const y = await fetch("https://huggingface.co/api/models/" + modelId + "/tree/main/onnx");
    if (!y.ok) return null;
    const liste = await y.json();
    return liste.map((x) => x.path || x.rfilename || "").filter(Boolean);
  } catch {
    return null;
  }
}

function dosyalardanDtype(dosyalar, cihaz) {
  if (!dosyalar) return null;
  const aday = dtypeAdaylari(cihaz);
  const bulunan = (d) => dosyalar.some((f) => f.endsWith("model_" + d + ".onnx"));
  for (const d of aday) if (bulunan(d)) return d;
  if (dosyalar.some((f) => f.endsWith("model.onnx"))) return "fp32";
  return null;
}

/* ------------------------------------------------------------------ yükleme */
export function durum() {
  return {
    yuklu: !!boruHatti,
    modelId: yukluModel,
    cihaz: yukluCihaz,
    dtype: yukluDtype,
    hiz: sonHiz,
    cihazEtiketi: yukluCihaz ? cihazEtiketi(yukluCihaz) : cihazEtiketi(cihazSec()),
  };
}

export async function yukle(ayar = {}) {
  const modelId = ayar.modelId || MODELLER[0].id;
  const cihaz = ayar.cihaz || cihazSec();
  const ilerleme = ayar.ilerleme;
  const zorla = !!ayar.zorla;

  if (boruHatti && yukluModel === modelId && yukluCihaz === cihaz && !zorla) return durum();
  if (yuklemeSurüyor) return yuklemeSurüyor;

  yuklemeSurüyor = (async () => {
    bosalt();
    const mod = await kutuphaneYukle(ilerleme);

    const dosyalar = await onnxDosyalari(modelId);
    const adaylar = [];
    const tahmin = dosyalardanDtype(dosyalar, cihaz);
    if (tahmin) adaylar.push(tahmin);
    for (const d of dtypeAdaylari(cihaz)) if (!adaylar.includes(d)) adaylar.push(d);

    let sonHata = null;
    for (const dtype of adaylar) {
      try {
        if (ilerleme) ilerleme({ asama: "model", mesaj: "Model indiriliyor/yükleniyor (" + dtype + ")…", model: modelId, cihaz, dtype });
        const boru = await mod.pipeline("text-generation", modelId, {
          device: cihaz,
          dtype,
          progress_callback: (p) => {
            if (!ilerleme) return;
            if (p && p.status === "progress" && p.total) {
              ilerleme({
                asama: "indirme",
                dosya: p.file || "",
                yuzde: Math.max(0, Math.min(100, Math.round((p.loaded / p.total) * 100))),
                yuklenen: p.loaded,
                toplam: p.total,
                mesaj: "İndiriliyor: " + (p.file || "").split("/").pop(),
              });
            } else if (p && p.status) {
              ilerleme({ asama: p.status, mesaj: p.status === "ready" ? "Hazır!" : p.status });
            }
          },
        });
        boruHatti = boru;
        yukluModel = modelId;
        yukluCihaz = cihaz;
        yukluDtype = dtype;
        if (ilerleme) ilerleme({ asama: "hazir", mesaj: "Model hazır: " + modelId + " (" + cihazEtiketi(cihaz) + ")", model: modelId, cihaz, dtype });
        return durum();
      } catch (e) {
        sonHata = e;
        if (ilerleme) ilerleme({ asama: "uyari", mesaj: dtype + " ile yüklenemedi, sıradaki deneniyor…" });
      }
    }
    throw new Error("Model yüklenemedi: " + (sonHata && sonHata.message ? sonHata.message : sonHata) +
      " — internetinizi kontrol edin ya da sistem içi modele geçin.");
  })();

  try {
    return await yuklemeSurüyor;
  } finally {
    yuklemeSurüyor = null;
  }
}

export function bosalt() {
  try {
    if (boruHatti && typeof boruHatti.dispose === "function") boruHatti.dispose();
  } catch { /* yoksay */ }
  boruHatti = null;
  yukluModel = null;
  yukluCihaz = null;
  yukluDtype = null;
}

/* ---------------------------------------------------------------- üretim */
/**
 * Akışlı cevap üretir.
 * @param {Array<{role:string, content:string}>} mesajlar  sistem + kullanıcı mesajları
 * @param {{onParca?:Function, maksToken?:number, sicaklik?:number, iptal?:{iptal:boolean}}} secenekler
 */
export async function uret(mesajlar, secenekler = {}) {
  if (!boruHatti) throw new Error("Model yüklü değil. Önce 'Modeli başlat' düğmesine basın.");

  const maksToken = Math.min(secenekler.maksToken || 420, 1024);
  const sicaklik = secenekler.sicaklik ?? 0.6;
  const iptal = secenekler.iptal || { iptal: false };
  const basla = Date.now();
  let uzunluk = 0;

  let akis = null;
  try {
    const Streamer = kutuphane.TextStreamer;
    if (Streamer && boruHatti.tokenizer) {
      akis = new Streamer(boruHatti.tokenizer, {
        skip_prompt: true,
        skip_special_tokens: true,
        callback_function: (metin) => {
          if (iptal.iptal) return;
          uzunluk += metin.length;
          if (secenekler.onParca) secenekler.onParca(metin);
        },
      });
    }
  } catch { /* akış desteklenmiyorsa tek seferde alınır */ }

  const secenek = {
    max_new_tokens: maksToken,
    do_sample: sicaklik > 0,
    temperature: sicaklik,
    repetition_penalty: 1.1,
  };
  if (akis) secenek.streamer = akis;

  const sonuc = await boruHatti(mesajlar, secenek);

  let metin = "";
  try {
    const uretilen = sonuc && sonuc[0] && sonuc[0].generated_text;
    if (Array.isArray(uretilen)) {
      const sonMesaj = uretilen[uretilen.length - 1];
      metin = (sonMesaj && sonMesaj.content) || "";
    } else if (typeof uretilen === "string") {
      metin = uretilen;
    }
  } catch { /* akış kullanıldıysa gerek yok */ }

  if (!akis && metin && secenekler.onParca) {
    // akış yoksa cevabı küçük parçalar hâlinde yaz
    const parcalar = metin.match(/[\s\S]{1,18}/g) || [metin];
    for (const p of parcalar) {
      if (iptal.iptal) break;
      secenekler.onParca(p);
      await new Promise((r) => setTimeout(r, 8));
    }
  }

  const saniye = Math.max((Date.now() - basla) / 1000, 0.001);
  sonHiz = Math.round((uzunluk || metin.length) / saniye);
  return { metin: metin || "", hiz: sonHiz, sure: Math.round(saniye * 10) / 10, dtype: yukluDtype, cihaz: yukluCihaz };
}
