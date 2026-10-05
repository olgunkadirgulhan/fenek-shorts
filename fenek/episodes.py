"""Bölüm üretici: sitenin içeriğinden (content/course.json) her slot için bir Shorts senaryosu kurar.

Formatlar (günde 4 slot, sırayla):
  sahne  ünitenin diyaloğunu Emre ve Lena canlandırır, sonda artikel sorusu
  kelime 5 kelime kartı (emoji + artikel renkli Almanca + Türkçe)
  quiz   3 soru (artikel / anlam), 3 sn geri sayım, cevap
  av     harf tablosunda 5 saklı kelime, 10 sn geri sayım
  hata   bank/ klasöründeki elle yazılmış "tipik hata" skeçleri (varsa sahne yerine)

Her şey içerikten türetilir; kelime/cümle uydurulmaz. Aynı içerik kısa sürede tekrar etmez (history.json).
"""
import json
import os
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSE = json.loads((ROOT / 'content' / 'course.json').read_text(encoding='utf-8'))
SRC, TGT = 'tr', 'de'  # anlatım dili, öğretilen dil (kanal: tr-de)
LEVEL_WEIGHT = {'A1': 5, 'A2': 4, 'B1': 3, 'B2': 2, 'C1': 1, 'C2': 1}
ART = re.compile(r'^(der|die|das) (.+)$')
ART_COLOR = {'der': '#2F6FEB', 'die': '#E5484D', 'das': '#16A37E'}
# 6'lık döngü: ilk hafta medyan izlenme kelime 743, sahne 651, quiz 200, av 76 (format başına 4-5 video);
# güçlü formatlar ikişer kez, zayıflar bir kez. Format listesi (--format) ilk geçişten okunur.
SLOT_FORMATS = ['sahne', 'kelime', 'quiz', 'kelime', 'sahne', 'av']
LEVELS = [l.strip() for l in (os.environ.get('LEVELS') or 'A1,A2,B1').split(',')]  # kanalın hedef seviyeleri

# Açılış cümleleri: konu adı söylenmez (zaten ekranın üstünde yazıyor), kısa ve doğrudan
HOOKS = {
    'sahne': ['Almancada böyle konuşulur!', 'Bu diyaloğu ezberle!', 'Dinle ve tekrar et!'],
    'kelime': ['Beş Almanca kelime. Hazır mısın?', 'Beş kelime, otuz saniye!'],
    'quiz': ['Üç soru, üç saniye. Hazır mısın?', 'Kendini dene! Üç soru.'],
    'av': ['Bu tabloda beş Almanca kelime saklı. On saniyen var!', 'Beş kelime saklı. Kaç tanesini bulabilirsin?'],
}
SITE_CTAS = ['Tüm ünite sitede ücretsiz. Link profilde!', 'Bunun devamı sitede, ücretsiz. Link profilde!']
FOLLOW_CTAS = ['Her gün yeni Almanca video için takip et!', 'Kaç tanesini bildin? Yorumlara yaz!',
               'Bunu kaydet, yarın tekrar et!', 'Yarın yeni kelimeler var. Takip et!']
# Site açılana kadar (SITE_URL boş) siteye/markaya yönlendiren cümle kurulmaz
BRAND = bool((os.environ.get('SITE_URL') or '').strip())
CTAS = SITE_CTAS + FOLLOW_CTAS if BRAND else FOLLOW_CTAS


def noun(w):
    m = ART.match(w[TGT])
    return (m.group(1), m.group(2)) if m and not w.get('plural') else (None, None)


def pick_least_used(items, key, used, rng, weight=lambda x: 1):
    """En az kullanılan (ve en eskide kullanılan) öğeyi seç; seviye ağırlığıyla."""
    counts = {}
    for i, u in enumerate(used):
        counts[u] = (counts.get(u, (0, -1))[0] + 1, i)
    def score(x):
        c, last = counts.get(key(x), (0, -1))
        return (c, last, -weight(x) * rng.random())
    pool = sorted(items, key=score)
    best = [x for x in pool if score(x)[:2] == score(pool[0])[:2]]
    return rng.choices(best, weights=[weight(x) for x in best])[0]


def beat(who, lang, text, sub='', **st):
    return {'who': who, 'lang': lang, 'text': text, 'sub': sub, 'st': st}


def pause(sec, **st):
    return {'who': None, 'lang': None, 'text': '', 'silence': sec, 'st': st}


def up(s):
    """Türkçe büyük harf (i -> İ)."""
    return s.replace('i', 'İ').replace('ı', 'I').upper()


def lower_first(s):
    return s[:1].lower() + s[1:] if s else s


# ------------------------------------------------------------------ formatlar

def ep_sahne(unit, rng):
    t = unit['title'][SRC]
    lines = unit['lines']
    beats = [beat('fenek', SRC, rng.choice(HOOKS['sahne']).format(t=t, tl=lower_first(t)), phase='hook', fenek=True)]
    roles = {'A': 'lena', 'B': 'emre'}
    for i, ln in enumerate(lines[:8]):
        beats.append(beat(roles[ln['who']], TGT, ln[TGT], ln[SRC], phase='dialog', mood={'emre': 'happy' if i == 7 else 'neutral'}))
    nouns = [w for w in unit['words'] if noun(w)[0]]
    if nouns:
        w = rng.choice(nouns)
        art, n = noun(w)
        q = {'type': 'quiz', 'kind': 'art', 'emoji': w['emoji'], 'word': n, 'opts': ['der', 'die', 'das'], 'answer': art, 'tr': w[SRC]}
        beats += [beat('fenek', SRC, 'Bu kelimenin artikeli ne?', overlay=q, key='q', fenek=True),
                  pause(3.0, overlay=q, key='q', countdown=3, fenek=True),
                  beat('emre', TGT, w[TGT], w[SRC], overlay={**q, 'reveal': True}, key='q', sfx='ding', fenek=True, mood={'emre': 'happy'})]
    beats.append(beat('fenek', SRC, rng.choice([c for c in CTAS if 'Kaç tanesini' not in c]), overlay={'type': 'cta', 'unit': t, 'emoji': unit['emoji'], 'cefr': unit['cefr']}, key='cta', fenek=True, sfx_before='pop'))
    title = f"{t}: Almanca diyalog {unit['emoji']} | {unit['cefr']} #almanca"
    return dict(caption=[f"{up(t)}", "ALMANCA DİYALOG " + unit['emoji']], tag=f"{unit['cefr']} · ÜNİTE", title=title,
                topic=unit['id'], theme=unit['id'], poster={'emoji': unit['emoji'], 'label': unit['title'][TGT].upper()[:18]}, beats=beats,
                desc=f"{t} ({unit['cefr']}) ünitesinden Almanca diyalog. Türkçe altyazılı, sesli.")


def ep_kelime(pack, rng):
    t = pack['title'][SRC]
    words = rng.sample(pack['words'], min(5, len(pack['words'])))
    beats = [beat('fenek', SRC, rng.choice(HOOKS['kelime']).format(t=t, tl=lower_first(t)), phase='hook', fenek=True)]
    for i, w in enumerate(words):
        art, n = noun(w)
        card = {'type': 'card', 'emoji': w['emoji'], 'de': w[TGT], 'art': art, 'noun': n, 'tr': w[SRC], 'i': i + 1, 'n': len(words)}
        who = 'lena' if i % 2 == 0 else 'emre'
        beats += [beat(who, TGT, w[TGT], '', overlay=card, key=f'c{i}', sfx_before='whoosh', nosub=True),
                  beat('fenek', SRC, w[SRC], '', overlay=card, key=f'c{i}', fenek=True, nosub=True)]
    beats.append(beat('fenek', SRC, rng.choice(CTAS), overlay={'type': 'cta', 'unit': t, 'emoji': pack['emoji'], 'cefr': pack['cefr']}, key='cta', fenek=True, sfx_before='pop'))
    return dict(caption=[f"5 ALMANCA KELİME", f"{up(t)} {pack['emoji']}"], tag=f"{pack['cefr']} · KELİME", topic=pack['id'], theme='study', poster={'emoji': pack['emoji'], 'label': pack['title'][TGT].upper()[:18]},
                title=f"5 Almanca kelime: {t} {pack['emoji']} | {pack['cefr']} #almanca", beats=beats,
                desc=f"{t} konusunda 5 Almanca kelime ({pack['cefr']}). Artikelleriyle, sesli ve Türkçe anlamlarıyla.")


def ep_quiz(pack, rng):
    t = pack['title'][SRC]
    pool = pack['words'][:]
    rng.shuffle(pool)
    nouns = [w for w in pool if noun(w)[0]]
    qs = []
    for kind in ('art', 'mean', 'art' if len(nouns) > 1 else 'mean'):
        cand = [w for w in (nouns if kind == 'art' else pool) if w not in [q['w'] for q in qs]]
        if not cand:
            continue
        w = cand[0]
        if kind == 'art':
            art, n = noun(w)
            qs.append({'w': w, 'q': {'type': 'quiz', 'kind': 'art', 'emoji': w['emoji'], 'word': n, 'opts': ['der', 'die', 'das'], 'answer': art, 'tr': w[SRC]}})
        else:
            same = [x for x in pool if x is not w and x[SRC] != w[SRC] and bool(noun(x)[0]) == bool(noun(w)[0])]
            wrong = rng.sample(same if len(same) >= 2 else [x for x in pool if x is not w and x[SRC] != w[SRC]], 2)
            opts = [w[SRC]] + [x[SRC] for x in wrong]
            rng.shuffle(opts)
            qs.append({'w': w, 'q': {'type': 'quiz', 'kind': 'mean', 'emoji': '❓', 'word': w[TGT], 'opts': opts, 'answer': w[SRC], 'tr': w[SRC]}})
    beats = [beat('fenek', SRC, rng.choice(HOOKS['quiz']).format(t=t, tl=lower_first(t)), phase='hook', fenek=True)]
    for i, item in enumerate(qs):
        q, w = dict(item['q'], i=i + 1, n=len(qs)), item['w']
        ask = 'Artikeli ne?' if q['kind'] == 'art' else 'Bu kelime ne demek?'   # soru numarası kartta yazıyor, söylenmez
        beats += [beat('fenek', SRC, ask, overlay=q, key=f'q{i}', fenek=True, sfx_before='whoosh', nosub=True)]
        if q['kind'] == 'mean':
            beats.append(beat('lena', TGT, w[TGT], '', overlay=q, key=f'q{i}', fenek=True, nosub=True))
        beats.append(pause(3.0, overlay=q, key=f'q{i}', countdown=3, fenek=True))
        if q['kind'] == 'mean':
            # kelimeyi Lena zaten söyledi: cevabı Fenek Türkçe verir (aynı kelime iki kez duyulmasın)
            beats.append(beat('fenek', SRC, f"Cevap: {w[SRC]}!", '', overlay={**q, 'reveal': True}, key=f'q{i}', sfx='ding', fenek=True, nosub=True, mood={'emre': 'happy'}))
        else:
            beats.append(beat('emre', TGT, w[TGT], w[SRC], overlay={**q, 'reveal': True}, key=f'q{i}', sfx='ding', fenek=True, mood={'emre': 'happy'}))
    beats.append(beat('fenek', SRC, rng.choice(CTAS), overlay={'type': 'cta', 'unit': t, 'emoji': pack['emoji'], 'cefr': pack['cefr']}, key='cta', fenek=True, sfx_before='pop'))
    return dict(caption=['ALMANCA QUIZ 🤔', f"{up(t)}"], tag=f"{pack['cefr']} · QUIZ", topic=pack['id'], theme='study', poster={'emoji': pack['emoji'], 'label': pack['title'][TGT].upper()[:18]},
                title=f"Almanca quiz: {t} 🤔 3 soruda kendini dene! | {pack['cefr']}", beats=beats,
                desc=f"{t} ({pack['cefr']}) üzerine 3 soruluk Almanca quiz. Kaç doğru yaptın? Yorumlara yaz!")


HUNT_FILL = 'ABCDEFGHIJKLMNOPRSTUVWZÄÖÜ'


def hunt_word(w):
    art, n = noun(w)
    s = (n or w[TGT]).upper()
    return re.sub(r'[^A-ZÄÖÜ]', '', s.replace('ß', 'SS'))


def make_grid(words, rng, size=8):
    grid = [[''] * size for _ in range(size)]
    placed = []
    dirs = [(0, 1), (1, 0), (1, 1)]
    for wd in words:
        for _ in range(300):
            dr, dc = rng.choice(dirs)
            r = rng.randrange(size - (len(wd) - 1) * dr)
            c = rng.randrange(size - (len(wd) - 1) * dc)
            cells = [(r + k * dr, c + k * dc) for k in range(len(wd))]
            if all(grid[a][b] in ('', wd[k]) for k, (a, b) in enumerate(cells)):
                for k, (a, b) in enumerate(cells):
                    grid[a][b] = wd[k]
                placed.append(cells)
                break
        else:
            return None
    for a in range(size):
        for b in range(size):
            grid[a][b] = grid[a][b] or rng.choice(HUNT_FILL[:23])
    return [''.join(r) for r in grid], placed


def ep_av(pack, rng):
    t = pack['title'][SRC]
    cands = [w for w in pack['words'] if 3 <= len(hunt_word(w)) <= 8]
    for _ in range(40):
        ws = rng.sample(cands, min(5, len(cands)))
        g = make_grid([hunt_word(w) for w in ws], rng)
        if g:
            break
    else:
        raise RuntimeError(f'grid failed for {pack["id"]}')
    grid, cells = g
    words = [{'w': hunt_word(w), 'de': w[TGT], 'tr': w[SRC], 'emoji': w['emoji'], 'cells': c} for w, c in zip(ws, cells)]
    base = {'type': 'grid', 'grid': grid, 'words': words}
    beats = [beat('fenek', SRC, rng.choice(HOOKS['av']), overlay={**base, 'found': 0}, key='g', fenek=True),
             pause(10.0, overlay={**base, 'found': 0}, key='g', countdown=10, fenek=False)]
    for i, w in enumerate(words):
        who = 'lena' if i % 2 == 0 else 'emre'
        beats.append(beat(who, TGT, w['de'], w['tr'], overlay={**base, 'found': i + 1}, key='g', sfx_before='pop'))
    beats.append(beat('fenek', SRC, 'Kaç tanesini buldun? Yorumlara yaz!', overlay={**base, 'found': len(words)}, key='g', fenek=True))
    beats.append(beat('fenek', SRC, rng.choice([c for c in CTAS if 'Yorumlara' not in c]), overlay={'type': 'cta', 'unit': t, 'emoji': pack['emoji'], 'cefr': pack['cefr']}, key='cta', fenek=True, sfx_before='pop'))
    return dict(caption=['5 KELİME SAKLI 🔍', '10 SANİYEN VAR!'], tag=f"{pack['cefr']} · KELİME AVI", topic=pack['id'], theme='study', poster={'emoji': pack['emoji'], 'label': pack['title'][TGT].upper()[:18]},
                title=f"Bu tabloda 5 Almanca kelime saklı 🔍 Bulabilir misin? | {t}", beats=beats,
                desc=f"Kelime avı: {t} ({pack['cefr']}). Harf tablosunda saklı 5 Almanca kelimeyi 10 saniyede bul!")


def ep_bank(item):
    return dict(item, beats=item['beats'])


# ------------------------------------------------------------------ seçim

def make_episode(slot, hist, seed):
    rng = random.Random(seed)
    used = [h['topic'] for h in hist.get('recent', []) if h.get('topic')]
    fmt = SLOT_FORMATS[slot % len(SLOT_FORMATS)]
    bank_dir = ROOT / 'bank'
    if fmt == 'sahne' and bank_dir.exists():
        done = set(hist.get('bank_used', []))
        fresh = sorted(p for p in bank_dir.glob('*.json') if p.stem not in done)
        if fresh and rng.random() < 0.5:
            item = json.loads(fresh[0].read_text(encoding='utf-8'))
            ep = dict(item, format='hata', bank_id=fresh[0].stem)
            return ep
    lw = lambda x: LEVEL_WEIGHT.get(x['cefr'], 1)
    if fmt == 'sahne':
        unit = pick_least_used([u for u in COURSE['units'] if u['cefr'] in LEVELS], lambda u: u['id'], used, rng, lw)
        ep = ep_sahne(unit, rng)
    else:
        packs = [p for p in COURSE['packs'] if len(p['words']) >= 8 and p['cefr'] in LEVELS]
        pack = pick_least_used(packs, lambda p: p['id'], used, rng, lw)
        ep = {'kelime': ep_kelime, 'quiz': ep_quiz, 'av': ep_av}[fmt](pack, rng)
    ep['format'] = fmt
    return ep
