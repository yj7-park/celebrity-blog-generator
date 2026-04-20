"""
Video slideshow generator using FFmpeg.
Adapted from Blog-main/VideoMaker.py

Creates an MP4 slideshow from a list of image file paths.
Each image is displayed for 4 seconds with 1-second fade in/out transitions.
"""
from __future__ import annotations
import os
import subprocess
import time
from typing import List


def make_slideshow(
    image_paths: List[str],
    output_path: str,
    duration_per_image: int = 4,
    fade_duration: float = 1.0,
) -> str:
    """
    Create an MP4 slideshow from image_paths using FFmpeg.

    Args:
        image_paths:        Local file paths to images (jpg/png).
        output_path:        Destination .mp4 file path.
        duration_per_image: Seconds each image is shown (default 4).
        fade_duration:      Fade in/out duration in seconds (default 1).

    Returns:
        Absolute path to the created MP4 file.

    Raises:
        FileNotFoundError: If ffmpeg is not found.
        RuntimeError:      If ffmpeg exits with non-zero status or times out.
    """
    if not image_paths:
        raise ValueError("image_paths must not be empty")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if os.path.exists(output_path):
        return output_path

    n = len(image_paths)
    fade_st = duration_per_image - fade_duration  # fade-out start time

    # Build ffmpeg input options: -loop 1 -t {dur} -i "{path}"
    inputs = " ".join(
        f'-loop 1 -t {duration_per_image} -i "{p}"' for p in image_paths
    )

    if n == 1:
        # Single image — simple fade in/out
        filter_complex = (
            f"[0:v]fade=t=in:st=0:d={fade_duration},"
            f"fade=t=out:st={fade_st}:d={fade_duration}[v]"
        )
    else:
        # First image: fade out only
        parts = [f"[0:v]fade=t=out:st={fade_st}:d={fade_duration}[v0]; "]
        # Middle + last images: fade in + fade out
        for i in range(1, n):
            parts.append(
                f"[{i}:v]fade=t=in:st=0:d={fade_duration},"
                f"fade=t=out:st={fade_st}:d={fade_duration}[v{i}]; "
            )
        concat_inputs = "".join(f"[v{i}]" for i in range(n))
        parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0,format=rgb24[v]")
        filter_complex = "".join(parts)

    cmd = (
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[v]" "{output_path}"'
    )

    proc = subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (code {proc.returncode}):\n{proc.stderr.decode(errors='replace')}"
        )

    return os.path.abspath(output_path)


def make_slideshow_from_urls(
    image_urls: List[str],
    output_path: str,
    tmp_dir: str = "",
    **kwargs,
) -> str:
    """
    Download images from URLs then create a slideshow.

    Args:
        image_urls: HTTP/HTTPS image URLs.
        output_path: Destination .mp4 path.
        tmp_dir:    Directory for downloaded images (uses output dir if empty).

    Returns:
        Absolute path to the created MP4 file.
    """
    import requests
    from pathlib import Path

    base = tmp_dir or os.path.dirname(os.path.abspath(output_path))
    os.makedirs(base, exist_ok=True)

    local_paths: List[str] = []
    for idx, url in enumerate(image_urls):
        ext = url.split("?")[0].rsplit(".", 1)[-1]
        if ext.lower() not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        dest = os.path.join(base, f"slide_{idx:03d}.{ext}")
        if not os.path.exists(dest):
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                Path(dest).write_bytes(r.content)
            except Exception as e:
                continue  # skip failed images
        if os.path.exists(dest):
            local_paths.append(dest)

    if not local_paths:
        raise RuntimeError("이미지를 다운로드할 수 없습니다.")

    return make_slideshow(local_paths, output_path, **kwargs)
