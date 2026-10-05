"""Kanalların herkese açık istatistikleri, resmi YouTube API ile (sadece okuma, hiçbir şey değiştirmez).
    python tools/channel_stats.py VIDEO_ID [VIDEO_ID ...]   # her kanaldan bir video yeter
"""
import os
import statistics
import sys
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def main():
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'], token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    seeds = yt.videos().list(part='snippet', id=','.join(sys.argv[1:])).execute()['items']
    now = datetime.now(timezone.utc)
    for ch_id in dict.fromkeys(s['snippet']['channelId'] for s in seeds):
        ch = yt.channels().list(part='snippet,statistics,contentDetails,status', id=ch_id).execute()['items'][0]
        st = ch['statistics']
        uploads, ids, tok = ch['contentDetails']['relatedPlaylists']['uploads'], [], None
        while True:
            r = yt.playlistItems().list(part='contentDetails', playlistId=uploads, maxResults=50, pageToken=tok).execute()
            ids += [i['contentDetails']['videoId'] for i in r['items']]
            tok = r.get('nextPageToken')
            if not tok:
                break
        vids = []
        for k in range(0, len(ids), 50):
            vids += yt.videos().list(part='snippet,statistics,status,contentDetails', id=','.join(ids[k:k + 50])).execute()['items']
        pub = [v for v in vids if v['status']['privacyStatus'] == 'public']
        views = [int(v['statistics'].get('viewCount', 0)) for v in pub]
        likes = sum(int(v['statistics'].get('likeCount', 0)) for v in pub)
        comments = sum(int(v['statistics'].get('commentCount', 0)) for v in pub)
        first = min((v['snippet']['publishedAt'] for v in vids), default='')
        print(f"\n=== {ch['snippet']['title']} | abone {st.get('subscriberCount')} | toplam izlenme {st.get('viewCount')}"
              f" | video {len(vids)} (public {len(pub)}) | medyan {statistics.median(views) if views else 0}"
              f" | beğeni {likes} | yorum {comments} | ilk video {first[:10]} | madeForKids {ch['status'].get('madeForKids')}")
        pub.sort(key=lambda v: -int(v['statistics'].get('viewCount', 0)))
        for tag, part in (('EN İYİ', pub[:5]), ('EN KÖTÜ', pub[-3:] if len(pub) > 5 else [])):
            for v in part:
                age = (now - datetime.fromisoformat(v['snippet']['publishedAt'].replace('Z', '+00:00'))).days
                print(f"  {tag:7} {int(v['statistics'].get('viewCount', 0)):>7} izl | {age:>2}g | {v['contentDetails']['duration']:>8} | {v['snippet']['title'][:75]}")


if __name__ == '__main__':
    main()
