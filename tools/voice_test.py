"""Ses denemesi: her karakter için örnek cümleler üretir -> output/voice_test/*.wav (+ hepsi arka arkaya: all.wav)
    TTS_ENGINE=chatterbox python tools/voice_test.py
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fenek import voice  # noqa: E402

LINES = [
    ('fenek', 'tr', "Almanya'da kafede bu hatayı yapma!"),
    ('lena', 'de', 'Guten Morgen! Was möchten Sie?'),
    ('emre', 'de', 'Ich möchte einen Kaffee mit Milch, bitte.'),
    ('fenek', 'tr', 'Dur! İki hata var. Birincisi kaba duruyor, kibarcası şöyle.'),
    ('lena', 'de', 'Das macht sieben Euro.'),
    ('fenek', 'tr', 'Tüm ünite sitede ücretsiz. Link profilde!'),
]
out = ROOT / 'output' / 'voice_test'
out.mkdir(parents=True, exist_ok=True)
files = []
for i, (who, lang, text) in enumerate(LINES):
    t = time.time()
    wav, dur = voice.synth(who, lang, text)
    dst = out / f'{i:02d}_{who}.wav'
    dst.write_bytes(Path(wav).read_bytes())
    files.append(dst)
    print(f'{who:6} {dur:4.1f}s ses, {time.time() - t:5.1f}s üretim | {text}', flush=True)
lst = out / 'list.txt'
lst.write_text(''.join(f"file '{f.name}'\n" for f in files), encoding='utf-8')
subprocess.run([os.environ.get('FFMPEG', 'ffmpeg'), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst),
                '-af', 'apad=pad_dur=0.5', str(out / 'all.wav')], check=True)
print('->', out / 'all.wav')
