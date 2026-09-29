// Kaydırmalı gönderi (Instagram/TikTok fotoğraf modu): slides.json → slide_1.png ... (1080x1350, 4:5)
// Kullanım: node render/carousel.mjs <klasör>   (klasörde slides.json)
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const dir = path.resolve(process.argv[2]);
const spec = JSON.parse(fs.readFileSync(path.join(dir, "slides.json"), "utf8"));
const W = 1080, H = 1350;
const CHROME = process.env.CHROME || (process.platform === "win32"
  ? ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"].find(p => fs.existsSync(p))
  : ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"].find(p => fs.existsSync(p)));
const port = 9900 + Math.floor(Math.random() * 90);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "fenek-car-"));
const proc = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
  "--disable-dev-shm-usage", `--user-data-dir=${profile}`, "about:blank"]);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let list;
for (let i = 0; i < 240 && !list; i++) { await sleep(250); try { list = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch {} }
const ws = new WebSocket(list.find(p => p.type === "page").webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pend = {};
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m); delete pend[m.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result; if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 300)); return r.result?.value; };

// Sitenin tilki amblemi (site/js/app.js mascot ile aynı çizim)
const fox = size => `<svg width="${size}" height="${size}" viewBox="0 0 120 120"><polygon points="22,62 6,6 54,42" fill="#F08A3C"/><polygon points="25,53 14,18 46,42" fill="#FFD2B0"/><polygon points="98,62 114,6 66,42" fill="#F08A3C"/><polygon points="95,53 106,18 74,42" fill="#FFD2B0"/><ellipse cx="60" cy="74" rx="40" ry="34" fill="#F4A259"/><ellipse cx="60" cy="89" rx="27" ry="18" fill="#FFF4E6"/><circle cx="46" cy="67" r="6.5" fill="#2B2350"/><circle cx="74" cy="67" r="6.5" fill="#2B2350"/><circle cx="48.5" cy="64.5" r="2.2" fill="#fff"/><circle cx="76.5" cy="64.5" r="2.2" fill="#fff"/><ellipse cx="60" cy="81" rx="5.5" ry="4" fill="#2B2350"/><path d="M51 89 q9 10 18 0" stroke="#2B2350" stroke-width="3.5" fill="#E5484D" stroke-linecap="round"/><circle cx="33" cy="84" r="5" fill="#FF8C8C" opacity=".45"/><circle cx="87" cy="84" r="5" fill="#FF8C8C" opacity=".45"/></svg>`;
const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const ART = { der: "#2F6FEB", die: "#E5484D", das: "#16A37E" };
const artWord = (de) => { const m = /^(der|die|das) (.+)$/.exec(de); return m ? `<span style="color:${ART[m[1]]}">${m[1]}</span> ${esc(m[2])}` : esc(de); };

const CSS = `
html,body{margin:0;width:${W}px;height:${H}px;overflow:hidden}
.s{position:relative;width:${W}px;height:${H}px;box-sizing:border-box;padding:90px 80px;font-family:Nunito,"Noto Color Emoji",sans-serif;color:#1B1F3B;
  background:#FBF6EE;background-image:radial-gradient(#e9dfcf 2.5px,transparent 2.5px);background-size:38px 38px;display:flex;flex-direction:column}
.cap{font-family:"Baloo 2",sans-serif;font-weight:800}
.top{display:flex;justify-content:space-between;align-items:center;font-size:38px;font-weight:900}
.pill{background:var(--c,#E4572E);color:#fff;border:6px solid #1B1F3B;border-radius:18px;padding:6px 22px;box-shadow:0 7px 0 #1B1F3B}
.num{color:#9AA3B2}
.card{flex:1;margin-top:46px;background:#fff;border:9px solid #1B1F3B;border-radius:44px;box-shadow:0 16px 0 #1B1F3B;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:50px}
.emo{font-size:230px;line-height:1.1}
.de{font-size:104px;line-height:1.05;margin-top:24px}
.tr{font-size:58px;font-weight:900;color:#5B6072;margin-top:26px;padding-top:26px;border-top:6px dashed #E6E1D8;width:80%}
.hint{font-size:40px;font-weight:800;color:#9AA3B2;margin-top:22px}
.sen{font-size:78px;line-height:1.15}
.sen b{color:#E4572E}
.foot{display:flex;align-items:center;justify-content:space-between;margin-top:40px;font-size:40px;font-weight:900}
.foot .sw{color:#5B6072}
.cover{justify-content:center;text-align:center;align-items:center}
.cover h1{font-size:112px;line-height:1.02;margin:30px 0 20px}.cover h1 em{font-style:normal;color:#E4572E}
.cover .sub{font-size:52px;font-weight:900;color:#5B6072}
.chips{display:flex;gap:22px;justify-content:center;margin-top:44px}
.chip{font-size:44px;font-weight:900;padding:14px 30px;border:6px solid #1B1F3B;border-radius:22px;background:#fff;box-shadow:0 7px 0 #1B1F3B}
.opts{display:flex;gap:34px;margin-top:60px}
.opt{font-size:84px;color:#fff;border:8px solid #1B1F3B;border-radius:34px;padding:22px 44px;box-shadow:0 10px 0 #1B1F3B}
.cta{font-size:62px;line-height:1.15}.cta .big{font-size:96px;color:#E4572E}
`;

function slide(s, i, n) {
  const foot = i < n - 1 ? `<div class="foot"><span>${fox(92)}</span><span class="sw">Kaydır ➜</span></div>`
                         : `<div class="foot"><span>${fox(92)}</span><span class="sw">🔔 Takip et</span></div>`;
  const top = (label, color) => `<div class="top"><span class="pill cap" style="--c:${color}">${esc(label)}</span><span class="num cap">${i + 1}/${n}</span></div>`;
  if (s.type === "cover") return `<div class="s cover">${fox(260)}<h1 class="cap">${esc(s.title)}<br><em>${esc(s.em)}</em></h1>
    <div class="sub">${esc(s.sub)}</div><div class="chips">${s.chips.map(c => `<span class="chip cap">${esc(c)}</span>`).join("")}</div>
    <div class="sub" style="margin-top:60px">Kaydır ➜</div></div>`;
  if (s.type === "word") return `<div class="s">${top(`KELİME ${s.k}`, "#2F6FEB")}<div class="card"><div class="emo">${s.emoji}</div>
    <div class="de cap">${artWord(s.de)}</div><div class="tr">${esc(s.tr)}</div>${s.plural ? `<div class="hint">çoğul</div>` : ""}</div>${foot}</div>`;
  if (s.type === "sentence") return `<div class="s">${top(`CÜMLE ${s.k}`, "#16A37E")}<div class="card"><div class="sen cap">${s.deHtml}</div>
    <div class="tr">${esc(s.tr)}</div></div>${foot}</div>`;
  if (s.type === "quiz") return `<div class="s">${top("MİNİ QUIZ 🤔", "#8B5CF6")}<div class="card"><div class="emo" style="font-size:180px">${s.emoji}</div>
    <div class="de cap">___ ${esc(s.noun)}</div><div class="hint" style="font-size:46px">Artikeli ne? Cevabı yoruma yaz 👇</div>
    <div class="opts">${["der", "die", "das"].map(a => `<span class="opt cap" style="background:${ART[a]}">${a}</span>`).join("")}</div></div>${foot}</div>`;
  if (s.type === "answer") return `<div class="s">${top("CEVAP ✓", "#16A37E")}<div class="card"><div class="emo" style="font-size:180px">${s.emoji}</div>
    <div class="de cap">${artWord(s.de)}</div><div class="tr">${esc(s.tr)}</div>
    <div class="cta cap" style="margin-top:50px">Bildin mi? 👇<br><span class="big">Kaydet · Takip et</span></div></div>${foot}</div>`;
  throw new Error("bilinmeyen slayt: " + s.type);
}

await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
const html = `<!doctype html><html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@800&family=Nunito:wght@700;800;900&display=swap" rel="stylesheet"><style>${CSS}</style></head><body><div id="root"></div></body></html>`;
fs.writeFileSync(path.join(dir, "carousel.html"), html);
await send("Page.navigate", { url: "file://" + (process.platform === "win32" ? "/" : "") + path.join(dir, "carousel.html").replace(/\\/g, "/") });
await sleep(1500);
await ev("document.fonts.ready.then(()=>true)");
const n = spec.slides.length;
for (let i = 0; i < n; i++) {
  await ev(`document.getElementById('root').innerHTML = ${JSON.stringify(slide(spec.slides[i], i, n))}; document.fonts.ready.then(()=>true)`);
  await sleep(250);
  const r = await send("Page.captureScreenshot", { format: "jpeg", quality: 93, clip: { x: 0, y: 0, width: W, height: H, scale: 1 } });
  fs.writeFileSync(path.join(dir, `slide_${i + 1}.jpg`), Buffer.from(r.result.data, "base64"));
}
console.log(`carousel ok: ${n} slayt`);
ws.close(); proc.kill();
await sleep(500);
try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(0);
