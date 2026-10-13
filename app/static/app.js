/* ============================================================
   ŞEYH TUĞRUL — İslami Yapay Zeka Danışmanı  •  Arayüz mantığı
   Harici servis yok: yalnızca kendi FastAPI backend'imiz (/api/*)
   ============================================================ */
(() => {
  "use strict";

  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const chat   = $("#chat");
  const input  = $("#input");
  const form   = $("#form");
  const sendBtn= $("#sendBtn");
  const chips  = $("#chips");

  let DETAY = "normal";
  let gecmis = [];
  let MODEL_BILGISI = { sistem_promptu: "", saglayicilar: [] };
  /* Sistem içi (yerel) model durumu — anahtar yok, dış servis yok */
  let YEREL = { hazir: false, model: "", arka_uc: "", kucuk_model: false };
  /* Üç durumlu tercih: null = otomatik (küçük model ise kapalı), "1" = açık, "0" = kapalı */
  function yerelEtkin() {
    if (!YEREL.hazir) return false;
    let tercih = null;
    try { tercih = localStorage.getItem("seyh-tugrul-yerel-kullan"); } catch {}
    if (tercih === "0") return false;
    if (tercih === "1") return true;
    return !YEREL.kucuk_model;
  }

  /* ------------------------- Markdown (hafif) ------------------------- */
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function inline(s) {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>")
      .replace(/«([^»]+)»/g, "«<em>$1</em>»");
  }

  function markdown(md) {
    const lines = esc(md).replace(/\r/g, "").split("\n");
    const out = [];
    let i = 0;

    const isTableSep = (l) => /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(l) && l.includes("-");
    const cells = (l) => l.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());

    while (i < lines.length) {
      let line = lines[i];

      // Tablo
      if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
        const head = cells(line);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].includes("|")) { rows.push(cells(lines[i])); i++; }
        out.push(
          "<table><thead><tr>" + head.map((h) => `<th>${inline(h)}</th>`).join("") + "</tr></thead><tbody>" +
          rows.map((r) => "<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>").join("") +
          "</tbody></table>"
        );
        continue;
      }

      // Başlık
      let m = line.match(/^(#{2,4})\s+(.*)$/);
      if (m) { out.push(`<h${m[1].length === 2 ? 3 : 4}>${inline(m[2])}</h${m[1].length === 2 ? 3 : 4}>`); i++; continue; }

      // Yatay çizgi
      if (/^\s*(---|___|\*\*\*)\s*$/.test(line)) { out.push("<hr>"); i++; continue; }

      // Alıntı
      if (/^\s*>\s?/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) { buf.push(lines[i].replace(/^\s*>\s?/, "")); i++; }
        out.push(`<blockquote>${inline(buf.join(" "))}</blockquote>`);
        continue;
      }

      // Sıralı liste
      if (/^\s*\d+[.)]\s+/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) { buf.push(lines[i].replace(/^\s*\d+[.)]\s+/, "")); i++; }
        out.push("<ol>" + buf.map((b) => `<li>${inline(b)}</li>`).join("") + "</ol>");
        continue;
      }

      // Madde listesi
      if (/^\s*[-*•]\s+/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) { buf.push(lines[i].replace(/^\s*[-*•]\s+/, "")); i++; }
        out.push("<ul>" + buf.map((b) => `<li>${inline(b)}</li>`).join("") + "</ul>");
        continue;
      }

      // Boş satır
      if (!line.trim()) { i++; continue; }

      // Paragraf
      const par = [line];
      i++;
      while (i < lines.length && lines[i].trim() &&
             !/^\s*([-*•]|\d+[.)]|>|#{2,4}\s|\|)/.test(lines[i]) &&
             !(lines[i].includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1]))) {
        par.push(lines[i]); i++;
      }
      out.push(`<p>${inline(par.join(" "))}</p>`);
    }
    return out.join("");
  }

  /* ------------------------- Yardımcılar ------------------------- */
  const scrollDown = () => { chat.scrollTop = chat.scrollHeight; };

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function botAvatar() { return el("div", "avatar", "🕌"); }
  function userAvatar() { return el("div", "avatar", "🧑"); }

  /* ------------------------- Mesaj çizimi ------------------------- */
  function addUser(text) {
    const wrap = el("div", "msg user");
    wrap.appendChild(el("div", "bubble", `<div class="answer">${markdown(text)}</div>`));
    wrap.appendChild(userAvatar());
    chat.appendChild(wrap);
    gecmis.push({ rol: "user", metin: text });
    kaydet();
    scrollDown();
  }

  function addTyping() {
    const wrap = el("div", "msg bot");
    wrap.id = "typing";
    wrap.appendChild(botAvatar());
    wrap.appendChild(el("div", "bubble", `<div class="typing"><i></i><i></i><i></i></div>`));
    chat.appendChild(wrap);
    scrollDown();
    return wrap;
  }

  function addBot(r) {
    const wrap = el("div", "msg bot");
    wrap.appendChild(botAvatar());

    const bubble = el("div", "bubble");
    const meta = el("div", "meta");

    if (r.kategori) meta.appendChild(el("span", "chip cat", `📚 ${esc(r.kategori)}`));
    if (r.tip === "cevap" && typeof r.guven === "number")
      meta.appendChild(el("span", "chip conf", `Güven: %${Math.round(r.guven * 100)}`));
    if (r.tip === "guvenlik") meta.appendChild(el("span", "chip conf", "⚠️ Öncelik: güvenlik ve destek"));
    if (r.tip === "kategori") meta.appendChild(el("span", "chip", "Konu listesi"));
    bubble.appendChild(meta);

    if (r.soru && r.tip === "cevap") bubble.appendChild(el("p", "q-title", `Soru: <b>${esc(r.soru)}</b>`));

    bubble.appendChild(el("div", "answer", markdown(r.cevap || "")));

    // Bilgi bankasından ilgili bölümler (pasaj araması)
    if (r.pasajlar && r.pasajlar.length) {
      const box = el("div", "pasajlar");
      box.appendChild(el("h5", null, "📖 Bilgi bankasından ilgili bölümler"));
      r.pasajlar.forEach((p) => {
        const item = el("div", "pasaj");
        const head = el("div", "pasaj-head");
        head.innerHTML = `↳ <b>${esc(p.soru)}</b> <span class="chip cat">${esc(p.kategori || "")}</span>`;
        item.appendChild(head);
        item.appendChild(el("div", "pasaj-body", markdown(p.metin || "")));
        const b = el("button", "tool", "Tamamını gör");
        b.addEventListener("click", () => soruSor(p.soru));
        item.appendChild(b);
        box.appendChild(item);
      });
      bubble.appendChild(box);
    }

    if (r.ilgili && r.ilgili.length) {
      const rel = el("div", "related");
      rel.appendChild(el("span", "q-title", "Benzer konular:"));
      r.ilgili.forEach((x) => {
        const b = el("button", "rel", `↳ ${esc(x.soru)}`);
        b.title = x.kategori || "";
        b.addEventListener("click", () => soruSor(x.soru));
        rel.appendChild(b);
      });
      bubble.appendChild(rel);
    }

    if (r.kaynaklar && r.kaynaklar.length) {
      const src = el("div", "sources");
      src.appendChild(el("h5", null, "Kaynaklar"));
      src.appendChild(el("ul", null, r.kaynaklar.map((k) => `<li>${esc(k)}</li>`).join("")));
      bubble.appendChild(src);
    }

    if (r.notlar && r.notlar.length) {
      bubble.appendChild(el("div", "notlar", r.notlar.map((n) => `⚠️ ${inline(esc(n))}`).join("<br>")));
    }

    const tools = el("div", "tools");
    const copy = el("button", "tool", "📋 Kopyala");
    copy.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(r.cevap || ""); copy.textContent = "✔ Kopyalandı"; }
      catch { copy.textContent = "Kopyalanamadı"; }
      setTimeout(() => (copy.textContent = "📋 Kopyala"), 1800);
    });
    tools.appendChild(copy);
    if (r.tip === "cevap") {
      const rf = el("button", "tool", "🎲 Benzer soru");
      rf.addEventListener("click", rastgele);
      tools.appendChild(rf);
    }
    bubble.appendChild(tools);

    wrap.appendChild(bubble);
    chat.appendChild(wrap);
    gecmis.push({ rol: "bot", veri: r });
    kaydet();
    scrollDown();
  }



  /* ============================================================
     SİSTEM İÇİ (YEREL) DİL MODELİ
     Model, uygulamanın çalıştığı makinede koşar: Ollama / llama.cpp /
     llama-cpp-python. API anahtarı yok, dış servis yok, kota yok.
     ============================================================ */
  const YEREL_KUCUK_DESEN = /(tiny|0\.5b|135m|360m|1b|demo|test|stories)/i;

  function yerelRozet() {
    const kullanilabilir = yerelEtkin();
    const durum = $("#yerelDurum");
    const ozet = $("#yerelOzet");
    const kutu = $("#yerelKullan");
    if (kutu) kutu.checked = kullanilabilir;
    if (kutu) kutu.disabled = !YEREL.hazir;

    if (durum) {
      durum.textContent = YEREL.hazir ? (kullanilabilir ? "Bağlı" : "Hazır (kapalı)") : "Bulunamadı";
      durum.classList.toggle("on", kullanilabilir);
    }
    if (ozet) {
      ozet.innerHTML = YEREL.hazir
        ? "Sunucuda <b>" + esc(YEREL.model || "yerel model") + "</b> çalışıyor (" + esc(YEREL.arka_uc || "yerel") + "). " +
          (YEREL.kucuk_model
            ? "⚠️ <b>Küçük bir demo modeli</b> algılandı (test için). Otomatik olarak <b>kapalı</b> tutulur; denemek isterseniz aşağıdaki anahtarı açın. Kaliteli cevap için <b>qwen2.5:7b</b> gibi büyük bir model kurun."
            : "Cevaplar bu model tarafından üretilir; bilgi bankası kaynakları modelle paylaşılır.")
        : "Sunucuda yerel model bulunamadı. <b>Kurulum komutları</b> ile 3 dakikada kurabilirsiniz — anahtar, ücret, kota yoktur.";
    }
    motorRozeti();
  }

  async function yerelDurumYukle(zorla = false) {
    try {
      const r = await fetch("/api/yerel-model" + (zorla ? "?zorla=true" : ""));
      YEREL = await r.json();
      YEREL.kucuk_model = YEREL_KUCUK_DESEN.test((YEREL.model || "") + " " + (YEREL.arka_uc || ""));
    } catch { YEREL = { hazir: false, model: "", arka_uc: "", kucuk_model: false }; }
    yerelRozet();
  }

  async function yerelAkisi(soru, t) {
    const wrap = el("div", "msg bot");
    wrap.appendChild(botAvatar());
    const bubble = el("div", "bubble");
    const meta = el("div", "meta");
    meta.appendChild(el("span", "chip llm", "🧠 " + esc(YEREL.model || "yerel model")));
    meta.appendChild(el("span", "chip cat", "Sistem içi · anahtarsız"));
    bubble.appendChild(meta);
    bubble.appendChild(el("p", "q-title", "Soru: <b>" + esc(soru) + "</b>"));
    if (YEREL.kucuk_model)
      bubble.appendChild(el("div", "notlar", "⚠️ Küçük demo modeli devrede: cevap yavaş gelebilir ve bilgisi sınırlıdır. Kaliteli cevaplar için <b>qwen2.5:7b</b> gibi büyük bir model kurun."));
    const ans = el("div", "answer", '<p class="mini">🧠 Yerel model cevap yazıyor…</p>');
    bubble.appendChild(ans);
    wrap.appendChild(bubble);
    chat.appendChild(wrap);
    scrollDown();

    let birikim = "";
    let kaynakVeri = null;
    let sonCizim = 0;
    const ciz = (zorla) => {
      const n = performance.now();
      if (!zorla && n - sonCizim < 90) return;
      sonCizim = n;
      ans.innerHTML = markdown(birikim) + (zorla ? "" : '<span class="imlec"></span>');
      scrollDown();
    };

    const res = await fetch("/api/sor-yerel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ soru }),
    });
    if (!res.ok || !res.body) throw new Error("Yerel model akışı başlatılamadı (HTTP " + res.status + ")");

    const oku = res.body.getReader();
    const coz = new TextDecoder();
    let tampon = "";
    let yedek = null;
    let hataMesaji = "";

    const isle = (olay) => {
      if (olay.tip === "meta") {
        kaynakVeri = olay;
        meta.insertBefore(el("span", "chip conf", esc(olay.motor || "yerel")), meta.firstChild.nextSibling);
      } else if (olay.tip === "parca") {
        birikim += olay.metin || "";
        ciz(false);
      } else if (olay.tip === "son") {
        ciz(true);
      } else if (olay.tip === "hata") {
        hataMesaji = olay.mesaj || "bilinmeyen hata";
      } else if (olay.tip === "yedek") {
        yedek = olay.cevap;
      }
    };

    for (;;) {
      const { done, value } = await oku.read();
      if (done) break;
      tampon += coz.decode(value, { stream: true });
      let i;
      while ((i = tampon.indexOf("\n")) >= 0) {
        const satir = tampon.slice(0, i).trim();
        tampon = tampon.slice(i + 1);
        if (!satir.startsWith("data:")) continue;
        const veri = satir.slice(5).trim();
        if (!veri || veri === "[DONE]") continue;
        try { isle(JSON.parse(veri)); } catch { /* atla */ }
      }
    }

    if (birikim.trim()) {
      ciz(true);
      if (kaynakVeri) bubble.appendChild(kaynakBloku(kaynakVeri));
      const tools = el("div", "tools");
      const kopya = el("button", "tool", "📋 Kopyala");
      kopya.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(birikim); kopya.textContent = "✔ Kopyalandı"; }
        catch { kopya.textContent = "Kopyalanamadı"; }
        setTimeout(() => (kopya.textContent = "📋 Kopyala"), 1800);
      });
      tools.appendChild(kopya);
      const ayar = el("button", "tool", "⚙️ Model ayarları");
      ayar.addEventListener("click", llmAc);
      tools.appendChild(ayar);
      bubble.appendChild(tools);
      gecmis.push({ rol: "bot", veri: { bulundu: true, tip: "yerel", guven: 1, kategori: "Sistem içi model", soru: soru, cevap: birikim, kaynaklar: [], ilgili: [], notlar: [] } });
      kaydet();
    } else {
      ans.innerHTML = "";
      bubble.appendChild(el("div", "notlar",
        "⚠️ " + esc(hataMesaji || "Yerel modelden cevap alınamadı") + (yedek ? " — bilgi bankası cevabı gösteriliyor." : "")));
      if (yedek) addBot(yedek);
    }
    scrollDown();
  }

  /* ============================================================
     YÜKSEK PARAMETRELİ DİL MODELİ (LLM) KATMANI
     • Model çağrısı doğrudan TARAYICIDAN yapılır — API anahtarı sunucuya gitmez.
     • Sunucu yalnızca yerel bilgi bankasından KAYNAKLI BAĞLAM üretir (RAG).
     ============================================================ */
  const AYAR_ANAHTAR = "seyh-tugrul-llm";
  let LLM = null;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function llmOku() {
    try { LLM = JSON.parse(localStorage.getItem(AYAR_ANAHTAR) || "null"); } catch { LLM = null; }
  }
  function llmYaz() {
    try {
      if (LLM) localStorage.setItem(AYAR_ANAHTAR, JSON.stringify(LLM));
      else localStorage.removeItem(AYAR_ANAHTAR);
    } catch {}
  }
  const saglayiciBul = (id) => (MODEL_BILGISI.saglayicilar || []).find((x) => x.id === id) || null;
  const llmAktif = () =>
    !!(LLM && LLM.model && saglayiciBul(LLM.saglayici) && (LLM.anahtar || LLM.saglayici === "ollama"));

  function motorRozeti() {
    const sag = LLM ? saglayiciBul(LLM.saglayici) : null;
    const yazi = yerelEtkin()
      ? "🧠 " + (YEREL.model || "yerel model")
      : (YEREL.hazir && !yerelEtkin())
        ? "🧠 " + (YEREL.model || "model") + " (kapalı)"
        : llmAktif() && sag
          ? "🧠 " + sag.ad.split("—")[0].split("(")[0].trim() + " · " + LLM.model
          : "📚 Yerel bilgi bankası";
    const b = $("#motorBtn");
    if (b) b.textContent = yazi;
    const durum = $("#motorDurum");
    if (durum) {
      durum.textContent = llmAktif() ? "Model bağlı" : "Yerel";
      durum.classList.toggle("on", llmAktif());
    }
    const ozet = $("#motorOzet");
    if (ozet) {
      ozet.innerHTML = llmAktif() && sag
        ? "<b>" + esc(sag.ad) + "</b> bağlı — cevaplar bu model tarafından, bilgi bankası kaynaklarıyla üretiliyor."
        : "Şu an <b>yerel bilgi bankası</b> cevaplıyor. İstersen ücretsiz bir yüksek parametreli model (Gemini / Llama 70B / GPT-OSS 120B) bağla.";
    }
  }

  async function modelBilgisiYukle() {
    try {
      const r = await fetch("/api/model");
      MODEL_BILGISI = await r.json();
    } catch { /* yerel motor yine çalışır */ }
    llmPaneliDoldur();
    motorRozeti();
  }

  function llmPaneliDoldur() {
    const sec = $("#llmSaglayici");
    if (!sec) return;
    sec.innerHTML = '<option value="yerel">📚 Yerel bilgi bankası (dil modeli yok)</option>';
    (MODEL_BILGISI.saglayicilar || []).forEach((sg) => {
      const o = document.createElement("option");
      o.value = sg.id;
      o.textContent = sg.ad;
      sec.appendChild(o);
    });
    // Kayıtlı model varsa paneli onunla aç
    sec.value = LLM && LLM.saglayici && saglayiciBul(LLM.saglayici) ? LLM.saglayici : "yerel";
    sec.onchange = () => formuGuncelle();
    formuGuncelle();
  }

  function formuGuncelle() {
    const id = $("#llmSaglayici").value;
    const sg = saglayiciBul(id);
    const not = $("#llmSagNot");
    const liste = $("#llmModelListe");
    const urlSar = $("#llmUrlSar");
    liste.innerHTML = "";
    if (!sg) { // yerel
      not.textContent = "Dil modeli kapalı: cevaplar 152 kayıtlık yerel bilgi bankasından gelir (ücretsiz, kotasız, çevrimdışı).";
      urlSar.hidden = true;
      const lnk = $("#llmLink"); if (lnk) lnk.innerHTML = "";
      return;
    }
    not.textContent = sg.not || "";
    (sg.modeller || []).forEach((m) => {
      const o = document.createElement("option"); o.value = m; liste.appendChild(o);
    });
    urlSar.hidden = sg.id !== "ozel";
    const mevcut = LLM && LLM.saglayici === id ? LLM : null;
    $("#llmModel").value = (mevcut && mevcut.model) || (sg.modeller || [])[0] || "";
    $("#llmAnahtar").value = (mevcut && mevcut.anahtar) || "";
    $("#llmUrl").value = (mevcut && mevcut.url) || sg.url || "";
    const link = $("#llmLink");
    link.innerHTML = sg.anahtar_linki
      ? '🔑 Ücretsiz anahtar: <a href="' + sg.anahtar_linki + '" target="_blank" rel="noopener">' + sg.anahtar_linki + "</a>"
      : "";
  }

  function llmAc() { $("#llmModal").hidden = false; formuGuncelle(); }
  function llmKapat() { $("#llmModal").hidden = true; }

  /* ------------------- Model çağrısı (akışlı / SSE) ------------------- */
  function llmUrl(sg) {
    const temel = (LLM && LLM.url) || sg.url || "";
    if (sg.tur === "gemini") {
      const u = temel.replace("{model}", encodeURIComponent(LLM.model));
      return u + (u.includes("?") ? "&" : "?") + "alt=sse&key=" + encodeURIComponent(LLM.anahtar || "");
    }
    return temel;
  }

  function llmGovde(sg, kullanici) {
    const sistem = MODEL_BILGISI.sistem_promptu || "";
    if (sg.tur === "gemini") {
      return {
        system_instruction: { parts: [{ text: sistem }] },
        contents: [{ role: "user", parts: [{ text: kullanici }] }],
        generationConfig: { temperature: 0.55, maxOutputTokens: 2400 },
      };
    }
    return {
      model: LLM.model,
      messages: [
        { role: "system", content: sistem },
        { role: "user", content: kullanici },
      ],
      temperature: 0.55,
      stream: true,
      max_tokens: 2400,
    };
  }

  function llmBasliklar(sg) {
    const h = { "Content-Type": "application/json" };
    if (LLM.anahtar) h["Authorization"] = "Bearer " + LLM.anahtar;
    if (sg.id === "openrouter") { h["HTTP-Referer"] = location.origin; h["X-Title"] = "Seyh Tugrul"; }
    return h;
  }

  function parcaAyikla(j) {
    if (j.candidates) {
      const p = (j.candidates[0] || {}).content || {};
      return (p.parts || []).map((x) => x.text || "").join("");
    }
    const c = j.choices && j.choices[0];
    if (c && c.delta && typeof c.delta.content === "string") return c.delta.content;
    if (c && c.message && typeof c.message.content === "string") return c.message.content;
    return "";
  }

  async function akisOku(res, parca) {
    const oku = res.body.getReader();
    const coz = new TextDecoder();
    let tampon = "";
    for (;;) {
      const { done, value } = await oku.read();
      if (done) break;
      tampon += coz.decode(value, { stream: true });
      let i;
      while ((i = tampon.indexOf("\n")) >= 0) {
        const satir = tampon.slice(0, i).trim();
        tampon = tampon.slice(i + 1);
        if (!satir.startsWith("data:")) continue;
        const veri = satir.slice(5).trim();
        if (!veri || veri === "[DONE]") continue;
        let j;
        try { j = JSON.parse(veri); } catch { continue; }
        const t = parcaAyikla(j);
        if (t) parca(t);
      }
    }
  }

  function hataMetni(e, res) {
    if (res) {
      if (res.status === 401 || res.status === 403) return "API anahtarı geçersiz ya da yetkisiz (HTTP " + res.status + ").";
      if (res.status === 429) return "Ücretsiz kota doldu veya çok hızlı istek (HTTP 429). Kısa bir süre bekleyip tekrar dene.";
      if (res.status === 404) return "Model bulunamadı (HTTP 404). Model adını kontrol et.";
      if (res.status >= 500) return "Model sunucusu geçici hata verdi (HTTP " + res.status + ").";
      return "Model hatası (HTTP " + res.status + ").";
    }
    const m = (e && e.message) || "";
    if (/Failed to fetch|NetworkError|load failed/i.test(m))
      return "Modele ulaşılamadı (ağ/CORS engeli veya internet yok).";
    return "Model çağrısı başarısız: " + (m || "bilinmeyen hata") + ".";
  }

  function kaynakBloku(veri) {
    const kutu = el("div", "sources");
    kutu.appendChild(el("h5", null, "📚 Cevaba temel olan bilgi bankası kayıtları"));
    (veri.kayitlar || []).slice(0, 3).forEach((k) => {
      const p = el("p", "kaynak-satir");
      p.innerHTML = "<b>" + esc(k.soru) + "</b> <span class=\"chip cat\">" + esc(k.kategori) + "</span>";
      const b = el("button", "tool", "Tamamını gör");
      b.addEventListener("click", () => soruSor(k.soru));
      p.appendChild(b);
      kutu.appendChild(p);
    });
    const src = (veri.kayitlar && veri.kayitlar[0] && veri.kayitlar[0].kaynaklar) || [];
    if (src.length) {
      kutu.appendChild(el("p", "mini", "Delil kaynakları: " + src.map(esc).join(" • ")));
    }
    return kutu;
  }

  async function llmAkisi(soru, veri) {
    const sg = saglayiciBul(LLM.saglayici);
    const wrap = el("div", "msg bot");
    wrap.appendChild(botAvatar());
    const bubble = el("div", "bubble");
    const meta = el("div", "meta");
    meta.appendChild(el("span", "chip llm", "🧠 " + esc(sg.ad.split("—")[0].split("(")[0].trim()) + " · " + esc(LLM.model)));
    meta.appendChild(el("span", "chip cat", "Bilgi bankası kaynaklı (RAG)"));
    bubble.appendChild(meta);
    if (veri.tip === "cevap" && veri.yerel && veri.yerel.soru)
      bubble.appendChild(el("p", "q-title", "Soru: <b>" + esc(soru) + "</b>"));
    const ans = el("div", "answer", '<p class="mini">🧠 Bilgi bankası taranıyor ve cevap yazılıyor…</p>');
    bubble.appendChild(ans);
    wrap.appendChild(bubble);
    chat.appendChild(wrap);
    scrollDown();

    let birikim = "";
    let sonCizim = 0;
    const ciz = (zorla) => {
      const n = performance.now();
      if (!zorla && n - sonCizim < 80) return;
      sonCizim = n;
      ans.innerHTML = markdown(birikim) + (zorla ? "" : '<span class="imlec"></span>');
      scrollDown();
    };

    let res = null;
    try {
      res = await fetch(llmUrl(sg), {
        method: "POST",
        headers: llmBasliklar(sg),
        body: JSON.stringify(llmGovde(sg, veri.kullanici_mesaji)),
      });
      if (!res.ok) {
        let govde = "";
        try { govde = (await res.text()).slice(0, 200); } catch {}
        throw new Error(hataMetni(null, res) + (govde ? " " + govde : ""));
      }
      await akisOku(res, (p) => { birikim += p; ciz(false); });
      ciz(true);
      if (!birikim.trim()) throw new Error("Model boş yanıt döndürdü.");

      bubble.appendChild(kaynakBloku(veri));
      const tools = el("div", "tools");
      const kopya = el("button", "tool", "📋 Kopyala");
      kopya.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(birikim); kopya.textContent = "✔ Kopyalandı"; }
        catch { kopya.textContent = "Kopyalanamadı"; }
        setTimeout(() => (kopya.textContent = "📋 Kopyala"), 1800);
      });
      tools.appendChild(kopya);
      const yz = el("button", "tool", "🔄 Modeli değiştir");
      yz.addEventListener("click", llmAc);
      tools.appendChild(yz);
      bubble.appendChild(tools);

      gecmis.push({ rol: "bot", veri: { bulundu: true, tip: "llm", guven: 1, kategori: sg.ad, soru: soru, cevap: birikim, kaynaklar: [], ilgili: [], notlar: [] } });
      kaydet();
    } catch (e) {
      ans.innerHTML = birikim.trim() ? markdown(birikim) : "";
      bubble.appendChild(el("div", "notlar", "⚠️ " + esc(hataMetni(e, null)) +
        " Aşağıda <b>yerel bilgi bankası</b> cevabı gösteriliyor."));
      if (veri.yerel) addBot(veri.yerel);
    }
    scrollDown();
  }

  /* ------------------------- Sunucu ile konuşma ------------------------- */
  async function soruSor(metin) {
    metin = (metin || input.value || "").trim();
    if (!metin) return;

    addUser(metin);
    input.value = "";
    autoGrow();
    sendBtn.disabled = true;
    const t = addTyping();

    try {
      const res = await fetch("/api/baglam", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ soru: metin, detay: DETAY }),
      });
      if (!res.ok) throw new Error("Sunucu hatası: " + res.status);
      const veri = await res.json();
      const yerel = veri.yerel || {};

      const ozelTip = ["guvenlik", "sohbet", "bos"].includes(veri.tip);

      // 1) Sistem içi model (varsa ve açıksa) — anahtarsız, dış servis yok
      if (!ozelTip && yerelEtkin()) {
        t.remove();
        await yerelAkisi(metin, t);
        return;
      }
      // 2) Tarayıcıdan bağlanan bulut modeli (isteğe bağlı)
      if (ozelTip || !llmAktif()) {
        t.remove();
        await sleep(160);
        addBot(yerel);
        return;
      }
      // 3) Bulut modeli: bağlamla beslenmiş cevap (akışlı)
      t.remove();
      await llmAkisi(metin, veri);
    } catch (e) {
      t.remove();
      addBot({
        bulundu: false, tip: "hata", guven: 0, kategori: "Bağlantı",
        cevap: "Sunucuya ulaşamadım. Bağlantını kontrol edip tekrar dener misin? " +
               "(Yerel bilgi bankası çevrimdışı da çalışır.)",
        kaynaklar: [], ilgili: [], notlar: [],
      });
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  /* ------------------------- Kenar çubuğu ------------------------- */
  async function kategorileriYukle() {
    try {
      const r = await fetch("/api/kategoriler");
      const d = await r.json();
      const box = $("#catList");
      box.innerHTML = "";
      d.kategoriler.forEach((k) => {
        const b = el("button", "cat", `${esc(k.kategori)} <i>${k.adet}</i>`);
        b.addEventListener("click", () => {
          $$(".cat").forEach((x) => x.classList.remove("active"));
          b.classList.add("active");
          sorulariYukle(k.kategori);
        });
        box.appendChild(b);
      });
    } catch { /* sessiz */ }
  }

  async function sorulariYukle(kategori) {
    try {
      const r = await fetch("/api/sorular" + (kategori ? `?kategori=${encodeURIComponent(kategori)}` : ""));
      const d = await r.json();
      $("#qlistTitle").textContent = kategori || "Sorular";
      const box = $("#qList");
      box.innerHTML = "";
      d.sorular.forEach((s) => {
        const b = el("button", "q-item", esc(s.soru));
        b.addEventListener("click", () => {
          soruSor(s.soru);
          if (window.innerWidth <= 980) toggleSide(false);
        });
        box.appendChild(b);
      });
    } catch { /* sessiz */ }
  }

  async function istatistikYukle() {
    try {
      const r = await fetch("/api/istatistik");
      const d = await r.json();
      $("#stats").innerHTML = `
        <div class="stat"><b>${d.toplam_kayit}</b><span>Soru-cevap kaydı</span></div>
        <div class="stat"><b>${d.kategoriler.length}</b><span>Konu başlığı</span></div>
        <div class="stat"><b>Sınırsız</b><span>Soru hakkı</span></div>
        <div class="stat"><b>0 ₺</b><span>Ücret</span></div>`;
    } catch { /* sessiz */ }
  }

  const POPULER = [
    "Namaz kaç rekât?",
    "Abdest nasıl alınır?",
    "Faizli kredi caiz mi?",
    "Orucu bozan şeyler nelerdir?",
    "Tövbe nasıl yapılır?",
    "Zekât kimlere verilir?",
    "Namaz kılmıyorum, nasıl başlarım?",
    "Müzik dinlemek caiz mi?",
    "Tesettür ölçüleri nedir?",
    "Dua kabul olmuyor, ne yapmalıyım?",
  ];

  function chipsYukle() {
    POPULER.forEach((p) => {
      const b = el("button", null, p);
      b.addEventListener("click", () => soruSor(p));
      chips.appendChild(b);
    });
  }

  async function rastgele() {
    try {
      const r = await fetch("/api/rastgele");
      const d = await r.json();
      addUser(d.soru);
      const t = addTyping();
      setTimeout(() => { t.remove(); addBot({ ...d, tip: "cevap" }); }, 320);
    } catch { /* sessiz */ }
  }

  /* ------------------------- Yardımcı: geçmiş ------------------------- */
  function kaydet() {
    try { localStorage.setItem("seyh-tugrul-gecmis", JSON.stringify(gecmis.slice(-40))); } catch {}
  }

  function yukle() {
    let kayit = [];
    try { kayit = JSON.parse(localStorage.getItem("seyh-tugrul-gecmis") || "[]"); } catch {}
    if (!kayit.length) { karsilama(); return; }
    kayit.forEach((k) => { if (k.rol === "user") addUserSessiz(k.metin); else addBotSessiz(k.veri); });
    scrollDown();
  }
  function addUserSessiz(text) {
    const wrap = el("div", "msg user");
    wrap.appendChild(el("div", "bubble", `<div class="answer">${markdown(text)}</div>`));
    wrap.appendChild(userAvatar());
    chat.appendChild(wrap);
  }
  function addBotSessiz(r) {
    if (!r) return;
    const once = gecmis.length;
    addBot(r);
    gecmis.length = once; // yükleme sırasında yeniden kaydetmeyi önle
  }

  function karsilama() {
    addBot({
      bulundu: true, tip: "sohbet", guven: 1, kategori: "Şeyh Tuğrul",
      soru: "Hoş geldiniz",
      cevap:
        "**Aleyküm selam ve rahmetullah!** 🌙\n\n" +
        "Ben **Şeyh Tuğrul** — İslami Yapay Zeka Danışmanı. Sorularını buradan **ücretsiz ve sınırsız** " +
        "sorabilirsin: kayıt yok, ücret yok, soru limiti yok.\n\n" +
        "**Şu konularda sorabilirsin:**\n" +
        "- Namaz, abdest, gusül, oruç, zekât, hac, dua, Kur'an\n" +
        "- İman esasları, kader, tevbe, âhiret, cin-şeytan, büyü\n" +
        "- Aile, nikâh, boşanma, çocuk terbiyesi, eş hakları\n" +
        "- Helâl-haram: faiz, helâl gıda, müzik, sigara, kumar, kripto\n" +
        "- Ahlâk: gıybet, yalan, öfke, sabır, anne-baba hakkı\n\n" +
        "Aşağıdaki örnek sorulardan birine dokunabilir ya da aklındakini doğrudan yazabilirsin. 🤲",
      kaynaklar: [], ilgili: [], notlar: [],
    });
    gecmis = [];
  }

  /* ------------------------- Olaylar ------------------------- */
  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 150) + "px";
  }
  input.addEventListener("input", autoGrow);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); soruSor(); }
  });
  form.addEventListener("submit", (e) => { e.preventDefault(); soruSor(); });

  $$(".seg button").forEach((b) =>
    b.addEventListener("click", () => {
      $$(".seg button").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      DETAY = b.dataset.detay;
    })
  );

  $("#clearBtn").addEventListener("click", () => {
    chat.innerHTML = "";
    gecmis = [];
    try { localStorage.removeItem("seyh-tugrul-gecmis"); } catch {}
    karsilama();
  });

  $("#randomBtn").addEventListener("click", rastgele);

  // Dil modeli paneli olayları
  const mb = $("#motorBtn"); if (mb) mb.addEventListener("click", llmAc);
  const mb2 = $("#motorBtn2"); if (mb2) mb2.addEventListener("click", llmAc);
  const kapat = $("#llmKapat"); if (kapat) kapat.addEventListener("click", llmKapat);
  const mmodal = $("#llmModal");
  if (mmodal) mmodal.addEventListener("click", (e) => { if (e.target === mmodal) llmKapat(); });

  const yerelKullan = $("#yerelKullan");
  if (yerelKullan) yerelKullan.addEventListener("change", () => {
    try { localStorage.setItem("seyh-tugrul-yerel-kullan", yerelKullan.checked ? "1" : "0"); } catch {}
    yerelRozet();
  });
  const yerelYenile = $("#yerelYenile");
  if (yerelYenile) yerelYenile.addEventListener("click", async () => {
    const d = $("#yerelDurum");
    if (d) d.textContent = "aranıyor…";
    await yerelDurumYukle(true);
  });
  const yerelKurulum = $("#yerelKurulum");
  if (yerelKurulum) yerelKurulum.addEventListener("click", () => {
    const k = $("#yerelKomut");
    if (k) k.hidden = !k.hidden;
  });

  const kaydetBtn = $("#llmKaydet");
  if (kaydetBtn) kaydetBtn.addEventListener("click", () => {
    const id = $("#llmSaglayici").value;
    const durum = $("#llmDurum");
    if (id === "yerel") {
      LLM = null; llmYaz(); motorRozeti();
      durum.textContent = "✔ Yerel bilgi bankası kullanılıyor (ücretsiz, kotasız).";
      setTimeout(llmKapat, 700);
      return;
    }
    const sg = saglayiciBul(id);
    const model = $("#llmModel").value.trim() || (sg.modeller || [])[0] || "";
    const anahtar = $("#llmAnahtar").value.trim();
    const url = $("#llmUrl").value.trim() || sg.url;
    if (!model) { durum.textContent = "⚠️ Model adı gerekli."; return; }
    if (!anahtar && id !== "ollama") { durum.textContent = "⚠️ API anahtarı gerekli (yalnızca yerel Ollama istemez)."; return; }
    if (!url) { durum.textContent = "⚠️ Sunucu adresi gerekli."; return; }
    LLM = { saglayici: id, anahtar, model, url };
    llmYaz(); motorRozeti();
    durum.textContent = "✔ Kaydedildi: " + model + " — sonraki sorular bu modelle cevaplanacak.";
    setTimeout(llmKapat, 900);
  });

  const yerelBtn = $("#llmYerel");
  if (yerelBtn) yerelBtn.addEventListener("click", () => {
    LLM = null; llmYaz(); motorRozeti();
    $("#llmDurum").textContent = "✔ Yerel bilgi bankasına dönüldü.";
    formuGuncelle();
  });

  const testBtn = $("#llmTest");
  if (testBtn) testBtn.addEventListener("click", async () => {
    const durum = $("#llmDurum");
    const id = $("#llmSaglayici").value;
    if (id === "yerel") { durum.textContent = "Yerel motor zaten çalışıyor — test gerekmez."; return; }
    const sg = saglayiciBul(id);
    const gecici = { saglayici: id, anahtar: $("#llmAnahtar").value.trim(), model: $("#llmModel").value.trim(), url: $("#llmUrl").value.trim() || sg.url };
    const eski = LLM; LLM = gecici;
    durum.textContent = "⏳ Test ediliyor…";
    let toplam = 0;
    try {
      const res = await fetch(llmUrl(sg), {
        method: "POST",
        headers: llmBasliklar(sg),
        body: JSON.stringify(llmGovde(sg, "Kısaca kendini bir cümleyle tanıt.")),
      });
      if (!res.ok) throw new Error(hataMetni(null, res));
      await akisOku(res, (p) => { toplam += p.length; });
      durum.textContent = "✔ Bağlantı başarılı! (" + toplam + " karakter yanıt geldi)";
    } catch (e) {
      durum.textContent = "✘ " + hataMetni(e, null);
    } finally {
      LLM = eski;
    }
  });

  function toggleSide(open) {
    $("#sidebar").classList.toggle("open", open);
    $("#overlay").classList.toggle("show", open);
  }
  $("#openSide").addEventListener("click", () => toggleSide(true));
  $("#closeSide").addEventListener("click", () => toggleSide(false));
  $("#overlay").addEventListener("click", () => toggleSide(false));

  function hicriTarih() {
    try {
      const f = new Intl.DateTimeFormat("tr-TR-u-ca-islamic-nu-latn", { day: "numeric", month: "long", year: "numeric" });
      $("#hijri").textContent = "• " + f.format(new Date());
    } catch { /* desteklenmiyor */ }
  }

  /* ------------------------- Başlat ------------------------- */
  llmOku();
  modelBilgisiYukle();
  yerelDurumYukle();
  motorRozeti();
  hicriTarih();
  chipsYukle();
  kategorileriYukle();
  sorulariYukle();
  istatistikYukle();
  yukle();
  autoGrow();
  input.focus();
})();
