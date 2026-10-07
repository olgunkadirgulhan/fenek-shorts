"""Diğer kanalların günün videosunu Fenek botuyla Telegram'a yollar (her kanalın ayrı bot token'ı gerekmez).

Kaynak repolar günün ilk videosunu 'social-<run_id>' artifact'ı olarak bırakır: video.mp4 + post.json
({channel, title, url, tiktok, instagram}) ya da deneme için post.json {"videos": [{"file", "caption"}], "note"}.
Bu betik saatlik çalışır; tüm kanalların yeni videosu hazır olunca HEPSİNİ BİRLİKTE gönderir (biri gelmezse\nRELAY_DEADLINE_H saatinde, UTC, varsayılan 22, hazır olanı gönderir) ve telegram_relay.json'a işler.
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
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    repos = [r.strip() for r in os.environ.get('RELAY_REPOS', '').split(',') if r.strip()]
    pending = {}                                             # repo -> gönderilmemiş artifact'lar (eskiden yeniye)
    for repo in repos:
        try:
            found = sorted(artifacts(repo, since), key=lambda a: a['created_at'])
        except Exception as e:
            print(f'{repo}: artifact listesi alınamadı: {e}'); continue
        new = [a for a in found if f"{repo}#{a['id']}" not in state['sent']]
        if new:
            pending[repo] = new
    if not pending:
        print('gönderilecek video yok'); return
    # Hepsi birlikte: her kanalın videosu hazır olunca tek seferde gönder. Biri gelmezse son saatte (veya bekleyen
    # video 20 saati geçince) hazır olanı yalnız gönder — video kaybolmasın.
    send_h = int(os.environ.get('RELAY_SEND_H', '15'))     # 15 UTC = Türkiye 18:00: günün videoları bu saatte
    if now.hour < send_h:
        print(f'gönderim saati {send_h}:00 UTC, bekleniyor'); return
    deadline = int(os.environ.get('RELAY_DEADLINE_H', '22'))
    oldest = min(datetime.fromisoformat(a['created_at'].replace('Z', '+00:00')) for xs in pending.values() for a in xs)
    if len(pending) < len(repos) and now.hour < deadline and now - oldest < timedelta(hours=30):
        print(f"bekleniyor: hazır {sorted(pending)} / {len(repos)} kanal"); return
    total = sum(len(xs) for xs in pending.values())
    if total > 1:
        notify.message(f"📦 Günün sosyal medya videoları ({total})")
    for repo in repos:
        for a in pending.get(repo, []):
            key = f"{repo}#{a['id']}"
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
