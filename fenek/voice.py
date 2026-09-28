"""Karakter sesleri.

Motorlar (TTS_ENGINE):
  chatterbox  Resemble AI Chatterbox Multilingual (MIT). Almanca + Türkçe, doğal ve yumuşak. Varsayılan.
  piper       Piper + Thorsten/Kerstin (CC0). Sadece Almanca; hızlı yedek.
  edge        edge-tts, SADECE yerel önizleme/test (ticari lisansı yok, yayında kullanma).
Ses kimliği: voices/<karakter>.wav varsa referans alınır (sadece hakkına sahip olduğun kayıtlar!).
Her ses ffmpeg ile yumuşatılır: EQ + de-esser + hafif kompresör + çok hafif oda yankısı.
Aynı cümle tekrar üretilmez (önbellek: ~/.cache/fenek/tts).
"""
import hashlib
import json
import os
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get('FENEK_CACHE', Path.home() / '.cache' / 'fenek'))
TTS_CACHE = CACHE / 'tts'
VOICES = ROOT / 'voices'
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')

# karakter -> (dil, piper sesi, chatterbox ayarları)
# Sakin, net "öğretmen" tonu: düşük exaggeration = daha az abartı; düşük cfg_weight = daha yavaş, yumuşak tempo
CAST = {
    'emre': {'piper': 'de_DE-thorsten-high', 'cb': {'exaggeration': 0.4, 'cfg_weight': 0.35, 'temperature': 0.65}},
    'lena': {'piper': 'de_DE-kerstin-low', 'cb': {'exaggeration': 0.42, 'cfg_weight': 0.35, 'temperature': 0.65}},
    'fenek': {'piper': None, 'cb': {'exaggeration': 0.45, 'cfg_weight': 0.32, 'temperature': 0.65}},
}
# Yumuşatma zinciri: gürültü/uğultu temizliği, hafif sıcaklık (200 Hz), sertlik azaltma (3.2 kHz), cızırtı giderici,
# nazik kompresör, baş/son sessizlik kırpma, her replik aynı ses seviyesine (-18 LUFS)
SOFTEN = ('highpass=f=80,lowpass=f=11000,'
          'equalizer=f=200:t=q:w=1.0:g=1.5,equalizer=f=3200:t=q:w=1.2:g=-2.5,'
          'deesser=i=0.4:m=0.5:f=0.5,'
          'acompressor=threshold=-22dB:ratio=2:attack=10:release=150:makeup=1.3,'
          'silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.25:stop_threshold=-45dB,'
          'loudnorm=I=-18:TP=-2:LRA=7,'
          'apad=pad_dur=0.05')

_cb = None
_piper = {}


def engine():
    return (os.environ.get('TTS_ENGINE') or 'chatterbox').lower()


def _chatterbox():
    global _cb
    if _cb is None:
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        dev = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f'[tts] loading chatterbox on {dev}', flush=True)
        _cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    return _cb


def _piper_voice(name):
    if name not in _piper:
        from piper import PiperVoice
        d = CACHE / 'piper'
        d.mkdir(parents=True, exist_ok=True)
        if not (d / f'{name}.onnx').exists():
            subprocess.run(['python', '-m', 'piper.download_voices', '--data-dir', str(d), name], check=True)
        _piper[name] = PiperVoice.load(str(d / f'{name}.onnx'))
    return _piper[name]


def wav_len(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def synth(who, lang, text):
    """-> (wav yolu 48 kHz mono, süre sn)"""
    eng = engine() if not (engine() == 'piper' and lang != 'de') else 'chatterbox'
    if os.environ.get('GITHUB_ACTIONS') and eng == 'edge':
        raise RuntimeError('edge-tts yayında kullanılamaz')
    ref = VOICES / f'{who}.wav'
    cfg = CAST[who]
    key = hashlib.sha1(json.dumps([eng, who, lang, text, cfg, ref.exists() and ref.stat().st_size, SOFTEN]).encode()).hexdigest()[:16]
    TTS_CACHE.mkdir(parents=True, exist_ok=True)
    out = TTS_CACHE / f'{key}.wav'
    if out.exists():
        return out, wav_len(out)
    raw = TTS_CACHE / f'{key}.raw.wav'
    if eng == 'chatterbox':
        import torchaudio
        m = _chatterbox()
        kw = dict(cfg['cb'])
        if ref.exists():
            kw['audio_prompt_path'] = str(ref)
        wav = m.generate(text, language_id=lang, **kw)
        torchaudio.save(str(raw), wav.cpu(), m.sr)
    elif eng == 'edge':
        import asyncio, edge_tts
        name = {'emre': 'de-DE-ConradNeural', 'lena': 'de-DE-KatjaNeural', 'fenek': 'tr-TR-EmelNeural'}[who]
        mp3 = raw.with_suffix('.mp3')
        asyncio.run(edge_tts.Communicate(text, name).save(str(mp3)))
        raw = mp3
    else:
        v = _piper_voice(cfg['piper'])
        with wave.open(str(raw), 'wb') as wf:
            v.synthesize_wav(text, wf)
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', str(raw), '-af', SOFTEN, '-ar', '48000', '-ac', '1', str(out)], check=True)
    raw.unlink(missing_ok=True)
    return out, wav_len(out)
