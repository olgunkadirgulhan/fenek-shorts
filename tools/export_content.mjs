// Sitenin içerik dosyalarını (site/js/corpus*.js, vocab*.js) tek bir content/course.json'a çevirir.
// Site güncellenince çalıştır:  node tools/export_content.mjs ../site/js
import vm from "node:vm";
import fs from "node:fs";
import path from "node:path";

const src = path.resolve(process.argv[2] || "../site/js");
const out = path.resolve(path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, "$1"), "..", "content", "course.json");
const files = fs.readdirSync(src).filter(f => /^(i18n\.js|corpus\d*\.js|vocab_\w+\.js)$/.test(f))
  .sort((a, b) => (a.startsWith("i18n") ? -1 : b.startsWith("i18n") ? 1 : a.startsWith("corpus") === b.startsWith("corpus") ? a.localeCompare(b) : a.startsWith("corpus") ? -1 : 1));
const ctx = { console };
vm.createContext(ctx);
vm.runInContext(files.map(f => fs.readFileSync(path.join(src, f), "utf8")).join("\n;\n") + ";this.__o={LANGS,CORPUS,VOCAB};", ctx);
const { LANGS, CORPUS, VOCAB } = ctx.__o;
const obj = arr => Object.fromEntries(LANGS.map((l, i) => [l, arr[i]]));
const word = w => ({ emoji: w[0], ...obj(w.slice(1, 11)), plural: !!w[11] });
const data = {
  langs: LANGS,
  units: CORPUS.filter(u => !u.soon).map(u => ({
    id: u.id, cefr: u.cefr, emoji: u.emoji, title: obj(u.title),
    words: u.words.map(word),
    lines: u.lines.map(l => ({ who: l[0], ...obj(l.slice(1, 11)) })),
  })),
  packs: VOCAB.map(p => ({ id: p.id, cefr: p.cefr, emoji: p.emoji, title: obj(p.title), words: p.words.map(word) })),
};
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(data));
console.log(`content: ${data.units.length} ünite, ${data.packs.length} paket, ${data.packs.reduce((a, p) => a + p.words.length, 0)} kelime -> ${out}`);
