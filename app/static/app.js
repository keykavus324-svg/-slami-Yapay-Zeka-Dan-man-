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
      const res = await fetch("/api/sor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ soru: metin, detay: DETAY }),
      });
      if (!res.ok) throw new Error("Sunucu hatası: " + res.status);
      const data = await res.json();
      t.remove();
      // Kısa doğal "düşünme" gecikmesi
      await new Promise((r) => setTimeout(r, 260));
      addBot(data);
    } catch (e) {
      t.remove();
      addBot({
        bulundu: false, tip: "hata", guven: 0, kategori: "Bağlantı",
        cevap: "Sunucuya ulaşamadım. Bağlantını kontrol edip tekrar dener misin? " +
               "(Uygulama tamamen yerel çalışır; internet gerekmez.)",
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
  hicriTarih();
  chipsYukle();
  kategorileriYukle();
  sorulariYukle();
  istatistikYukle();
  yukle();
  autoGrow();
  input.focus();
})();
