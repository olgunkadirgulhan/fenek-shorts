"""Dudak senkronu (Rhubarb Lip Sync, MIT) + kelime zamanları (faster-whisper, MIT).

mouth_cues(wav)            -> [[sn, "A".."H" | "X"], ...]   (X = ağız kapalı / dinlenme)
word_starts(wav, text, lg) -> [sn, ...]  metindeki her kelimenin başladığı an (altyazıda karaoke vurgusu)
İkisi de bulunamazsa None döner; sahne eski yönteme (ağız aç-kapa, tahmini vurgu) düşer.
"""
import difflib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

RHUBARB = os.environ.get('RHUBARB') or shutil.which('rhubarb')
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'small')
_whisper = None


def mouth_cues(wav):
    if not RHUBARB or not Path(RHUBARB).exists():
        return None
    out = Path(tempfile.gettempdir()) / f'rhubarb_{os.getpid()}.json'
    # phonetic: dilden bağımsız tanıyıcı (Türkçe/Almanca için); G/H/X ek ağız şekilleri açık
    r = subprocess.run([RHUBARB, '-r', 'phonetic', '-f', 'json', '--extendedShapes', 'GHX', '-q', '-o', str(out), str(wav)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        print(f'[lipsync] rhubarb hata: {r.stderr[:200]}', flush=True)
        return None
    cues = json.loads(out.read_text(encoding='utf-8')).get('mouthCues', [])
    out.unlink(missing_ok=True)
    return [[round(c['start'], 3), c['value']] for c in cues]


def _model():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        print(f'[lipsync] whisper modeli: {WHISPER_MODEL}', flush=True)
        _whisper = WhisperModel(WHISPER_MODEL, device='cpu', compute_type='int8')
    return _whisper


def _norm(w):
    return re.sub(r'[^\wäöüßçğıöşü]', '', w.lower())


def word_starts(wav, text, lang):
    words = text.split()
    if not words:
        return None
    try:
        segs, _ = _model().transcribe(str(wav), language=lang, word_timestamps=True, initial_prompt=text,
                                      beam_size=5, vad_filter=False, condition_on_previous_text=False)
        heard = [w for s in segs for w in (s.words or [])]
    except Exception as e:
        print(f'[lipsync] whisper hata: {e}', flush=True)
        return None
    if not heard:
        return None
    # duyulan kelimeleri metindeki kelimelerle eşleştir; eşleşmeyenler komşulardan doldurulur
    a, b = [_norm(w) for w in words], [_norm(h.word) for h in heard]
    starts = [None] * len(words)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            starts[blk.a + k] = heard[blk.b + k].start
    if starts[0] is None:
        starts[0] = heard[0].start
    end = heard[-1].end
    for i in range(len(starts)):   # boşluklar: önceki ile sonraki bilinen arasında eşit dağıt
        if starts[i] is None:
            j = next((k for k in range(i + 1, len(starts)) if starts[k] is not None), None)
            nxt = starts[j] if j is not None else end
            gap = (j if j is not None else len(starts)) - i + 1
            starts[i] = starts[i - 1] + (nxt - starts[i - 1]) / gap
    # sıralı olmalı
    for i in range(1, len(starts)):
        starts[i] = max(starts[i], starts[i - 1] + 0.03)
    return [round(max(0.0, s), 3) for s in starts]
