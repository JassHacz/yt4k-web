# 🎬 4K Downloader — Web Edition

Un `yt4k_downloader.py` (desktop GUI) ku **vidssave.com-style web version**.
Flask + yt-dlp engine. Python matte podhum run panradhukku.

## Setup (Windows)

```bash
cd yt4k-web
pip install -r requirements.txt
python app.py
```

Aparam browser-la open pannu: **http://localhost:5000**

> ⚠️ 4K video + audio merge panradhukku **ffmpeg** PATH-la irukkanum:
> `winget install ffmpeg` (already install pannirukkandha onnume pannanum venam)

## Features

- 🎥 YouTube video info auto-fetch (thumbnail, title, uploader, duration)
- 🎬 Quality: 4K / 2K / 1080p / 720p / 360p
- 🎧 MP3 conversion (192kbps)
- 📊 Live download progress (speed + ETA)
- 🧹 Files auto-delete — server disk full aagave padadhu (2 mani neram old files)
- 📋 Clipboard paste button

## Hosting

### Personal use (recommended) — un PC + tunnel
> 📦 `cloudflared.exe` idha repo-la oru build artifact-ava matrum venum — idha download pannunga:
> https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
```bash
cloudflared tunnel --url http://localhost:5000
```
Idhu oru public https link kudukum — phone-lenthu access pannalam.
YouTube server un home IP — so **IP block issue illa**.
PC off aana site down aagum nu mattum gavanikka.

### VPS-la deploy pannia (24/7)
```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```
⚠️ **Aana nyabagam vachukokka:** VPS-la YouTube datacenter IP-ai block pannuvadhu oda
"Sign in to confirm you're not a bot" error varalam. Appuram:
- `YTDLP_COOKIES_BROWSER=chrome` env var set pannu, illa
- residential proxy (paid) use pannu, illa
- mela solla vachadha **un PC + tunnel** dhaan best.

## ⚠️ Legal Note
Idhu personal use-ku mattum. Copyright/unpermissioned content download pannadha —
un original script-la irundha adhey policy ithaaye.
