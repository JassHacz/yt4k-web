"""
4K Downloader - Web Edition
vidssave-style YouTube downloader (backend on yt-dlp).

Run:
    pip install -r requirements.txt
    python app.py
    open http://localhost:5000

Use only for your own videos, content you have permission for, or Creative Commons videos.
"""
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory
import yt_dlp

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Optional: if the server IP gets "Sign in to confirm you're not a bot",
# set this to any browser installed on the machine, e.g. "chrome", "firefox", "edge"
COOKIES_FROM_BROWSER = os.environ.get("YTDLP_COOKIES_BROWSER", "")

MAX_CONCURRENT = 2          # parallel downloads limit
FILE_LIFETIME_MIN = 120     # old files will be deleted after this many minutes

QUALITIES = [
    {"id": "2160", "label": "4K (2160p)", "icon": "🎬", "type": "video", "ext": "mp4"},
    {"id": "1440", "label": "1440p (2K)", "icon": "🖥️", "type": "video", "ext": "mp4"},
    {"id": "1080", "label": "1080p Full HD", "icon": "📺", "type": "video", "ext": "mp4"},
    {"id": "720",  "label": "720p HD", "icon": "📱", "type": "video", "ext": "mp4"},
    {"id": "360",  "label": "360p (Data saver)", "icon": "💾", "type": "video", "ext": "mp4"},
    {"id": "mp3",  "label": "MP3 (Audio)", "icon": "🎧", "type": "audio", "ext": "mp3"},
]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # tiny POSTs only (URLs)

JOBS = {}  # job_id -> dict(state)
JOBS_LOCK = threading.Lock()


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
class _NullLog:
    """Silence yt-dlp console spam (progress still goes through progress_hooks)."""
    def debug(self, msg):  # noqa: D102
        pass
    def warning(self, msg):  # noqa: D102
        pass
    def error(self, msg):  # noqa: D102
        pass


def base_ydl_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "logger": _NullLog(),
        # YouTube resets slow connections — so retries are a must
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
    }
    if COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)
    return opts


def friendly_error(msg: str) -> str:
    low = msg.lower()
    if "sign in to confirm" in low or "not a bot" in low:
        return ("YouTube blocked this server IP (bot protection). "
                "Set YTDLP_COOKIES_BROWSER env var or run from your own PC.")
    if "video unavailable" in low:
        return "Video unavailable or private."
    if "unsupported url" in low:
        return "This URL is not supported. Paste a valid YouTube link."
    if "age" in low and "confirm" in low:
        return "Age-restricted video. Login cookies needed."
    return msg


def start_job(url, quality_id):
    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        running = sum(1 for j in JOBS.values() if j.get("state") in ("downloading", "merging"))
        if running >= MAX_CONCURRENT:
            return None, "Server busy — try again in a minute."
        JOBS[job_id] = {
            "state": "queued", "percent": 0, "speed": "", "eta": "",
            "title": "", "filename": "", "error": "", "url": url, "quality": quality_id,
        }
    threading.Thread(target=run_job, args=(job_id, url, quality_id), daemon=True).start()
    return job_id, None


def run_job(job_id, url, quality_id):
    q = next((x for x in QUALITIES if x["id"] == quality_id), QUALITIES[2])
    job = JOBS[job_id]

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            with JOBS_LOCK:
                job["state"] = "downloading"
                job["percent"] = round(pct, 1)
                job["speed"] = (d.get("_speed_str") or "").strip()
                job["eta"] = (d.get("_eta_str") or "").strip()
        elif d["status"] == "finished":
            with JOBS_LOCK:
                job["state"] = "merging"
                job["percent"] = 99
                job["eta"] = ""

    opts = base_ydl_opts()
    opts.update({
        "outtmpl": str(DOWNLOAD_DIR / "%(title).80s.%(ext)s"),
        "progress_hooks": [hook],
    })

    if q["type"] == "audio":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        h = int(quality_id)
        opts.update({
            "format": f"bv*[height<={h}]+ba/b[height<={h}]",
            "merge_output_format": q["ext"],
        })

    try:
        with JOBS_LOCK:
            job["state"] = "starting"
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # final merged filepath (works for vp9/opus merged files too)
            filepath = None
            if isinstance(info, dict):
                rd = info.get("requested_downloads") or []
                if rd:
                    filepath = rd[0].get("filepath")
            if not filepath:
                filepath = str(DOWNLOAD_DIR / f"{info.get('title','video')}.{q['ext']}")

        with JOBS_LOCK:
            job["state"] = "done"
            job["percent"] = 100
            job["title"] = info.get("title", "video")
            job["filename"] = Path(filepath).name
            job["filepath"] = filepath
            job["filesize"] = Path(filepath).stat().st_size if Path(filepath).exists() else 0
    except Exception as e:  # noqa: BLE001
        with JOBS_LOCK:
            job["state"] = "error"
            job["error"] = friendly_error(str(e))


# ----------------------------------------------------------------------------
# file cleanup: delete files older than FILE_LIFETIME_MIN
# ----------------------------------------------------------------------------
def cleanup_loop():
    while True:
        time.sleep(600)
        limit = time.time() - FILE_LIFETIME_MIN * 60
        for f in DOWNLOAD_DIR.glob("*"):
            try:
                if f.is_file() and f.stat().st_mtime < limit:
                    f.unlink()
            except OSError:
                pass


threading.Thread(target=cleanup_loop, daemon=True).start()


# ----------------------------------------------------------------------------
# routes
# ----------------------------------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html", qualities=QUALITIES)


@app.get("/favicon.ico")
def favicon():
    return send_file(BASE_DIR / "static" / "logo.svg", mimetype="image/svg+xml")


@app.post("/fetch")
def fetch():
    url = (request.json or {}).get("url", "").strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify(error="Please paste a valid YouTube URL."), 400
    opts = base_ydl_opts()
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify(
            title=info.get("title") or "",
            thumbnail=info.get("thumbnail") or "",
            duration=info.get("duration") or 0,
            uploader=info.get("uploader") or "",
        )
    except Exception as e:  # noqa: BLE001
        return jsonify(error=friendly_error(str(e))), 400


@app.post("/download")
def download():
    data = request.json or {}
    url = (data.get("url") or "").strip()
    quality = (data.get("quality") or "1080").strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify(error="Invalid URL."), 400
    job_id, err = start_job(url, quality)
    if err:
        return jsonify(error=err), 429
    return jsonify(job_id=job_id)


@app.get("/progress/<job_id>")
def progress(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify(state="gone"), 404
    return jsonify(
        state=job.get("state"), percent=job.get("percent"),
        speed=job.get("speed"), eta=job.get("eta"),
        title=job.get("title"), filename=job.get("filename"),
        filesize=job.get("filesize", 0), error=job.get("error"),
    )


@app.get("/file/<job_id>")
def serve_file(job_id):
    job = JOBS.get(job_id)
    if not job or job.get("state") not in ("done", "delivered"):
        return jsonify(error="File not ready (or already removed)."), 404
    if job.get("state") == "delivered":
        return jsonify(error="Link already used — press Download again."), 410
    path = job.get("filepath")
    if not path or not Path(path).exists():
        return jsonify(error="File expired — download again."), 404

    name = job.get("filename") or Path(path).name
    job["state"] = "delivered"  # one download per job

    # delete the file ~60s later so disk doesn't fill up
    def _cleanup():
        time.sleep(60)
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
        with JOBS_LOCK:
            job["state"] = "gone"

    threading.Thread(target=_cleanup, daemon=True).start()
    return send_file(path, as_attachment=True, download_name=name)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  [4K Downloader] web app running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
