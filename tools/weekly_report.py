"""Haftalık kanal raporu → Telegram (her pazartesi). Sadece okuma: herkese açık istatistikler, resmi API.

Her kanal için: abone, toplam izlenme ve geçen haftaya göre fark, son 7 günde yüklenen video sayısı ve medyan
izlenmesi, haftanın en iyi videosu. Önceki hafta stats_history.json'da tutulur.
    python tools/weekly_report.py
Env: YT_CLIENT_ID/SECRET/REFRESH_TOKEN (herhangi bir kanalın token'ı yeter), TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import html
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fenek import notify  # noqa: E402

HIST = ROOT / 'stats_history.json'
# kanal adı → kanal id (yeni kanal açılınca buraya eklenir)
CHANNELS = {
    'Dex & Friends': 'UCFpwuSiMBupYIOiiSx6lzsg',
    'Bloop Bonkers': 'UCdbAUr-IDGWaKXhXGnX55MQ',
    'German with Fenek': 'UCE76DGxmi3AWuKlp-bGYOCg',
}
# kimliği bilinmeyenler: her kanaldan bir video id → kanal id API'den bulunur
SEED_VIDEOS = ['tU35nbqGKME', 'SO3ZcE-QgKc', 'IjjH06w1I_w', 'D5uyEHgAfUQ', 'pmUNKe3bNZg', '7AyJ4fS-8B4', 'Wa3KXCSGjIo',
               'THLkUkT0zpc', 'BkOW0HgV36o', 'yzSnhl69zXo', 'bQysUnZx0Io']


def fmt(n):
    return f'{n / 1_000_000:.1f}M' if n >= 1_000_000 else f'{n / 1000:.1f}K' if n >= 1000 else str(n)


def main():
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'], token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    by_id = {c: n for n, c in CHANNELS.items()}  # kanal id → ad (tekil)
    for v in yt.videos().list(part='snippet', id=','.join(SEED_VIDEOS)).execute().get('items', []):
        by_id.setdefault(v['snippet']['channelId'], v['snippet']['channelTitle'].strip())
    ids = {n: c for c, n in by_id.items()}
    prev = json.loads(HIST.read_text()) if HIST.exists() else {}
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    rows, snap = [], {}
    for name, cid in ids.items():
        ch = yt.channels().list(part='snippet,statistics,contentDetails', id=cid).execute().get('items', [])
        if not ch:
            continue
        ch = ch[0]; st = ch['statistics']
        subs, views = int(st.get('subscriberCount', 0)), int(st.get('viewCount', 0))
        uploads = ch['contentDetails']['relatedPlaylists']['uploads']
        items = yt.playlistItems().list(part='contentDetails', playlistId=uploads, maxResults=50).execute().get('items', [])
        vids = []
        vid_ids = [i['contentDetails']['videoId'] for i in items]
        if vid_ids:
            vids = yt.videos().list(part='snippet,statistics,status', id=','.join(vid_ids)).execute().get('items', [])
        week = [v for v in vids if v['status'].get('privacyStatus') == 'public'
                and datetime.fromisoformat(v['snippet']['publishedAt'].replace('Z', '+00:00')) >= week_ago]
        wv = [int(v['statistics'].get('viewCount', 0)) for v in week]
        best = max(week, key=lambda v: int(v['statistics'].get('viewCount', 0)), default=None)
        p = prev.get(cid, {})
        snap[cid] = {'name': name, 'subs': subs, 'views': views, 'date': now.strftime('%Y-%m-%d')}
        rows.append(dict(name=html.escape(ch['snippet']['title'].strip()), subs=subs, dsubs=subs - p.get('subs', subs),
                         views=views, dviews=views - p.get('views', views), n=len(week),
                         med=int(statistics.median(wv)) if wv else 0,
                         best=(html.escape(best['snippet']['title'][:45]), int(best['statistics'].get('viewCount', 0))) if best else None))
    rows.sort(key=lambda r: -r['dviews'])
    lines = [f"📊 <b>Haftalık kanal raporu</b> · {now:%d.%m.%Y}", '']
    for r in rows:
        trend = '🟢' if r['dviews'] > 0 and r['med'] >= 100 else '🟡' if r['dviews'] > 0 else '🔴'
        lines.append(f"{trend} <b>{r['name']}</b>: +{fmt(r['dviews'])} izlenme · abone {r['subs']} "
                     f"({r['dsubs']:+d}) · bu hafta {r['n']} video, medyan {fmt(r['med'])}")
        if r['best']:
            lines.append(f"   ⭐ {r['best'][0]} — {fmt(r['best'][1])}")
    total = sum(r['dviews'] for r in rows)
    lines += ['', f"Toplam: +{fmt(total)} izlenme, {sum(r['dsubs'] for r in rows):+d} abone",
              '🔴 = izlenme artmadı → format/başlık değişikliği adayı']
    if not prev:
        lines.append('<i>İlk rapor: farklar gelecek haftadan itibaren doğru hesaplanır.</i>')
    HIST.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if notify.enabled():
        notify._call('sendMessage', text='\n'.join(lines)[:4000], parse_mode='HTML', disable_web_page_preview='true')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
