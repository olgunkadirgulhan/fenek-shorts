// Fenek Shorts karakterleri: Emre (öğrenen), Lena (yerli), Fenek (tilki maskot) + sahne dekoru. Saf SVG, telifsiz.
const W = 1080, H = 1920, INK = "#1B1F3B", S = 7;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const ease = x => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
const pop = x => { x = clamp(x, 0, 1); return x < .7 ? ease(x / .7) * 1.12 : 1.12 - .12 * ((x - .7) / .3); };
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

/* ---------- ortak yüz parçaları ---------- */
function eyes(x, y, o) {
  const gap = 46, bl = o.blink;
  let s = "";
  [-1, 1].forEach(d => {
    const ex = x + d * gap;
    if (bl) s += `<path d="M${ex - 20} ${y} q20 12 40 0" stroke="${INK}" stroke-width="${S}" fill="none" stroke-linecap="round"/>`;
    else {
      s += `<ellipse cx="${ex}" cy="${y}" rx="${o.rx || 22}" ry="${o.ry || 27}" fill="#fff" stroke="${INK}" stroke-width="5"/>`;
      s += `<circle cx="${ex + (o.look || 0)}" cy="${y + 4 + (o.lookY || 0)}" r="11" fill="${INK}"/><circle cx="${ex + (o.look || 0) + 4}" cy="${y}" r="4" fill="#fff"/>`;
    }
  });
  return s;
}
function brows(x, y, mood) {
  const m = { nervous: [8, -8], confident: [-10, 10], sad: [12, -12], happy: [-4, 4], neutral: [0, 0], angry: [-14, 14] }[mood] || [0, 0];
  return [-1, 1].map((d, i) => {
    const ex = x + d * 46, tilt = d < 0 ? m[0] : m[1];
    return `<path d="M${ex - 24} ${y + (d < 0 ? tilt : -tilt) * .5} L${ex + 24} ${y - (d < 0 ? tilt : -tilt) * .5}" stroke="${INK}" stroke-width="10" stroke-linecap="round"/>`;
  }).join("");
}
function mouth(x, y, mood, open) {
  if (open) return `<ellipse cx="${x}" cy="${y + 4}" rx="${mood === "happy" ? 34 : 24}" ry="${mood === "happy" ? 26 : 18}" fill="#7A1F2B" stroke="${INK}" stroke-width="${S}"/><ellipse cx="${x}" cy="${y + 16}" rx="12" ry="6" fill="#F28BA0"/>`;
  if (mood === "happy") return `<path d="M${x - 40} ${y - 6} Q${x} ${y + 48} ${x + 40} ${y - 6} Z" fill="#7A1F2B" stroke="${INK}" stroke-width="${S}" stroke-linejoin="round"/>`;
  if (mood === "sad") return `<path d="M${x - 28} ${y + 16} Q${x} ${y - 12} ${x + 28} ${y + 16}" stroke="${INK}" stroke-width="${S}" fill="none" stroke-linecap="round"/>`;
  if (mood === "nervous") return `<path d="M${x - 26} ${y + 6} q9 -9 17 0 t17 0 t17 0" stroke="${INK}" stroke-width="6" fill="none" stroke-linecap="round"/>`;
  if (mood === "confident") return `<path d="M${x - 30} ${y} Q${x + 5} ${y + 22} ${x + 34} ${y - 10}" stroke="${INK}" stroke-width="${S}" fill="none" stroke-linecap="round"/>`;
  return `<path d="M${x - 24} ${y} Q${x} ${y + 20} ${x + 24} ${y}" stroke="${INK}" stroke-width="${S}" fill="none" stroke-linecap="round"/>`;
}
const limb = (x1, y1, x2, y2) => `<path d="M${x1} ${y1} L${x2} ${y2}" stroke="${INK}" stroke-width="11" stroke-linecap="round"/>`;
const hand = (x, y, c) => `<circle cx="${x}" cy="${y}" r="17" fill="${c}" stroke="${INK}" stroke-width="6"/>`;

/* ---------- Emre (öğrenen) ---------- */
function emre(x, t, o) {
  const skin = "#F6C9A2", hood = "#14B8A6";
  const jump = o.jump ? Math.abs(Math.sin(t * 9)) * 34 : 0;
  const y = -(Math.sin(t * 2.3) * 5) - jump;
  const hy = 820;
  let a;
  if (o.mood === "confident") a = [[x - 150, 1110], [x + 175, 850]];
  else if (o.mood === "happy") a = [[x - 165, 880], [x + 165, 880]];
  else if (o.mood === "sad") a = [[x - 110, 1170], [x + 110, 1170]];
  else if (o.mood === "nervous") a = [[x - 40, 1095], [x + 40, 1095]];
  else a = [[x - 135, 1135], [x + 135, 1135]];
  let s = `<g transform="translate(0 ${y})">`;
  s += limb(x - 34, 1185, x - 52, 1428) + limb(x + 34, 1185, x + 52, 1428);
  s += `<ellipse cx="${x - 64}" cy="${1438}" rx="44" ry="20" fill="#E4572E" stroke="${INK}" stroke-width="6"/><ellipse cx="${x + 64}" cy="${1438}" rx="44" ry="20" fill="#E4572E" stroke="${INK}" stroke-width="6"/>`;
  s += limb(x - 78, 990, a[0][0], a[0][1]) + limb(x + 78, 990, a[1][0], a[1][1]);
  s += `<rect x="${x - 92}" y="950" width="184" height="250" rx="34" fill="${hood}" stroke="${INK}" stroke-width="${S}"/>`;
  s += `<path d="M${x - 50} 1110 h100 v44 q-50 18 -100 0 Z" fill="#0E9384" stroke="${INK}" stroke-width="5"/>`;
  s += `<path d="M${x - 22} 962 v52 M${x + 22} 962 v52" stroke="#fff" stroke-width="7" stroke-linecap="round"/>`;
  s += hand(a[0][0], a[0][1], skin) + hand(a[1][0], a[1][1], skin);
  s += `<circle cx="${x}" cy="${hy}" r="118" fill="${skin}" stroke="${INK}" stroke-width="${S}"/>`;
  // diken saç
  let p = `M${x - 118} ${hy - 12}`;
  const spikes = 7;
  for (let i = 0; i <= spikes; i++) {
    const ang = Math.PI + (i / spikes) * Math.PI, r1 = 126, r2 = 176;
    const bx = x + Math.cos(ang) * r1, by = hy + Math.sin(ang) * r1;
    if (i > 0) { const ma = ang - Math.PI / spikes / 2; p += ` L${x + Math.cos(ma) * r2} ${hy + Math.sin(ma) * r2 - 10}`; }
    p += ` L${bx} ${by}`;
  }
  s += `<path d="${p} Q${x} ${hy - 70} ${x - 118} ${hy - 12} Z" fill="#1F1F2E" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/>`;
  s += brows(x, hy - 58, o.mood);
  s += eyes(x, hy - 8, { blink: o.blink, look: o.look || 0 });
  s += [[-78, 44], [-64, 58], [-90, 60], [78, 44], [64, 58], [90, 60]].map(([dx, dy]) => `<circle cx="${x + dx}" cy="${hy + dy}" r="5" fill="#C9774F"/>`).join("");
  s += mouth(x, hy + 58, o.mood, o.talk);
  if (o.mood === "nervous") s += `<path d="M${x + 128} ${hy - 70} q16 30 0 44 q-16 -14 0 -44 Z" fill="#7CC7F5" stroke="${INK}" stroke-width="4"/>`;
  if (o.mood === "sad") s += `<path d="M${x - 70} ${hy + 20} q10 26 0 36 q-10 -10 0 -36 Z" fill="#7CC7F5" stroke="${INK}" stroke-width="4"/>`;
  if (o.mood === "happy") s += [[-170, -120], [165, -140], [0, -215]].map(([dx, dy], i) => star(x + dx, hy + dy, 20 + 6 * Math.sin(t * 8 + i), "#FFC93C")).join("");
  return s + "</g>";
}
function star(x, y, r, c) {
  let p = "";
  for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * .45 : r; p += (i ? "L" : "M") + (x + Math.cos(a) * rr) + " " + (y + Math.sin(a) * rr); }
  return `<path d="${p}Z" fill="${c}" stroke="${INK}" stroke-width="4" stroke-linejoin="round"/>`;
}

/* ---------- Lena (garson) ---------- */
function lena(x, t, o) {
  const skin = "#B97A56", hy = 790;
  const y = -(Math.sin(t * 2 + 1) * 4);
  const wave = o.talk ? Math.sin(t * 7) * 18 : 0;
  let s = `<g transform="translate(0 ${y})">`;
  // at kuyruğu
  const sw = Math.sin(t * 2.5) * 10;
  s += `<path d="M${x + 70} ${hy - 110} q${120 + sw} 20 ${95 + sw} 170 q-40 -30 -60 -70 Z" fill="#E0552B" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/>`;
  s += limb(x - 78, 975, x - 150, 1075) + limb(x + 78, 975, x + 150 + wave, 900 - wave);
  s += `<path d="M${x - 88} 940 h176 l34 260 h-244 Z" fill="#3B6FE0" stroke="${INK}" stroke-width="${S}" stroke-linejoin="round"/>`;
  s += `<rect x="${x - 70}" y="990" width="140" height="190" rx="18" fill="#FFC93C" stroke="${INK}" stroke-width="6"/>`;
  s += `<path d="M${x - 70} 1000 L${x - 88} 950 M${x + 70} 1000 L${x + 88} 950" stroke="${INK}" stroke-width="6"/>`;
  s += `<rect x="${x - 40}" y="1080" width="80" height="50" rx="10" fill="#FFB020" stroke="${INK}" stroke-width="5"/>`;
  s += `<rect x="${x - 205}" y="1030" width="80" height="100" rx="8" fill="#fff" stroke="${INK}" stroke-width="5" transform="rotate(-12 ${x - 165} 1080)"/>`;
  s += `<path d="M${x - 190} 1060 h48 M${x - 190} 1080 h40 M${x - 190} 1100 h44" stroke="#9AA3B2" stroke-width="5" transform="rotate(-12 ${x - 165} 1080)"/>`;
  s += hand(x - 150, 1075, skin) + hand(x + 150 + wave, 900 - wave, skin);
  s += `<circle cx="${x}" cy="${hy}" r="115" fill="${skin}" stroke="${INK}" stroke-width="${S}"/>`;
  s += `<path d="M${x - 118} ${hy + 10} Q${x - 128} ${hy - 150} ${x} ${hy - 124} Q${x + 128} ${hy - 150} ${x + 118} ${hy + 10} Q${x + 70} ${hy - 70} ${x + 10} ${hy - 62} Q${x - 60} ${hy - 90} ${x - 118} ${hy + 10} Z" fill="#E0552B" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/>`;
  s += `<path d="M${x - 104} ${hy - 58} Q${x} ${hy - 150} ${x + 104} ${hy - 58}" stroke="#2A9D8F" stroke-width="16" fill="none" stroke-linecap="round"/>`;
  s += eyes(x, hy - 2, { blink: o.blink, look: o.look || -6, rx: 20, ry: 25 });
  s += [-1, 1].map(d => `<path d="M${x + d * 46 + d * 16} ${hy - 26} l${d * 12} -12" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>`).join("");
  s += `<circle cx="${x - 78}" cy="${hy + 40}" r="16" fill="#F28BA0" opacity=".7"/><circle cx="${x + 78}" cy="${hy + 40}" r="16" fill="#F28BA0" opacity=".7"/>`;
  s += mouth(x, hy + 55, o.mood, o.talk);
  if (o.hearts) s += [0, 1, 2].map(i => { const k = (t * .8 + i / 3) % 1; return `<text x="${x + 140 + i * 30}" y="${hy - 80 - k * 160}" font-size="${44 - k * 10}" opacity="${1 - k}">💛</text>`; }).join("");
  return s + "</g>";
}

/* ---------- Fenek (tilki maskot) ---------- */
function fenek(x, y, sc, t, o) {
  const b = Math.sin(t * 3) * 6, tail = Math.sin(t * 4) * 12;
  let s = `<g transform="translate(${x} ${y + b}) scale(${sc})">`;
  s += `<path d="M60 90 q${120 + tail} -40 ${150 + tail} -170 q-10 110 -120 200 Z" fill="#F28C28" stroke="${INK}" stroke-width="${S}" stroke-linejoin="round"/>`;
  s += `<path d="M${200 + tail} -60 q${10} -30 ${10 + tail * .3} -20 q-6 50 -40 60 Z" fill="#fff" stroke="${INK}" stroke-width="5"/>`;
  s += `<ellipse cx="0" cy="110" rx="95" ry="110" fill="#F28C28" stroke="${INK}" stroke-width="${S}"/>`;
  s += `<ellipse cx="0" cy="130" rx="58" ry="80" fill="#FFF3E0"/>`;
  s += limb(-50, 210, -60, 250) + limb(50, 210, 60, 250);
  s += `<path d="M-120 -80 L-150 -250 L-40 -150 Z" fill="#F28C28" stroke="${INK}" stroke-width="${S}" stroke-linejoin="round"/><path d="M-115 -110 L-132 -205 L-70 -150 Z" fill="#FFD8B0"/>`;
  s += `<path d="M120 -80 L150 -250 L40 -150 Z" fill="#F28C28" stroke="${INK}" stroke-width="${S}" stroke-linejoin="round"/><path d="M115 -110 L132 -205 L70 -150 Z" fill="#FFD8B0"/>`;
  s += `<circle cx="0" cy="-70" r="128" fill="#F28C28" stroke="${INK}" stroke-width="${S}"/>`;
  s += `<path d="M-128 -60 Q-70 20 0 30 Q70 20 128 -60 Q90 60 0 62 Q-90 60 -128 -60 Z" fill="#FFF3E0" stroke="${INK}" stroke-width="5"/>`;
  s += eyes(0, -92, { blink: o.blink, rx: 20, ry: 26 });
  s += `<ellipse cx="0" cy="-30" rx="18" ry="13" fill="${INK}"/>`;
  s += mouth(0, 8, o.mood || "happy", o.talk);
  if (o.point) s += limb(80, 90, 190, -20) + hand(190, -20, "#F28C28");
  return s + "</g>";
}

/* ---------- arka plan: kafe ---------- */
const THEMES = {
  cafe: ["#CDEBDD", "#C0E3D3", "menu"], restaurant: ["#F6E3C8", "#EFD6B4", "menu"], cooking: ["#FBE3D6", "#F5D2C0", "menu"],
  study: ["#E3E4F8", "#D6D8F2", "poster"], default: ["#DDEBF7", "#CEE0F1", "poster"],
};
function background(t, theme, poster) {
  const [wall, stripe, deco] = THEMES[theme] || THEMES.default;
  let s = `<rect width="${W}" height="${H}" fill="${wall}"/>`;
  s += Array.from({ length: 9 }, (_, i) => `<rect x="${i * 130 - 20}" y="0" width="65" height="1240" fill="${stripe}"/>`).join("");
  if (deco !== "menu") {
    s += `<g transform="rotate(2 800 530)"><rect x="640" y="420" width="320" height="215" rx="18" fill="#FFF7E6" stroke="${INK}" stroke-width="8"/>`;
    s += `<text x="800" y="545" text-anchor="middle" font-size="105">${poster ? poster.emoji : "📚"}</text>`;
    s += `<text x="800" y="612" text-anchor="middle" class="cap" font-size="34" fill="${INK}">${esc(poster ? poster.label : "DEUTSCH")}</text></g>`;
  }
  s += `<rect y="1240" width="${W}" height="${H - 1240}" fill="#C9956A"/><rect y="1240" width="${W}" height="18" fill="#A87850"/>`;
  s += Array.from({ length: 6 }, (_, i) => `<path d="M${i * 200} 1258 L${i * 200 - 120} ${H}" stroke="#B9855B" stroke-width="6"/>`).join("");
  // menü tahtası
  if (deco === "menu") s += `<g transform="rotate(-2 800 560)"><rect x="620" y="440" width="360" height="250" rx="16" fill="#2E3B35" stroke="#7A5234" stroke-width="16"/>`
    + `<text x="800" y="500" text-anchor="middle" fill="#fff" class="cap" font-size="40">MENÜ</text>`
    + `<text x="650" y="560" fill="#F7E7C6" font-size="34" font-weight="800">Kaffee ....... 3 €</text><text x="650" y="610" fill="#F7E7C6" font-size="34" font-weight="800">Kuchen ...... 4 €</text><text x="650" y="660" fill="#F7E7C6" font-size="34" font-weight="800">Tee ........... 2 €</text></g>`;
  // pencere + bitki
  s += `<rect x="70" y="470" width="250" height="230" rx="14" fill="#FFF7E6" stroke="${INK}" stroke-width="8"/><path d="M195 470 v230 M70 585 h250" stroke="${INK}" stroke-width="7"/><circle cx="265" cy="525" r="26" fill="#FFD166"/>`;
  s += `<rect x="40" y="1130" width="90" height="110" rx="12" fill="#E4572E" stroke="${INK}" stroke-width="6"/>` + [[-30, -60], [0, -95], [30, -60], [-10, -40], [20, -40]].map(([dx, dy]) => `<ellipse cx="${85 + dx}" cy="${1130 + dy}" rx="26" ry="48" fill="#2A9D8F" stroke="${INK}" stroke-width="5" transform="rotate(${dx} ${85 + dx} ${1130 + dy})"/>`).join("");
  return s;
}
function counter(t, showCake, showReceipt, recT) {
  let s = `<rect x="530" y="1150" width="560" height="300" rx="10" fill="#8A5A3B" stroke="${INK}" stroke-width="${S}"/><rect x="515" y="1125" width="590" height="42" rx="12" fill="#B07A52" stroke="${INK}" stroke-width="${S}"/>`;
  s += `<path d="M560 1220 h500 M560 1300 h500 M560 1380 h500" stroke="#7A4E32" stroke-width="6"/>`;
  // kahve makinesi
  s += `<rect x="930" y="960" width="130" height="170" rx="16" fill="#9AA3B2" stroke="${INK}" stroke-width="6"/><rect x="955" y="990" width="80" height="40" rx="8" fill="#1B1F3B"/><circle cx="995" cy="1080" r="12" fill="#E4572E" stroke="${INK}" stroke-width="4"/>`;
  s += `<rect x="600" y="1068" width="70" height="62" rx="10" fill="#fff" stroke="${INK}" stroke-width="6"/><path d="M670 1085 q26 6 0 30" stroke="${INK}" stroke-width="6" fill="none"/>`;
  s += [0, 1].map(i => { const k = (t * .6 + i / 2) % 1; return `<path d="M${622 + i * 24} ${1060 - k * 70} q10 -14 0 -28" stroke="#fff" stroke-width="6" fill="none" opacity="${1 - k}" stroke-linecap="round"/>`; }).join("");
  if (showCake) s += `<g transform="translate(720 1062)"><path d="M0 60 L90 60 L90 20 Z" fill="#F7D6A0" stroke="${INK}" stroke-width="6"/><path d="M0 60 L90 20" stroke="#F28BA0" stroke-width="12"/><circle cx="78" cy="10" r="10" fill="#E4572E" stroke="${INK}" stroke-width="4"/></g>`;
  if (showReceipt) {
    const k = pop(recT / .35);
    s += `<g transform="translate(650 1165) scale(${k * .8}) rotate(-4)"><path d="M0 0 h300 v330 l-25 -18 l-25 18 l-25 -18 l-25 18 l-25 -18 l-25 18 l-25 -18 l-25 18 l-25 -18 l-25 18 l-25 -18 l-25 18 Z" fill="#fff" stroke="${INK}" stroke-width="6"/>`;
    s += `<text x="150" y="58" text-anchor="middle" class="cap" font-size="40" fill="${INK}">RECHNUNG</text>`;
    s += `<text x="30" y="130" font-size="34" font-weight="800" fill="${INK}">Kaffee</text><text x="270" y="130" text-anchor="end" font-size="34" font-weight="800" fill="${INK}">3,00</text>`;
    s += `<text x="30" y="185" font-size="34" font-weight="800" fill="${INK}">Kuchen</text><text x="270" y="185" text-anchor="end" font-size="34" font-weight="800" fill="${INK}">4,00</text>`;
    s += `<path d="M30 215 h240" stroke="${INK}" stroke-width="4" stroke-dasharray="10 8"/><text x="30" y="270" class="cap" font-size="40" fill="#E4572E">SUMME</text><text x="270" y="270" text-anchor="end" class="cap" font-size="40" fill="#E4572E">7 €</text></g>`;
  }
  return s;
}

