# Fenek Shorts — otomatik Almanca Shorts kanalı (tr-de)

Bilgisayar kapalıyken de çalışır: her şey GitHub Actions üzerinde (`.github/workflows/videos.yml`).

```
content/course.json (sitenin 35 ünitesi + 3000 kelimesi)
  → bölüm senaryosu (fenek/episodes.py: sahne · kelime · quiz · av · hata)
  → sesler: Chatterbox Multilingual (MIT), yumuşatma zinciri + prosedürel müzik/SFX
  → SVG animasyon (render/scene.html, karakterler render/cast.js) → headless Chrome → ffmpeg
  → YouTube (upload.py)
```

**Takvim:** Günde 3 Shorts, TR 08:00 · 15:00 · 22:00. Workflow saatlik tetiklenir; `.github/slot_guard.py` sadece zamanı gelmiş ve yüklenmemiş slot varsa video yapar (GitHub cron gecikmelerine karşı).

**Formatlar** (slot sırasıyla dönüşümlü): diyalog sahnesi (veya `bank/` içindeki "tipik hata" skeçleri) → 5 kelime kartı → 3 soruluk quiz → kelime avı. İçerik uydurulmaz; hepsi sitenin onaylı verisinden gelir ve kısa sürede tekrar etmez (`history.json`).

**Karakterler:** Emre (öğrenen), Lena (yerli), Fenek 🦊 (anlatıcı, sitenin maskotu). Tamamen kodla çizilir; telif yok.

## Kurulum (bir kez)

1. **YouTube kanalını bağla** (diğer kanallarındaki `client_secret.json` kullanılabilir):
   `python auth_setup.py --repo olgunkadirgulhan/fenek-shorts --expect Fenek`
   → `YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN / YT_CHANNEL_ID` secrets'a yazılır.
   Google Cloud'daki OAuth uygulaması **In production** olmalı; *Testing* modunda token 7 günde ölür.
2. **Repo variables** (Settings → Variables):
   - `YT_PRIVACY` = `private` (ilk günler kontrol için) → sonra `public`
   - `SITE_URL` = sitenin adresi (yayına alınınca)
   - opsiyonel: `LEVELS` (varsayılan `A1,A2,B1`), `MAX_PER_DAY` (varsayılan 4), `TTS_ENGINE` (`chatterbox` | `piper`)
3. **API denetimi:** 2020 sonrası açılan Google Cloud projelerinden yüklenen videolar, proje YouTube API denetiminden geçene kadar *private* kilitli kalır. Diğer kanallarının projesi denetimden geçtiyse onu kullan.
4. **Harici tetikleyici (önerilir):** cron-job.org'dan saatte bir `workflow_dispatch` (`auto: true`) çağrısı — GitHub cron'u bazen saatlerce gecikir.

## Sesler

- Varsayılan: Chatterbox Multilingual (Resemble AI, MIT lisansı, Almanca + Türkçe). Çıktıya duyulmayan Perth filigranı ekler.
- Karakterlere kendi ses kimliklerini vermek için `voices/emre.wav`, `voices/lena.wav`, `voices/fenek.wav` (10–15 sn temiz kayıt) koy. **Sadece hakkına sahip olduğun kayıtlar** (kendi sesin veya izin aldığın kişiler). Fenek için en iyisi kendi sesin.
- `edge` motoru yalnızca yerel önizleme içindir; Actions'da çalışmaz.

## Yerel test

```
pip install -r requirements.txt
python run.py --format quiz --no-upload      # output/<id>/video.mp4
node render/render.mjs output/<id> 3 10      # belirli saniyelerin önizleme PNG'leri
```

## İçeriği güncelle

Site içeriği değişince: `node tools/export_content.mjs ../site/js` → `content/course.json`.
