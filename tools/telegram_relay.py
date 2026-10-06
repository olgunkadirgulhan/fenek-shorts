"""Diğer kanalların günün videosunu Fenek botuyla Telegram'a yollar (her kanalın ayrı bot token'ı gerekmez).

Kaynak repolar günün ilk videosunu 'social-<run_id>' artifact'ı olarak bırakır: video.mp4 + post.json
({channel, title, url, tiktok, instagram}) ya da deneme için post.json {"videos": [{"file", "caption"}], "note"}.
Bu betik saatlik çalışır, yeni artifact'ları indirir, gönderir ve telegram_relay.json'a işler (tekrar gönderilmez).
Env: GITHUB_TOKEN, RELAY_REPOS (virgüllü), TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fenek import notify  # noqa: E402

STATE = ROOT / 'telegram_relay.json'
GH = 'https://api.github.com'
HDR = {'Authorization': f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", 'Accept': 'application/vnd.github+json'}


def artifacts(repo, since):
    r = requests.get(f'{GH}/repos/{repo}/actions/artifacts', headers=HDR, params={'per_page': 100}, timeout=30)
    r.raise_for_status()
    for a in r.json().get('artifacts', []):
        if a['name'].startswith('social-') and not a['expired'] and a['created_at'] >= since:
            yield a


def send(files, post):
    if post.get('videos'):                                   # deneme: birden çok video, sırayla
        for v in post['videos']:
            with io.BytesIO(files[v['file']]) as f:
                notify._call('sendVideo', files={'video': (v['file'], f, 'video/mp4')},
                             caption=v.get('caption', '')[:1000], supports_streaming='true')
        if post.get('note'):
            notify.message(post['note'])
        return
    with io.BytesIO(files['video.mp4']) as f:
        notify._call('sendDocument', files={'document': ('video.mp4', f, 'video/mp4')},
                     caption=f"🎬 {post['channel']} — günün videosu (TikTok/Instagram için)\n{post['title']}\n{post['url']}"[:1000])
    notify.copyable('🎵 TikTok açıklaması (kutuya dokun → kopyalanır):', post['tiktok'])
    notify.copyable('📸 Instagram açıklaması (kutuya dokun → kopyalanır):', post['instagram'])


def main():
    if not notify.enabled():
        sys.exit('TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID yok')
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'sent': []}
    since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    for repo in [r.strip() for r in os.environ.get('RELAY_REPOS', '').split(',') if r.strip()]:
        try:
            found = sorted(artifacts(repo, since), key=lambda a: a['created_at'])
        except Exception as e:
            print(f'{repo}: artifact listesi alınamadı: {e}'); continue
        for a in found:
            key = f"{repo}#{a['id']}"
            if key in state['sent']:
                continue
            z = requests.get(a['archive_download_url'], headers=HDR, timeout=300)
            if not z.ok:
                print(f'{key}: indirilemedi {z.status_code} {z.text[:200]}'); continue
            with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
                files = {Path(n).name: zf.read(n) for n in zf.namelist()}
            post = json.loads(files['post.json'])
            send(files, post)
            print(f"✓ {key}: {post.get('title') or post.get('note', '')[:60]}")
            state['sent'] = (state['sent'] + [key])[-300:]
            STATE.write_text(json.dumps(state, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
