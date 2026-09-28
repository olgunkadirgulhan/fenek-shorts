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
CAST = {
    'emre': {'piper': 'de_DE-thorsten-high', 'cb': {'exaggeration': 0.45, 'cfg_weight': 0.45, 'temperature': 0.7}},
    'lena': {'piper': 'de_DE-kerstin-low', 'cb': {'exaggeration': 0.5, 'cfg_weight': 0.45, 'temperature': 0.7}},
    'fenek': {'piper': None, 'cb': {'exaggeration': 0.55, 'cfg_weight': 0.4, 'temperature': 0.75}},
}
SOFTEN = ('highpass=f=75,lowpass=f=10500,deesser=i=0.35:m=0.5:f=0.5,'
          'acompressor=threshold=-21dB:ratio=2.2:attack=8:release=120:makeup=1.5,'
          'aecho=0.9:0.5:28|46:0.07|0.04,'
          'silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.25:stop_threshold=-45dB,'
          'apad=pad_dur=0.04')

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


def expected_len(text):
    """Metin uzunluğundan beklenen konuşma süresi (sn): Türkçe/Almanca ~13 harf/sn + nefes payı."""
    return len(text.replace(' ', '')) / 13 + 0.35


def _chatterbox_checked(who, lang, text, cfg, ref, raw):
    """Chatterbox bazen kelimeyi tekrarlar (ses uzar) ya da cümleyi keser (ses kısalır): o zaman yazı ile ses
    kayar. Süre beklenenin çok dışındaysa farklı tohum ve daha düşük sıcaklıkla tekrar üret; en yakın olanı tut."""
    import torch, torchaudio
    m = _chatterbox()
    exp = expected_len(text)
    best = None
    for attempt in range(4):
        kw = dict(cfg['cb'])
        kw['temperature'] = max(0.45, kw['temperature'] - 0.1 * attempt)
        if ref.exists():
            kw['audio_prompt_path'] = str(ref)
        torch.manual_seed(1234 + attempt * 7919)
        # tek kelimelik kısa metinler modelde kararsız: noktalama ile cümle gibi okut
        say = text if text.rstrip()[-1:] in '.!?' else text.rstrip() + '.'
        wav = m.generate(say, language_id=lang, **kw)
        # sadece konuşulan kısmı ölç (baştaki/sondaki sessizlik kısa kelimelerde oranı şişirir)
        x = wav.detach().abs().flatten()
        loud = (x > 0.02).nonzero()
        dur = ((loud[-1] - loud[0]).item() / m.sr) if len(loud) else 0.0
        ratio = dur / exp
        err = abs(ratio - 1)
        if best is None or err < best[0]:
            best = (err, wav, dur)
        if 0.55 <= ratio <= 1.9:
            break
        print(f'[tts] süre şüpheli ({dur:.1f} sn, beklenen ~{exp:.1f}): tekrar üretiliyor — {text!r}', flush=True)
    torchaudio.save(str(raw), best[1].cpu(), m.sr)


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
        _chatterbox_checked(who, lang, text, cfg, ref, raw)
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
