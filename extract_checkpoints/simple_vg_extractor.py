#!/usr/bin/env python3
"""
simple_vg_extractor.py

Super-simple script:
- Has a dictionary of games -> YouTube URLs.
- Creates a directory for each game under ./vgbench_outputs/<Game_Name>/
- Downloads the YouTube video (mp4) with yt-dlp.
- Extracts one screenshot every 10 seconds across the whole video using ffmpeg.
- Saves images and a CSV manifest in the game's folder.

Requirements:
    pip install yt-dlp
    # macOS:
    brew install ffmpeg
"""

import csv
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# ---------- Config (edit these) ----------------------------------------------

GAMES: Dict[str, str] = {
    "Doom 2": "https://www.youtube.com/watch?v=nhmRxFf02JA",
    "Pokemon Crystal": "https://www.youtube.com/watch?v=HQEaaIuyKAM",
    "Kirby": "https://www.youtube.com/watch?v=n8CSolb0hjc",
}

OUTPUT_ROOT = Path("./vgbench_outputs")
INTERVAL_SECONDS = 10.0  # take a frame every N seconds

# ---------- Helpers -----------------------------------------------------------

SAFE_RE = re.compile(r'[^A-Za-z0-9._ -]+')

def safe_name(name: str) -> str:
    return SAFE_RE.sub('_', name).strip().replace(' ', '_')

def ytdlp_extract_info(url: str) -> dict:
    import yt_dlp
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def ytdlp_download_mp4(url: str, out_dir: Path) -> Path:
    """Download the best mp4 (or best available) and return the file path."""
    import yt_dlp
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "quiet": True,
        "noprogress": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp often puts final path in requested_downloads
        if "requested_downloads" in info and info["requested_downloads"]:
            p = info["requested_downloads"][-1].get("filepath")
            if p:
                return Path(p)
        vid = info.get("id")
        ext = info.get("ext", "mp4")
        return out_dir / f"{vid}.{ext}"

def ffmpeg_grab_frame(video_path: Path, t_seconds: float, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{t_seconds:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        # Retry with -ss after -i (more accurate, slower)
        cmd2 = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-ss", f"{t_seconds:.3f}",
            "-frames:v", "1",
            "-q:v", "2",
            str(out_path),
        ]
        subprocess.run(cmd2, check=True)

def compute_interval_times(duration: float, step: float) -> List[float]:
    times = []
    if duration <= 0 or step <= 0:
        return times
    t = 0.0
    # Stop a bit before the very end to avoid black tail frames
    end_time = max(0.0, duration - 0.25)
    while t <= end_time + 1e-6:
        times.append(round(t, 3))
        t += step
    return times

# ---------- Main --------------------------------------------------------------

def process_game(game_name: str, url: str) -> None:
    print(f"[info] Processing {game_name} -> {url}")
    game_dir = OUTPUT_ROOT / safe_name(game_name)
    images_dir = game_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Pull metadata (duration for interval list)
    info = ytdlp_extract_info(url)
    duration = float(info.get("duration") or 0.0)
    video_title = info.get("title") or "untitled"
    video_id = info.get("id") or "unknown"
    print(f"[info] Title: {video_title}  | Duration: {duration:.1f}s  | ID: {video_id}")

    # Download the video
    video_path = ytdlp_download_mp4(url, game_dir)
    print(f"[info] Downloaded: {video_path}")

    # Compute times
    times = compute_interval_times(duration, INTERVAL_SECONDS)
    if not times:
        print("[warn] Could not compute interval times; writing a placeholder at 5s.")
        times = [5.0]

    # Extract frames + CSV
    csv_path = game_dir / "checkpoints.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_seconds", "image_path"])
        for i, t in enumerate(times, 1):
            # slight nudge to avoid black frames
            t_eff = max(0.0, t + 0.25)
            img_path = images_dir / f"frame_{i:05d}_{int(t_eff):06d}.jpg"
            try:
                ffmpeg_grab_frame(video_path, t_eff, img_path)
                writer.writerow([f"{t:.3f}", str(img_path)])
            except Exception as e:
                print(f"[error] ffmpeg at {t_eff}s: {e}")

    print(f"[ok] {game_name}: saved {len(times)} frames to {images_dir} and CSV {csv_path}")

def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, url in GAMES.items():
        try:
            process_game(name, url)
        except Exception as e:
            print(f"[error] Failed {name}: {e}")

if __name__ == "__main__":
    main()
