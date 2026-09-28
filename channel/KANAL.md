# YouTube kanalı açılışı (Almanca · Türkler için)

Görseller bu klasörde: `profil_800.png` (profil resmi) ve `kapak_2560x1440.png` (kanal kapağı).
Site açılana kadar kanal adında ve açıklamada "Fenek" geçmiyor.

## 1. Kanalı aç (5 dk)
1. youtube.com → sağ üstte profil resmi → **Ayarlar** → **Yeni kanal oluştur**
   *(Marka hesabı olarak açılır: ileride şirkete devredilebilir, başka yöneticiler eklenebilir.)*
2. **Kanal adı** — öneriler (sonradan değiştirilebilir):
   - **Emre ile Almanca**
   - **Günlük Almanca**
   - **Almanca Kafe**
3. **Tanıtıcı (@)**: adla aynı, ör. `@emreilealmanca`
4. **Profil resmi**: `profil_800.png` · **Kapak**: `kapak_2560x1440.png`

## 2. Kanal açıklaması (kopyala-yapıştır)
```
Her gün 4 kısa Almanca video! 🇩🇪
Kelimeler, günlük diyaloglar, artikel (der/die/das) soruları ve kelime avı — hepsi Türkçe açıklamalı.
A1'den B1'e: Almanya'da yaşayanlar, Almanca sınavına hazırlananlar ve sıfırdan başlayanlar için.
Emre, Lena ve tilkimizle her gün birkaç dakikada Almancanı geliştir. Takip et! 🔔
```
**Anahtar kelimeler** (Ayarlar → Kanal): `almanca, almanca öğren, almanca dersi, almanca kelimeler, deutsch lernen, almanya, der die das, almanca a1`
**Ülke**: Türkiye · **Varsayılan video dili**: Türkçe

## 3. Telefon doğrulaması (zorunlu)
youtube.com/verify → telefon numarası ile doğrula. (Özel küçük resim, uzun video ve canlı yayın için gerekli.)

## 4. Otomatik yüklemeyi bağla (bilgisayarında, 2 dk)
1. `dex-and-friends\client_secret.json` dosyasını `fenek-shorts` klasörüne **kopyala**.
2. `fenek-shorts` klasöründe:
   ```
   python auth_setup.py --repo olgunkadirgulhan/fenek-shorts
   ```
3. Açılan Google ekranında **yeni kanalı** seç → izin ver. Anahtarlar GitHub'a otomatik kaydedilir.
4. Bana "bağlandı" de: ilk 2–3 videoyu **gizli** yükleyip kontrol ederiz, sonra **herkese açık** yaparız.
