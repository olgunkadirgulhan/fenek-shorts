"""Fenek Shorts pipeline. Bir çalıştırma = bir Shorts.

    içerik (content/course.json) -> bölüm senaryosu -> sesler (Chatterbox) + müzik/SFX -> SVG animasyon -> MP4 -> YouTube

Kullanım
  python run.py                       # sıradaki slot için 1 Shorts üret ve yükle
  python run.py --no-upload           # sadece render (output/<id>/video.mp4)
  python run.py --format quiz --no-upload
Env
  YT_PRIVACY   public | private | unlisted | off   (varsayılan: secrets varsa private)
  MAX_PER_DAY  günlük üst sınır (varsayılan 4)
  LEVELS       kanalın seviyeleri (varsayılan A1,A2,B1)
  TTS_ENGINE   chatterbox | piper
  SITE_URL     açıklamadaki site linki
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN, YT_CHANNEL_ID
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import traceback
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fenek import audio, episodes, lipsync, voice  # noqa: E402

HIST = HERE / 'history.json'
PUBLISHED = HERE / 'published.csv'
QUEUE = HERE / 'queue'
OUT = HERE / 'output'
FIELDS = ['id', 'date_utc', 'format', 'video_id', 'privacy', 'topic', 'title']
GAP = 0.3


def log(msg):
    print(f'[run] {msg}', flush=True)


def gh(level, msg):
    print(f'::{level}::{msg}' if os.environ.get('GITHUB_ACTIONS') else f'[run] {level.upper()}: {msg}', flush=True)


def rows():
    if not PUBLISHED.exists():
        return []
    with PUBLISHED.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def today_count():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return sum(1 for r in rows() if r['date_utc'].startswith(today))


def load_hist():
    return json.loads(HIST.read_text(encoding='utf-8')) if HIST.exists() else {'recent': [], 'bank_used': [], 'count': 0}


def read_wav(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(1)
        if w.getframerate() != audio.SR:
            x = audio.resample(x, w.getframerate() / audio.SR) if hasattr(audio, 'resample') else x
    return x


def build(ep, out):
    """Sesleri üretir, zamanlamayı kurar, track.wav'ı karıştırır."""
    t, voices, effects, speech = 0.4, [], [], [(0, 0)]
    for b in ep['beats']:
        st = b.setdefault('st', {})
        if st.get('sfx_before'):
            effects.append((t, audio.sfx(st['sfx_before']), 0.5))
            t += 0.22
        if b.get('silence'):
            b['t0'], b['t1'] = round(t, 3), round(t + b['silence'], 3)
            for k in range(int(b['silence'])):
                effects.append((t + k, audio.sfx('tick'), 0.45))
            t += b['silence']
        else:
            wav, dur = voice.synth(b['who'], b['lang'], b['text'])
            voices.append((t, read_wav(wav), 1.0))
            b['mouth'] = lipsync.mouth_cues(wav)                      # gerçek dudak senkronu
            if not st.get('nosub'):
                b['words'] = lipsync.word_starts(wav, b['text'], b['lang'])   # karaoke altyazı
            speech += [(t - 0.05, 1), (t + dur, 1), (t + dur + 0.2, 0)]
            if st.get('sfx') == 'ding':
                effects.append((t, audio.sfx('ding'), 0.35))
            b['t0'], b['t1'] = round(t, 3), round(t + dur, 3)
            t += dur
        t += GAP
    ep['total'] = total = round(t + 0.8, 2)
    pts = sorted(speech[1:])
    xs = [0] + [p[0] for p in pts] + [total]
    ys = [0] + [p[1] for p in pts] + [0]
    stereo = audio.mix(total, voices, effects, audio.music(total, seed=hash(ep['id']) % 1000), (np.array(xs), np.array(ys, np.float32)))
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    raw = out / 'track_raw.wav'
    with wave.open(str(raw), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(audio.SR); w.writeframes(pcm.tobytes())
    # mastering: YouTube standardı -14 LUFS, tepe -1.5 dB (videolar arası ses seviyesi eşit)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(raw), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9', '-ar', str(audio.SR), str(out / 'track.wav')], check=True)
    raw.unlink(missing_ok=True)
    return total


def free_models():
    """Ses modellerini bellekten at: Chrome'a yer kalsın (Chatterbox + whisper birkaç GB tutar)."""
    import gc
    voice._cb = None
    lipsync._whisper = None
    gc.collect()


def render(ep, out):
    free_models()
    for f in ('scene.html', 'cast.js'):
        shutil.copy(HERE / 'render' / f, out / f)
    (out / 'ep.js').write_text('window.EP = ' + json.dumps(ep, ensure_ascii=False) + ';\n', encoding='utf-8')
    r = subprocess.run(['node', str(HERE / 'render' / 'render.mjs'), str(out)])
    if r.returncode != 0:
        raise RuntimeError(f'render failed ({r.returncode})')
    return out / 'video.mp4'


def metadata(ep):
    site = os.environ.get('SITE_URL', '').strip()
    tags = ['almanca', 'almanca öğren', 'almanca dersi', 'deutsch lernen', 'almanca kelimeler', 'almanya',
            'german', 'learn german', ep['format'], 'fenek']
    desc = (f"{ep.get('desc', '')}\n\n"
            + (f'Tüm üniteler ücretsiz: {site}\n' if site else 'Tüm üniteler ücretsiz, link profilde.\n')
            + 'Her gün 4 yeni Almanca video. Karakterler: Emre, Lena ve Fenek 🦊\n\n'
            '#almanca #almancaöğren #deutsch #shorts')
    return ep['title'][:100], desc, tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-upload', action='store_true')
    ap.add_argument('--format', choices=episodes.SLOT_FORMATS)
    ap.add_argument('--slot', type=int)
    ap.add_argument('--bank', help='bank/ içinden belirli bir skeç dosyası')
    a = ap.parse_args()
    import upload

    mode = 'off' if a.no_upload or not upload.configured() else ((os.environ.get('YT_PRIVACY') or 'private').lower())
    if mode not in ('public', 'private', 'unlisted', 'off'):
        mode = 'private'
    log(f'upload mode: {mode}')
    if mode != 'off':
        cap = int(os.environ.get('MAX_PER_DAY') or 4)
        if today_count() >= cap:
            log(f'daily cap {cap} reached'); return
        try:
            log(f'channel: {upload.check_channel()}')
        except Exception as e:
            gh('error', f'channel check failed: {e}'); raise SystemExit(1)

    hist = load_hist()
    queued = sorted(QUEUE.glob('*.json')) if QUEUE.exists() else []
    qpath = None
    if a.bank:
        p = Path(a.bank)
        ep = dict(json.loads(p.read_text(encoding='utf-8')), format='hata', bank_id=p.stem)
        ep['id'] = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M') + '-hata'
    elif queued:
        qpath = queued[0]
        ep = json.loads(qpath.read_text(encoding='utf-8'))
        log(f"retrying queued {ep['id']}")
    else:
        slot = a.slot if a.slot is not None else hist.get('count', 0)
        if a.format:
            slot = episodes.SLOT_FORMATS.index(a.format)
        ep = episodes.make_episode(slot, hist, seed=int(datetime.now().timestamp()))
        ep['id'] = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M') + '-' + ep['format']
    log(f"episode {ep['id']}: {ep['title']}")

    out = OUT / ep['id']
    out.mkdir(parents=True, exist_ok=True)
    try:
        total = build(ep, out)
        log(f'audio ok ({total}s)')
        mp4 = render(ep, out)
    except Exception as e:
        traceback.print_exc(); gh('error', f'build failed: {e}'); raise SystemExit(1)
    title, desc, tags = metadata(ep)
    (out / 'meta.json').write_text(json.dumps({'title': title, 'description': desc, 'tags': tags, 'duration': total}, indent=2, ensure_ascii=False), encoding='utf-8')
    log(f'rendered {mp4}')

    if not qpath and mode != 'off':
        hist['recent'] = (hist.get('recent', []) + [{'id': ep['id'], 'format': ep['format'], 'topic': ep.get('topic'), 'title': ep['title']}])[-200:]
        hist['count'] = hist.get('count', 0) + 1
        if ep.get('bank_id'):
            hist.setdefault('bank_used', []).append(ep['bank_id'])
        HIST.write_text(json.dumps(hist, indent=1, ensure_ascii=False), encoding='utf-8')
    if mode == 'off':
        log('upload skipped'); return
    try:
        vid = upload.upload(mp4, title, desc, tags, mode, category='27')
    except upload.QuotaError as e:
        QUEUE.mkdir(exist_ok=True); (QUEUE / f"{ep['id']}.json").write_text(json.dumps(ep, ensure_ascii=False), encoding='utf-8')
        gh('warning', f'quota: queued ({e})'); return
    except Exception as e:
        traceback.print_exc()
        QUEUE.mkdir(exist_ok=True); (QUEUE / f"{ep['id']}.json").write_text(json.dumps(ep, ensure_ascii=False), encoding='utf-8')
        gh('error', f'upload failed: {e}'); raise SystemExit(1)
    new = not PUBLISHED.exists()
    with PUBLISHED.open('a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({'id': ep['id'], 'date_utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'), 'format': ep['format'],
                    'video_id': vid, 'privacy': mode, 'topic': ep.get('topic'), 'title': title})
    if qpath:
        qpath.unlink(missing_ok=True)
    log(f'uploaded https://youtube.com/shorts/{vid} ({mode})')


if __name__ == '__main__':
    main()
