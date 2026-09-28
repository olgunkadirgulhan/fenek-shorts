"""Karakter sesleri — yedekli zincir (TTS_ENGINE=auto, varsayılan):

  1. azure     Microsoft Azure Speech (resmî, ticari kullanım serbest). AZURE_SPEECH_KEY + AZURE_SPEECH_REGION varsa.
  2. edge      edge-tts: AYNI Microsoft sesleri (gayriresmî uç). Azure yoksa / hata verirse / kota dolarsa.
  3. fallback  İkisi de çalışmazsa: Almanca → Piper (Thorsten/Kerstin, CC0), Türkçe → Chatterbox (MIT). Gün boş geçmez.
Azure ile edge aynı ses kataloğunu kullanır: yedeğe geçilse de izleyici fark etmez (önbellekte ortak anahtar 'ms').
TTS_ENGINE ile tek motor da zorlanabilir: azure | edge | piper | chatterbox.
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
# Sadece baştaki ve sondaki sessizlik kırpılır (ortadaki duraklamalar ve kelime sonlarındaki kısık sesler korunur;
# eski zincir bunları "sessizlik" sanıp kırpıyordu → kelimeler kesik duyuluyordu). Sonda 0.12 sn nefes payı kalır.
SOFTEN = ('highpass=f=75,lowpass=f=10500,deesser=i=0.35:m=0.5:f=0.5,'
          'acompressor=threshold=-21dB:ratio=2.2:attack=8:release=120:makeup=1.5,'
          'aecho=0.9:0.5:28|46:0.07|0.04,'
          'silenceremove=start_periods=1:start_threshold=-50dB,'
          'areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.12,areverse,'
          'apad=pad_dur=0.06')
PIPER_SLOW = 1.2   # Piper'ın konuşma süresi çarpanı: öğrenenler için ~%20 daha yavaş ve net

# Microsoft sinir ağı sesleri (Azure ve edge-tts'de aynı isimler)
MS_VOICE = {'emre': 'de-DE-ConradNeural', 'lena': 'de-DE-KatjaNeural', 'fenek': 'tr-TR-EmelNeural'}
MS_RATE = {'de': '-8%', 'tr': '+0%'}   # Almanca biraz yavaş: öğrenenler rahat takip etsin
# Microsoft sesleri zaten temiz: sadece baş/son sessizlik kırpılır
CLEAN = ('silenceremove=start_periods=1:start_threshold=-50dB,'
         'areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.12,areverse,'
         'apad=pad_dur=0.06')

_cb = None
_piper = {}


def engine():
    return (os.environ.get('TTS_ENGINE') or 'auto').lower()


def chain():
    """Denenecek motorlar sırası."""
    e = engine()
    if e == 'auto':
        return (['azure'] if os.environ.get('AZURE_SPEECH_KEY') else []) + ['edge', 'fallback']
    return [e] if e == 'fallback' else [e, 'fallback']


def _xml(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _azure(who, lang, text, raw):
    import requests
    region = os.environ.get('AZURE_SPEECH_REGION', 'westeurope')
    locale = MS_VOICE[who][:5]
    ssml = (f"<speak version='1.0' xml:lang='{locale}'><voice name='{MS_VOICE[who]}'>"
            f"<prosody rate='{MS_RATE[lang]}'>{_xml(text)}</prosody></voice></speak>")
    r = requests.post(f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1', data=ssml.encode('utf-8'), timeout=30,
                      headers={'Ocp-Apim-Subscription-Key': os.environ['AZURE_SPEECH_KEY'], 'Content-Type': 'application/ssml+xml',
                               'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm', 'User-Agent': 'fenek-shorts'})
    if r.status_code != 200 or len(r.content) < 2000:
        raise RuntimeError(f'azure {r.status_code}: {r.text[:120]}')
    raw.write_bytes(r.content)
    return raw


def _edge(who, lang, text, raw):
    import asyncio, edge_tts
    mp3 = raw.with_suffix('.mp3')
    async def go():
        await asyncio.wait_for(edge_tts.Communicate(text, MS_VOICE[who], rate=MS_RATE[lang]).save(str(mp3)), timeout=40)
    last = None
    for _ in range(3):
        try:
            asyncio.run(go())
            if mp3.exists() and mp3.stat().st_size > 1000:
                return mp3
        except Exception as e:
            last = e
    raise RuntimeError(f'edge: {last}')


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
        # kesilme testi: son 40 ms tam seste bitiyorsa kelime yarıda kalmış demektir (doğal bitişte ses söner)
        cut = 0.0
        if len(loud):
            w = int(0.04 * m.sr); end = loud[-1].item()
            tail = x[max(0, end - w):end].pow(2).mean().sqrt().item()
            peak = max(x[i:i + w].pow(2).mean().sqrt().item() for i in range(0, max(1, len(x) - w), w))
            cut = tail / (peak + 1e-9)
        err = abs(ratio - 1) + (cut if cut > 0.45 else 0)
        if best is None or err < best[0]:
            best = (err, wav, dur)
        if 0.55 <= ratio <= 1.9 and cut <= 0.45:
            break
        print(f'[tts] şüpheli (konuşma {dur:.1f} sn, beklenen ~{exp:.1f}, son/tepe {cut:.2f}): tekrar üretiliyor — {text!r}', flush=True)
    torchaudio.save(str(raw), best[1].cpu(), m.sr)


def synth(who, lang, text):
    """-> (wav yolu 48 kHz mono, süre sn). Motor zinciri: azure → edge → yedek (piper/chatterbox)."""
    ref = VOICES / f'{who}.wav'
    cfg = CAST[who]
    TTS_CACHE.mkdir(parents=True, exist_ok=True)
    errors = []
    for eng in chain():
        if eng == 'fallback':
            eng = 'piper' if (lang == 'de' and cfg['piper']) else 'chatterbox'
        group = 'ms' if eng in ('azure', 'edge') else eng        # Azure ve edge aynı ses → ortak önbellek
        key = hashlib.sha1(json.dumps([group, who, lang, text, MS_VOICE.get(who), MS_RATE.get(lang), cfg, SOFTEN, CLEAN, PIPER_SLOW]).encode()).hexdigest()[:16]
        out = TTS_CACHE / f'{key}.wav'
        if out.exists():
            return out, wav_len(out)
        raw = TTS_CACHE / f'{key}.raw.wav'
        try:
            if eng == 'azure':
                src = _azure(who, lang, text, raw)
            elif eng == 'edge':
                src = _edge(who, lang, text, raw)
            elif eng == 'chatterbox':
                _chatterbox_checked(who, lang, text, cfg, ref, raw); src = raw
            else:
                from piper import SynthesisConfig
                v = _piper_voice(cfg['piper'])
                with wave.open(str(raw), 'wb') as wf:
                    v.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=PIPER_SLOW))
                src = raw
        except Exception as e:
            errors.append(f'{eng}: {str(e)[:150]}')
            print(f'[tts] {eng} başarısız, sıradaki motor deneniyor — {errors[-1]}', flush=True)
            continue
        if errors:   # yedeğe geçildi: GitHub'da uyarı olarak görünsün
            msg = f'ses yedeğe geçti ({eng}): ' + ' | '.join(errors)
            print(f'::warning::{msg}' if os.environ.get('GITHUB_ACTIONS') else f'[tts] {msg}', flush=True)
        af = CLEAN if group == 'ms' else SOFTEN
        subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', str(src), '-af', af, '-ar', '48000', '-ac', '1', str(out)], check=True)
        src.unlink(missing_ok=True)
        return out, wav_len(out)
    raise RuntimeError('hiçbir ses motoru çalışmadı: ' + ' | '.join(errors))
