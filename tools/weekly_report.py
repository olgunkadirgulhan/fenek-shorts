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
    'Fenektr': 'UC0E2yFyEoA_G8bBRYbW6cbg',
    'Maya Builds Cozy': 'UCe5trBb_n-p9FA-qFlOvocQ',
    'Konuşan Fruits': 'UCbuPTAaiLEbSvTDSZnRe6IQ',
    'Fruit Drama Club': 'UCRn8Uvt1czDE5hJQBrJRalg',
}
# kimliği bilinmeyenler: her kanaldan bir video id → kanal id API'den bulunur
SEED_VIDEOS = ['tU35nbqGKME', 'SO3ZcE-QgKc', 'IjjH06w1I_w', 'D5uyEHgAfUQ', 'pmUNKe3bNZg', '7AyJ4fS-8B4', 'Wa3KXCSGjIo',
               'THLkUkT0zpc', 'BkOW0HgV36o', 'yzSnhl69zXo', 'bQysUnZx0Io']


REQUEST_FILES = [('dex-and-friends', 'viewer_requests.json'), ('konusan-meyveler', 'viewer_requests.json'),
                 ('konusan-meyveler', 'viewer_requests_en.json'), ('bloop-bonkers', 'viewer_requests.json'),
                 ('fenek-de-en', 'viewer_requests.json'), ('fenek-shorts', 'viewer_requests.json'),
                 ('maya-builds-cozy', 'viewer_requests.json')]


def viewer_requests(since):
    """Yorumlardan toplanan video istekleri (tools/auto_reply.py), son 7 gün; kullanılanlar işaretli."""
    import requests
    out = []
    for repo, f in REQUEST_FILES:
        try:
            r = requests.get(f'https://raw.githubusercontent.com/olgunkadirgulhan/{repo}/main/{f}', timeout=20)
            if r.status_code != 200:
                continue
            for x in r.json():
                if x.get('date', '') >= since.strftime('%Y-%m-%d'):
                    out.append(f"{repo}: {x['topic']}" + (' ✅ videosu yapıldı' if x.get('used') else ''))
        except Exception:  # noqa: BLE001
            continue
    return out


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
            vids = yt.videos().list(part='snippet,statistics,status,contentDetails', id=','.join(vid_ids)).execute().get('items', [])
        week = [v for v in vids if v['status'].get('privacyStatus') == 'public'
                and datetime.fromisoformat(v['snippet']['publishedAt'].replace('Z', '+00:00')) >= week_ago]
        wv = [int(v['statistics'].get('viewCount', 0)) for v in week]
        best = max(week, key=lambda v: int(v['statistics'].get('viewCount', 0)), default=None)
        flags = []  # ihtar/kısıtlama işaretleri (bağlantılı kanallar riski: erken fark et)
        for v in vids:
            stt, cd = v['status'], v.get('contentDetails', {})
            if stt.get('uploadStatus') in ('rejected', 'failed'):
                flags.append(f"reddedildi ({stt.get('rejectionReason') or stt.get('failureReason')})")
            elif stt['privacyStatus'] != 'public' and not stt.get('publishAt'):
                flags.append('gizli kaldı')
            if cd.get('contentRating', {}).get('ytRating') == 'ytAgeRestricted':
                flags.append('yaş kısıtlı')
            if cd.get('regionRestriction', {}).get('blocked'):
                flags.append('bölge engeli')
        p = prev.get(cid, {})
        snap[cid] = {'name': name, 'subs': subs, 'views': views, 'date': now.strftime('%Y-%m-%d')}
        rows.append(dict(name=html.escape(ch['snippet']['title'].strip()), subs=subs, dsubs=subs - p.get('subs', subs),
                         views=views, dviews=views - p.get('views', views), n=len(week),
                         med=int(statistics.median(wv)) if wv else 0,
                         flags=sorted(set(flags)), best=(html.escape(best['snippet']['title'][:45]), int(best['statistics'].get('viewCount', 0))) if best else None))
    rows.sort(key=lambda r: -r['dviews'])
    lines = [f"📊 <b>Haftalık kanal raporu</b> · {now:%d.%m.%Y}", '']
    for r in rows:
        trend = '🟢' if r['dviews'] > 0 and r['med'] >= 100 else '🟡' if r['dviews'] > 0 else '🔴'
        lines.append(f"{trend} <b>{r['name']}</b>: +{fmt(r['dviews'])} izlenme · abone {r['subs']} "
                     f"({r['dsubs']:+d}) · bu hafta {r['n']} video, medyan {fmt(r['med'])}")
        if r['best']:
            lines.append(f"   ⭐ {r['best'][0]} — {fmt(r['best'][1])}")
        if r['flags']:
            lines.append(f"   ⚠️ <b>Kısıtlama:</b> {', '.join(r['flags'])} → Studio'da kontrol et")
    total = sum(r['dviews'] for r in rows)
    flagged = [r['name'] for r in rows if r['flags']]
    lines.insert(1, '⚠️ <b>Kısıtlama var:</b> ' + ', '.join(flagged) if flagged else '✅ Hiçbir kanalda ihtar/kısıtlama işareti yok')
    lines += ['', f"Toplam: +{fmt(total)} izlenme, {sum(r['dsubs'] for r in rows):+d} abone",
              '🔴 = izlenme artmadı → format/başlık değişikliği adayı']
    if not prev:
        lines.append('<i>İlk rapor: farklar gelecek haftadan itibaren doğru hesaplanır.</i>')
    reqs = viewer_requests(week_ago)
    if reqs:
        lines += ['', '💡 <b>İzleyici istekleri (bu hafta)</b>'] + [f'• {html.escape(r)}' for r in reqs[:15]]
    HIST.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if notify.enabled():
        notify._call('sendMessage', text='\n'.join(lines)[:4000], parse_mode='HTML', disable_web_page_preview='true')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
