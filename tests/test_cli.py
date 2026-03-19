from pathlib import Path

from typer.testing import CliRunner

from trendsubs.cli import app


def test_cli_render_invokes_shared_service(tmp_path, monkeypatch):
    runner = CliRunner()
    video_path = tmp_path / "in.mp4"
    srt_path = tmp_path / "in.srt"
    font_path = tmp_path / "font.ttf"
    output_path = tmp_path / "out.mp4"
    video_path.write_bytes(b"video")
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    font_path.write_bytes(b"font")

    called = {}

    def fake_render(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("trendsubs.cli.render_subtitled_video", fake_render)

    result = runner.invoke(
        app,
        [
            "render",
            "--video",
            str(video_path),
            "--subs",
            str(srt_path),
            "--out",
            str(output_path),
            "--font",
            str(font_path),
        ],
    )

    assert result.exit_code == 0
    assert called["video_path"] == video_path
    assert called["srt_path"] == srt_path
    assert called["output_path"] == output_path


def test_cli_gui_launches_desktop_app(monkeypatch):
    runner = CliRunner()
    called = {"launched": False}

    def fake_launch():
        called["launched"] = True

    monkeypatch.setattr("trendsubs.cli.launch_gui", fake_launch)

    result = runner.invoke(app, ["gui"])

    assert result.exit_code == 0
    assert called["launched"] is True
