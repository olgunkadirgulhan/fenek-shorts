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
               'THLkUkT0zpc', 'BkOW0HgV36o', 'yzSnhl69zXo', 'bQysUnZx0Io',
               # 2026-10-14: yeni/eksik kanallar (Then vs Now, The Real Cost, Paw Rivals, Countryball, Whale, Orbit, Moon, Bigger)
               'BT4AIr-ke2w', 'EJDr1QqvAQE', 'QbWjO8_7jKE', 'CCuS0sDMeO0', 'BjdD7ePr8v8', '4DSPgPoQmvE', 'aSdteejXYH8', 'Pdg-lzG7K3k']

# Para kazanma tahmini: kanal adı parçası → (uzun video RPM aralığı $, Short RPM aralığı $) — sektör ortalaması, kesin değil
RPM = [('real cost', (8, 15), (0.05, 0.15)), ('debtlab', (8, 15), (0.05, 0.15)), ('then', (5, 10), (0.05, 0.12)),
       ('stocks', (5, 10), (0.05, 0.12)), ('moon', (4, 10), (0.04, 0.1)), ('whale', (4, 10), (0.04, 0.1)),
       ('how long', (3, 6), (0.04, 0.1)), ('fenek', (3, 6), (0.04, 0.1)), ('bigger', (3, 6), (0.04, 0.1)), ('fox', (3, 6), (0.04, 0.1)),
       ('maya', (2, 5), (0.03, 0.08)), ('fenektr', (0.3, 1), (0.01, 0.03)), ('konuşan', (0.3, 1), (0.01, 0.03))]
RPM_DEFAULT = ((0.5, 2), (0.02, 0.06))      # animasyon / genel


def rpm_for(name):
    n = name.lower()
    for key, lr, sr in RPM:
        if key in n: return lr, sr
    return RPM_DEFAULT


def iso_dur(d):
    import re as _re
    m = _re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d or '')
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0


def long_stats(yt, uploads):
    """(uzun video izlenme saati tahmini, uzun video izlenme payı). Uzun = 3 dk+; izlenme süresi ≈ izlenme × süre × %35 (tahmin)."""
    ids, tok = [], None
    for _ in range(6):
        r = yt.playlistItems().list(part='contentDetails', playlistId=uploads, maxResults=50, pageToken=tok).execute()
        ids += [i['contentDetails']['videoId'] for i in r.get('items', [])]; tok = r.get('nextPageToken')
        if not tok: break
    hrs = lv = tv = 0
    for i in range(0, len(ids), 50):
        for v in yt.videos().list(part='statistics,contentDetails,status', id=','.join(ids[i:i + 50])).execute().get('items', []):
            if v['status'].get('privacyStatus') != 'public': continue
            vc = int(v['statistics'].get('viewCount', 0)); tv += vc; d = iso_dur(v['contentDetails'].get('duration'))
            if d >= 180: lv += vc; hrs += vc * d * 0.35 / 3600
    return hrs, (lv / tv if tv else 0)


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


SEARCH_SEEDS = {'Bloop': ['normal vs psychopath', 'funny animation'], 'Dex': ['types of people'],
                'Fruit Drama Club': ['talking fruit'], 'Fenek': ['almanca'], 'German with Fenek': ['learn german', 'german a1'],
                'Maya': ['diy pallet'], 'DebtLab': ['pay off debt'], 'Paw Rivals': ['cat vs dog'], 'Fox Run': ['reaction test'],
                'Why Stocks': ['stocks to buy'], 'Moon/Whale': ['crypto news'], 'Konuşan Fruits': ['türk aileleri']}


def search_trends():
    """YouTube arama kutusu önerileri (herkese açık): başlıkları aranan kelimelere göre güncel tutmak için."""
    import requests
    out = []
    for ch, seeds in SEARCH_SEEDS.items():
        sug = []
        for q in seeds:
            try:
                r = requests.get('https://suggestqueries.google.com/complete/search',
                                 params={'client': 'firefox', 'ds': 'yt', 'hl': 'tr' if ch == 'Fenek' else 'en', 'q': q}, timeout=10)
                sug += [x for x in r.json()[1][1:6] if x not in sug]
            except Exception:
                pass
        if sug:
            out.append(f"• <b>{ch}</b>: " + html.escape(' | '.join(sug[:6])))
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
    for c, v in (json.loads(HIST.read_text()) if HIST.exists() else {}).items():
        by_id.setdefault(c, v.get('name', c))
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
        try:
            lhrs, lshare = long_stats(yt, uploads)
        except Exception:
            lhrs, lshare = p.get('long_hours', 0), p.get('long_share', 0)
        snap[cid] = {'name': ch['snippet']['title'].strip(), 'subs': subs, 'views': views, 'date': now.strftime('%Y-%m-%d'),
                     'long_hours': round(lhrs), 'long_share': round(lshare, 3)}
        rows.append(dict(name=html.escape(ch['snippet']['title'].strip()), subs=subs, dsubs=subs - p.get('subs', subs),
                         views=views, dviews=views - p.get('views', views), n=len(week),
                         med=int(statistics.median(wv)) if wv else 0,
                         days=max(1.0, (now - datetime.strptime(p['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)).days) if p.get('date') else 7.0,
                         lhrs=lhrs, dlhrs=lhrs - p.get('long_hours', lhrs), lshare=lshare, title=ch['snippet']['title'].strip(),
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
    lines += ['', '💰 <b>Para kazanma yolu</b> (1.000 abone + 4.000 saat uzun video, ya da 90 günde 10M Short)']
    money_rows = []
    for r in sorted(rows, key=lambda r: -r['subs']):
        lr, sr = rpm_for(r['title']); k7 = 7 / r['days']; mviews = r['dviews'] * k7 * 4.3
        lo = mviews * (r['lshare'] * lr[0] + (1 - r['lshare']) * sr[0]) / 1000
        hi = mviews * (r['lshare'] * lr[1] + (1 - r['lshare']) * sr[1]) / 1000
        subs_ok, hrs_ok, shorts_ok = r['subs'] >= 1000, r['lhrs'] >= 4000, r['dviews'] * k7 * 13 >= 10_000_000
        def eta(left, per_week):
            if left <= 0: return 'tamam'
            if per_week <= 0: return 'büyüme yok'
            w = left / per_week
            return f'~{w:.0f} hafta' if w < 52 else '1 yıldan fazla'
        e_subs = eta(1000 - r['subs'], r['dsubs'] * k7); e_hrs = eta(4000 - r['lhrs'], r['dlhrs'] * k7)
        status = '✅ BAŞVURULABİLİR' if subs_ok and (hrs_ok or shorts_ok) else f"abone {r['subs']}/1000 ({e_subs}) · saat ~{r['lhrs']:.0f}/4000 ({e_hrs})"
        lines.append(f"• <b>{r['name']}</b>: {status}")
        lines.append(f"   açılınca bu hızla ≈ ${lo:,.0f}–{hi:,.0f}/ay (uzun RPM ${lr[0]}–{lr[1]})")
        money_rows.append((lo, hi))
    lines.append(f"Toplam potansiyel (hepsi açık olsaydı, bu haftanın hızıyla): ${sum(a for a, _ in money_rows):,.0f}–{sum(b for _, b in money_rows):,.0f}/ay")
    lines.append('<i>Saat = izlenme × süre × %35 tahmini (gerçeği Studio’da). RPM sektör ortalaması; gerçek RPM para kazanma açılınca görünür.</i>')
    reqs = viewer_requests(week_ago)
    if reqs:
        lines += ['', '💡 <b>İzleyici istekleri (bu hafta)</b>'] + [f'• {html.escape(r)}' for r in reqs[:15]]
    trends = search_trends()
    if trends:
        lines += ['', '🔎 <b>Bu hafta en çok aranan (YouTube önerileri)</b>'] + trends
    HIST.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if notify.enabled():                                         # Telegram 4096 karakter sınırı: satır satır parçala
        chunk = ''
        for l in lines:
            if len(chunk) + len(l) + 1 > 3900:
                notify._call('sendMessage', text=chunk, parse_mode='HTML', disable_web_page_preview='true'); chunk = ''
            chunk += l + '\n'
        if chunk.strip():
            notify._call('sendMessage', text=chunk, parse_mode='HTML', disable_web_page_preview='true')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
