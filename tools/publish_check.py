"""Gizli kalan son yüklemeleri herkese açık yapmayı dener ve durumu raporlar.
Google, doğrulanmamış (denetimden geçmemiş) API projelerinden yüklenen videoları gizliye kilitleyebilir:
bu durumda güncelleme hata verir ya da video gizli kalır → rapor edilir.
    python tools/publish_check.py [video_id ...]
"""
import csv
import os
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent


def main():
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'], token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    ids = sys.argv[1:]
    if not ids and (ROOT / 'published.csv').exists():
        with (ROOT / 'published.csv').open(encoding='utf-8') as f:
            ids = [r['video_id'] for r in csv.DictReader(f)][-8:]
    for vid in ids:
        v = yt.videos().list(part='status,snippet', id=vid).execute().get('items', [])
        if not v:
            print(f'{vid}: bulunamadı'); continue
        st = v[0]['status']
        print(f"{vid}: şu an {st['privacyStatus']} | yükleme {st.get('uploadStatus')} | {v[0]['snippet']['title'][:50]}", flush=True)
        if st['privacyStatus'] != 'public':
            try:
                yt.videos().update(part='status', body={'id': vid, 'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}}).execute()
                after = yt.videos().list(part='status', id=vid).execute()['items'][0]['status']['privacyStatus']
                print(f'  → herkese açık yapıldı, yeni durum: {after}' + ('' if after == 'public' else '  ⚠️ KİLİTLİ OLABİLİR'), flush=True)
            except Exception as e:
                print(f'  → herkese açık YAPILAMADI (muhtemelen proje kilidi): {str(e)[:300]}', flush=True)


if __name__ == '__main__':
    main()
