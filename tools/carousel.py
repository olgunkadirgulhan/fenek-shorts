"""Günlük kaydırmalı gönderi (Instagram / TikTok fotoğraf modu) → Telegram'a albüm + hazır açıklamalar.

Senaryo içerikten üretilir (content/course.json): 1 konu → kapak, 3 kelime, 3 cümle, mini quiz, cevap = 9 slayt.
Aynı konu art arda gelmez, aynı cümle 90 gün tekrar etmez (carousel_history.json).
    python tools/carousel.py            # bugünkü gönderi (bugün zaten gönderildiyse atlar)
    python tools/carousel.py --force    # yine de üret
    python tools/carousel.py --no-send  # sadece üret (output/carousel/...)
"""
import argparse
import html
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fenek import notify  # noqa: E402

COURSE = json.loads((ROOT / 'content' / 'course.json').read_text(encoding='utf-8'))
HIST = ROOT / 'carousel_history.json'
SRC, TGT = 'tr', 'de'
LEVELS = [l.strip() for l in (os.environ.get('LEVELS') or 'A1,A2,B1').split(',')]
ART = re.compile(r'^(der|die|das) (.+)$')
HOOKS = ['3 kelime + 3 cümle', 'bunları mutlaka bil!', 'en çok lazım olanlar', '1 dakikada öğren']


def is_noun(w):
    return bool(ART.match(w[TGT])) and not w.get('plural')


def highlight(sentence, words):
    """Cümlede geçen öğrenilen kelimeleri kalın/turuncu yap."""
    out = html.escape(sentence)
    for w in words:
        core = ART.sub(r'\2', w[TGT]).strip()
        if len(core) >= 3:
            out = re.sub(rf'(?i)\b({re.escape(html.escape(core))}\w*)', r'<b>\1</b>', out, count=1)
    return out


def build(hist, rng):
    units = [u for u in COURSE['units'] if u['cefr'] in LEVELS and len(u['lines']) >= 3 and len(u['words']) >= 4]
    used = [h['unit'] for h in hist.get('days', [])]
    last = used[-1] if used else None
    # en az kullanılan konu (dünküyle aynı olmasın)
    cand = sorted((u for u in units if u['id'] != last), key=lambda u: (used.count(u['id']), rng.random()))
    unit = cand[0]
    used_sent = set(hist.get('sentences', [])[-400:])

    nouns = [w for w in unit['words'] if is_noun(w)]
    others = [w for w in unit['words'] if not is_noun(w)]
    rng.shuffle(nouns); rng.shuffle(others)
    # artikeller karışık olsun (der/die/das): önce her artikelden birer isim, sonra kalanlar
    words, seen_art = [], set()
    for w in nouns:
        a = ART.match(w[TGT]).group(1)
        if a not in seen_art:
            words.append(w); seen_art.add(a)
    words = (words + [w for w in nouns if w not in words] + others)[:3]

    lines = [l for l in unit['lines'] if 6 <= len(l[TGT]) <= 70 and l[TGT] not in used_sent]
    if len(lines) < 3:
        lines = [l for l in unit['lines'] if 6 <= len(l[TGT]) <= 70]
    idx = sorted(rng.sample(range(len(lines)), 3))
    sents = [lines[i] for i in idx]

    quiz_pool = [w for w in nouns if w not in words] or [w for p in COURSE['packs'] if p['cefr'] == unit['cefr'] for w in p['words'] if is_noun(w)]
    qw = rng.choice(quiz_pool)
    q_art, q_noun = ART.match(qw[TGT]).groups()

    t = unit['title'][SRC]
    slides = [{'type': 'cover', 'title': f'{t}:', 'em': rng.choice(HOOKS), 'sub': 'Almanca · Türkçe açıklamalı',
               'chips': [unit['emoji'], unit['cefr'], '🇩🇪 Deutsch']}]
    slides += [{'type': 'word', 'k': i + 1, 'emoji': w['emoji'], 'de': w[TGT], 'tr': w[SRC], 'plural': bool(w.get('plural'))} for i, w in enumerate(words)]
    slides += [{'type': 'sentence', 'k': i + 1, 'deHtml': highlight(s[TGT], words), 'tr': s[SRC]} for i, s in enumerate(sents)]
    slides += [{'type': 'quiz', 'emoji': qw['emoji'], 'noun': q_noun},
               {'type': 'answer', 'emoji': qw['emoji'], 'de': qw[TGT], 'tr': qw[SRC]}]
    return unit, words, sents, slides


def captions(unit, words, sents):
    t, lvl = unit['title'][SRC], unit['cefr']
    wl = ' · '.join(w[TGT] for w in words)
    tiktok = (f"{unit['emoji']} {t}: Almanca 3 kelime + 3 cümle\n{wl}\nArtikel sorusunu cevaba bakmadan bildin mi? Yoruma yaz 👇\n\n"
              f"#almanca #almancaöğren #almancakelimeler #almanca{lvl.lower()} #fyp")
    insta = (f"{unit['emoji']} {t}: Almanca 3 kelime + 3 cümle 🇩🇪\n\n"
             + '\n'.join(f"• {w[TGT]} = {w[SRC]}" for w in words) + "\n\n"
             + '\n'.join(f"💬 {s[TGT]}\n    {s[SRC]}" for s in sents)
             + "\n\n🤔 8. slayttaki artikel sorusunu cevaba bakmadan bildin mi? Yoruma yaz!\n📌 Kaydet, sonra tekrar et · 🔔 Her gün yeni Almanca\n\n"
             + f"#almanca #almancaöğren #almancadersi #almancakelimeler #almancacümleler #almanca{lvl.lower()} "
               "#derdiedas #deutsch #deutschlernen #almanya #almancakursu #keşfet")
    return tiktok, insta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--no-send', action='store_true')
    a = ap.parse_args()
    hist = json.loads(HIST.read_text(encoding='utf-8')) if HIST.exists() else {'days': [], 'sentences': []}
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if not a.force and any(d['date'] == today for d in hist['days']):
        print('bugünkü kaydırmalı gönderi zaten gönderildi'); return
    rng = random.Random(int(datetime.now().timestamp()))
    unit, words, sents, slides = build(hist, rng)
    out = ROOT / 'output' / 'carousel' / f"{today}-{unit['id']}"
    out.mkdir(parents=True, exist_ok=True)
    (out / 'slides.json').write_text(json.dumps({'slides': slides}, ensure_ascii=False, indent=1), encoding='utf-8')
    r = subprocess.run(['node', str(ROOT / 'render' / 'carousel.mjs'), str(out)])
    if r.returncode != 0:
        notify.message('❌ Günlük kaydırmalı gönderi üretilemedi.'); sys.exit(1)
    imgs = sorted(out.glob('slide_*.jpg'), key=lambda p: int(p.stem.split('_')[1]))
    tiktok, insta = captions(unit, words, sents)
    (out / 'captions.txt').write_text(f'TIKTOK\n{tiktok}\n\nINSTAGRAM\n{insta}\n', encoding='utf-8')
    print(f"{unit['id']}: {len(imgs)} slayt → {out}")
    if a.no_send:
        return
    ok = notify.album(imgs, f"🖼️ Günün kaydırmalı gönderisi ({len(imgs)} slayt) · {unit['emoji']} {unit['title'][SRC]} · {unit['cefr']}\n"
                            "Instagram ve TikTok'a (fotoğraf modu) sırayla yükle.")
    if ok:
        notify.copyable('🎵 TikTok açıklaması (kutuya dokun → kopyalanır):', tiktok)
        notify.copyable('📸 Instagram açıklaması (kutuya dokun → kopyalanır):', insta)
        hist['days'].append({'date': today, 'unit': unit['id'], 'words': [w[TGT] for w in words]})
        hist['sentences'] = (hist.get('sentences', []) + [s[TGT] for s in sents])[-1000:]
        HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding='utf-8')
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
