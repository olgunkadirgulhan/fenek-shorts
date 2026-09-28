"""Site için telaffuz dosyaları (Chatterbox Multilingual, MIT) — Piper'da ticari lisanslı sesi olmayan diller (tr, ar) için.

    python tools/site_audio.py tr 0 8     # dil, parça no, parça sayısı → out/tr/<fnv>.mp3
Metin listesi: site_audio/tts_<dil>.json (sitedeki tools/collect_tts.mjs üretir). Dosya adı = FNV-1a (site ile aynı).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

ROOT = Path(__file__).resolve().parent.parent
FILTER = "highpass=f=70,lowpass=f=11000,silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.3:stop_threshold=-45dB,acompressor=threshold=-20dB:ratio=2:attack=8:release=120,loudnorm=I=-18:TP=-2,apad=pad_dur=0.05"


def fnv(s):
    h = 0x811C9DC5
    data = s.encode("utf-16-le")
    for i in range(0, len(data), 2):
        h ^= data[i] | (data[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def main():
    lang, shard, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    texts = json.loads((ROOT / "site_audio" / f"tts_{lang}.json").read_text(encoding="utf-8"))
    mine = [t for i, t in enumerate(texts) if i % n == shard]
    out = ROOT / "out" / lang
    out.mkdir(parents=True, exist_ok=True)
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    ref = ROOT / "voices" / f"site_{lang}.wav"
    t0 = time.time()
    for i, text in enumerate(mine):
        mp3 = out / f"{fnv(text)}.mp3"
        if mp3.exists():
            continue
        # çok kısa metinler (tek kelime) modelde kararsız olabiliyor: noktalama ekleyerek cümle gibi okut
        say = text if text[-1:] in ".!?؟" else text + "."
        kw = {"exaggeration": 0.4, "cfg_weight": 0.5, "temperature": 0.6}
        if ref.exists():
            kw["audio_prompt_path"] = str(ref)
        wav = model.generate(say, language_id=lang, **kw)
        raw = out / "_tmp.wav"
        torchaudio.save(str(raw), wav.cpu(), model.sr)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", FILTER, "-ac", "1", "-ar", "24000",
                        "-c:a", "libmp3lame", "-b:a", "40k", str(mp3)], check=True)
        raw.unlink(missing_ok=True)
        if i % 25 == 0:
            print(f"[{lang} {shard}/{n}] {i + 1}/{len(mine)} ({time.time() - t0:.0f}s)", flush=True)
    print(f"OK {lang} shard {shard}: {len(mine)} metin, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
