"""Tek seferlik hatırlatma: Bloop uzun bölümünün izlenmeleri + "yarın sıradaki bölüm, devam mı?" → Telegram.
    python tools/episode_reminder.py VIDEO_ID "yarın ne olacak"
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fenek import notify  # noqa: E402


def main():
    vid, nxt = sys.argv[1], sys.argv[2]
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'], token_uri='https://oauth2.googleapis.com/token')
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    it = yt.videos().list(part='snippet,statistics', id=vid).execute()['items'][0]
    st = it['statistics']
    hours = (datetime.now(timezone.utc) - datetime.fromisoformat(it['snippet']['publishedAt'].replace('Z', '+00:00'))).total_seconds() / 3600
    views = int(st.get('viewCount', 0))
    verdict = ('İyi gidiyor 👍' if views >= 1000 else 'Orta 🙂' if views >= 300 else 'Zayıf 😐')
    text = (f"⏰ <b>Hatırlatma: Bloop uzun bölüm</b>\n\n"
            f"1. bölüm ({hours / 24:.1f} gün): <b>{views:,}</b> izlenme, {int(st.get('likeCount', 0)):,} beğeni, "
            f"{int(st.get('commentCount', 0))} yorum → {verdict}\n"
            f"https://youtu.be/{vid}\n\n{nxt}\n\nDevam mı? Claude'a yaz: <b>devam</b> ya da <b>dur</b>.")
    print(text)
    notify._call('sendMessage', text=text, parse_mode='HTML', disable_web_page_preview='true')


if __name__ == '__main__':
    main()
