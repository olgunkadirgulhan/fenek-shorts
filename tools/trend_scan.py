"""Viral format taraması (sadece okuma): her arama için son 30 günün en çok izlenen Shorts'ları →
medyan izlenme, 100K+ oranı, farklı kanal sayısı (tek kanalın tekelinde mi, herkes yapabiliyor mu).
    python tools/trend_scan.py "query 1|query 2|..."   (arama başına ~101 kota birimi)
"""
import json, os, re, statistics, sys
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def dur(s):
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    return (int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + int(m[3] or 0)) if m else 0


def main():
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'], token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    out = {}
    for q in [x.strip() for x in sys.argv[1].split('|') if x.strip()]:
        try:
            items = yt.search().list(part='id', q=q, type='video', videoDuration='short', order='viewCount',
                                     publishedAfter=after, maxResults=50, relevanceLanguage='en').execute()['items']
            ids = [i['id']['videoId'] for i in items]
            vids = yt.videos().list(part='snippet,statistics,contentDetails', id=','.join(ids)).execute()['items'] if ids else []
        except Exception as e:
            print(f'{q}: hata {str(e)[:120]}'); continue
        vids = [v for v in vids if dur(v['contentDetails']['duration']) <= 180]
        views = [int(v['statistics'].get('viewCount', 0)) for v in vids]
        chans = {v['snippet']['channelId'] for v in vids if int(v['statistics'].get('viewCount', 0)) >= 100000}
        top = sorted(vids, key=lambda v: -int(v['statistics'].get('viewCount', 0)))[:3]
        r = dict(n=len(views), median=int(statistics.median(views)) if views else 0,
                 over100k=sum(x >= 100000 for x in views), channels_100k=len(chans),
                 top=[(int(v['statistics'].get('viewCount', 0)), v['snippet']['channelTitle'], v['snippet']['title'][:70]) for v in top])
        out[q] = r
        print(f"{q:40} n{r['n']:>3} medyan {r['median']:>9,} | 100K+ {r['over100k']:>2} video / {r['channels_100k']:>2} kanal | {r['top'][0] if r['top'] else ''}", flush=True)
    json.dump(out, open('trend_scan.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
