// Kare kare yakalama (headless Chrome, CDP) + ffmpeg -> video.mp4
// Kullanım: node render/render.mjs <bölüm klasörü> [önizleme saniyeleri...]
// Klasörde: scene.html, cast.js, ep.js, track.wav
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const dir = path.resolve(process.argv[2]);
const previews = process.argv.slice(3).map(Number);
const FPS = Number(process.env.FPS || 30);
const CHROME = process.env.CHROME || (process.platform === "win32"
  ? ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"].find(p => fs.existsSync(p))
  : ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"].find(p => fs.existsSync(p)));
const FFMPEG = process.env.FFMPEG || "ffmpeg";

const port = 9300 + Math.floor(Math.random() * 600);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "fenek-chrome-"));
const proc = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
  "--force-device-scale-factor=1", "--allow-file-access-from-files", "--disable-dev-shm-usage", `--user-data-dir=${profile}`, "about:blank"]);
let chromeErr = "";
proc.stderr.on("data", d => { chromeErr = (chromeErr + d).slice(-2000); });
proc.on("exit", code => { if (code) console.error(`chrome çıktı (kod ${code}):\n${chromeErr}`); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let list;
for (let i = 0; i < 240 && !list; i++) { await sleep(250); try { list = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch {} }   // 60 sn'ye kadar bekle
if (!list || !list.find(p => p.type === "page")) { console.error(`Chrome açılmadı (${CHROME}).\n${chromeErr}`); process.exit(3); }
const ws = new WebSocket(list.find(p => p.type === "page").webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pend = {}; const errors = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend[m.id]) { pend[m.id](m); delete pend[m.id]; } if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text); };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.result.value;

await send("Runtime.enable"); await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1080, height: 1920, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: "file://" + (process.platform === "win32" ? "/" : "") + path.join(dir, "scene.html").replace(/\\/g, "/") + "?capture" });
await sleep(1500);
await ev("document.fonts.ready.then(() => true)");
await sleep(300);
const total = await ev("EP.total");
const shot = async (t, file, fmt) => {
  await ev(`seek(${t}); true`);
  const r = await send("Page.captureScreenshot", { format: fmt, ...(fmt === "jpeg" ? { quality: 92 } : {}), clip: { x: 0, y: 0, width: 1080, height: 1920, scale: 1 } });
  fs.writeFileSync(file, Buffer.from(r.result.data, "base64"));
};

let status = 0;
if (previews.length) {
  for (const t of previews) await shot(t, path.join(dir, `preview_${String(t).replace(".", "_")}.png`), "png");
  console.log(`previews ok (${total}s)`);
} else {
  const fdir = path.join(dir, "frames");
  fs.rmSync(fdir, { recursive: true, force: true }); fs.mkdirSync(fdir);
  const n = Math.ceil(total * FPS);
  for (let f = 0; f < n; f++) {
    await shot(f / FPS, path.join(fdir, `f${String(f).padStart(5, "0")}.jpg`), "jpeg");
    if (f % 300 === 0) console.log(`[render] frame ${f}/${n}`);
  }
  const r = spawnSync(FFMPEG, ["-y", "-v", "error", "-framerate", String(FPS), "-i", path.join(fdir, "f%05d.jpg"), "-i", path.join(dir, "track.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
    path.join(dir, "video.mp4")], { stdio: "inherit" });
  status = r.status ?? 1;
  if (status === 0) fs.rmSync(fdir, { recursive: true, force: true });
  // küçük resim: CTA'dan önceki ilk sahnenin 1. saniyesi
  await shot(Math.min(1.2, total), path.join(dir, "thumb.png"), "png");
}
if (errors.length) { console.error("page errors:", errors); status = status || 2; }
ws.close(); proc.kill();
await sleep(800);
try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(status);
