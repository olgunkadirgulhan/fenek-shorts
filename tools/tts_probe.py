"""Seslendirme teşhisi: kısa Almanca kelimeler kesiliyor mu? Birkaç yöntemi karşılaştırır → probe/*.wav + probe/rapor.json
    python tools/tts_probe.py
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fenek import voice  # noqa: E402

WORDS = ['die Vorstellung', 'das Hobby', 'der Ausflug', 'die Freizeit', 'das Konzert',
         'Ich möchte einen Kaffee mit Milch, bitte.']
OUT = ROOT / 'probe'
OUT.mkdir(exist_ok=True)


def analyze(path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    loud = np.nonzero(np.abs(x) > 0.02)[0]
    span = (loud[-1] - loud[0]) / sr if len(loud) else 0
    # son 40 ms'nin enerjisi / en yüksek enerji: yüksekse ses aniden kesilmiş demektir
    win = int(0.04 * sr)
    rms = lambda a: float(np.sqrt(np.mean(a ** 2)) + 1e-9)
    frames = [rms(x[i:i + win]) for i in range(0, max(1, len(x) - win), win)]
    tail = rms(x[loud[-1] - win:loud[-1]]) if len(loud) and loud[-1] > win else 0
    return {'toplam_sn': round(len(x) / sr, 2), 'konusma_sn': round(span, 2), 'son_enerji_orani': round(tail / max(frames), 3)}


def chatterbox(text, say, name):
    import torch, torchaudio
    m = voice._chatterbox()
    torch.manual_seed(1234)
    wav = m.generate(say, language_id='de', **voice.CAST['emre']['cb'])
    p = OUT / f'{name}.wav'
    torchaudio.save(str(p), wav.cpu(), m.sr)
    return p


def piper(text, name, who='emre'):
    v = voice._piper_voice(voice.CAST[who]['piper'])
    p = OUT / f'{name}.wav'
    with wave.open(str(p), 'wb') as wf:
        v.synthesize_wav(text, wf)
    return p


rapor = {}
for i, t in enumerate(WORDS):
    r = {}
    for key, path in [('A_chatterbox_nokta', chatterbox(t, t.rstrip('.') + '.', f'{i}_A')),
                      ('B_chatterbox_uc_nokta', chatterbox(t, t.rstrip('.') + '...', f'{i}_B')),
                      ('C_piper', piper(t, f'{i}_C'))]:
        r[key] = analyze(path)
        soft = path.with_name(path.stem + '_soft.wav')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(path), '-af', voice.SOFTEN, '-ar', '48000', '-ac', '1', str(soft)], check=True)
        r[key + '_yumusatilmis'] = analyze(soft)
    rapor[t] = r
    print(t, json.dumps(r, ensure_ascii=False), flush=True)
(OUT / 'rapor.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding='utf-8')
