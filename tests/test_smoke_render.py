from pathlib import Path
import subprocess

from trendsubs.core.models import RenderOptions
from trendsubs.core.render_service import render_subtitled_video


def test_smoke_render_produces_output_mp4(tmp_path: Path):
    video_path = tmp_path / "input.mp4"
    srt_path = tmp_path / "input.srt"
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    output_path = tmp_path / "output.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=640x360:d=2",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(video_path),
        ],
        check=True,
        capture_output=True,
    )
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\nHello brave world\n",
        encoding="utf-8",
    )

    render_subtitled_video(
        video_path=video_path,
        srt_path=srt_path,
        output_path=output_path,
        options=RenderOptions(
            preset="social-pop",
            font_path=str(font_path),
            accent_color="#FFD84D",
            font_size=48,
            bottom_margin=40,
            keep_ass=True,
        ),
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
