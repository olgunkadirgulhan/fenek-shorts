"""Telegram botunu bağla (bir kez, kendi bilgisayarında):
  1. Telegram'da @BotFather → /newbot → bir ad ver → verdiği TOKEN'ı kopyala
  2. python tools/telegram_setup.py            (birden fazla kanal: --repo a/b --repo c/d)
  3. İstendiğinde token'ı yapıştır (ekranda görünmez), sonra bota Telegram'dan /start yaz
Token ve sohbet numarası doğrudan GitHub Secrets'a yazılır (dosyaya/ekrana yazılmaz), bota deneme mesajı gelir.
"""
import argparse
import getpass
import subprocess
import sys
import time

import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', action='append', help='GitHub repo(ları); varsayılan olgunkadirgulhan/fenek-shorts')
    a = ap.parse_args()
    repos = a.repo or ['olgunkadirgulhan/fenek-shorts']
    token = getpass.getpass('BotFather token (yapıştır, görünmez): ').strip()
    api = f'https://api.telegram.org/bot{token}/'
    me = requests.get(api + 'getMe', timeout=20).json()
    if not me.get('ok'):
        sys.exit('Token geçersiz. BotFather\'dan tekrar kopyala.')
    name = me['result']['username']
    print(f'Bot bulundu: @{name}\nŞimdi Telegram\'da @{name} ile sohbeti aç ve /start yaz (3 dk bekliyorum)...')
    chat = None
    for _ in range(90):
        for u in requests.get(api + 'getUpdates', timeout=20).json().get('result', []):
            m = u.get('message') or {}
            if m.get('chat', {}).get('type') == 'private':
                chat = m['chat']['id']
        if chat:
            break
        time.sleep(2)
    if not chat:
        sys.exit('Mesaj gelmedi. Bota /start yazıp tekrar çalıştır.')
    for repo in repos:
        subprocess.run(['gh', 'secret', 'set', 'TELEGRAM_BOT_TOKEN', '--repo', repo], input=token, text=True, check=True)
        subprocess.run(['gh', 'secret', 'set', 'TELEGRAM_CHAT_ID', '--repo', repo], input=str(chat), text=True, check=True)
        print(f'✓ {repo}: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID kaydedildi')
    requests.post(api + 'sendMessage', data={'chat_id': chat, 'text': '✅ Bağlandı! Kanallarına yüklenen her video buraya gelecek, '
                                             'TikTok ve Instagram açıklamalarıyla birlikte. 🦊'}, timeout=20)
    print('Deneme mesajı gönderildi. Telegram\'a bak!')


if __name__ == '__main__':
    main()
