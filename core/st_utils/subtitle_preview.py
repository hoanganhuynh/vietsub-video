import os
import platform
import subprocess
import tempfile

from core.utils import load_key


def _font_name():
    if platform.system() == "Darwin":
        return "Arial Unicode MS"
    if platform.system() == "Linux":
        return "NotoSansCJK-Regular"
    return "Arial"


def _build_sub_vf(src_srt: str, trans_srt: str) -> str:
    s = load_key("subtitle_style") or {}
    font = _font_name()
    src_size   = s.get("src_font_size",    15)
    src_col    = s.get("src_font_color",   "&HFFFFFF")
    src_out    = s.get("src_outline_color","&H000000")
    trans_size = s.get("trans_font_size",  17)
    trans_col  = s.get("trans_font_color", "&H00FFFF")
    trans_out  = s.get("trans_outline_color", "&H000000")
    trans_back = s.get("trans_back_color", "&H33000000")
    margin_v   = s.get("margin_v", 27)
    return (
        f"subtitles=filename='{src_srt}':force_style='FontSize={src_size},"
        f"FontName={font},PrimaryColour={src_col},OutlineColour={src_out},"
        f"OutlineWidth=1,ShadowColour=&H80000000,BorderStyle=1',"
        f"subtitles=filename='{trans_srt}':force_style='FontSize={trans_size},"
        f"FontName={font},PrimaryColour={trans_col},OutlineColour={trans_out},"
        f"OutlineWidth=1,BackColour={trans_back},Alignment=2,"
        f"MarginV={margin_v},BorderStyle=4'"
    )


def _logo_inputs_and_filter(base_vf: str, input_count: int):
    """Return extra ffmpeg inputs and filter_complex string if logo is enabled."""
    logo_path = load_key("logo.path") or ""
    if not (load_key("logo.enabled") and logo_path and os.path.exists(logo_path)):
        return [], None
    w      = load_key("logo.width")  or 150
    margin = load_key("logo.margin") or 20
    pos_map = {
        "top-left":     f"{margin}:{margin}",
        "top-right":    f"W-w-{margin}:{margin}",
        "bottom-left":  f"{margin}:H-h-{margin}",
        "bottom-right": f"W-w-{margin}:H-h-{margin}",
    }
    pos = pos_map.get(load_key("logo.position") or "bottom-right", f"W-w-{margin}:H-h-{margin}")
    fc = f"[0:v]{base_vf}[sub];[{input_count}:v]scale={w}:-1[logo];[sub][logo]overlay={pos}"
    return ["-i", logo_path], fc


def generate_preview(timestamp_pct: float = 0.3) -> bytes | None:
    """Extract one frame at timestamp_pct of the video with subtitles (and logo) overlaid."""
    try:
        from core._1_ytdlp import find_video_files
        video_file = find_video_files()
    except Exception:
        return None

    src_srt   = os.path.abspath("output/src.srt")
    trans_srt = os.path.abspath("output/trans.srt")
    if not os.path.exists(src_srt) or not os.path.exists(trans_srt):
        return None

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_file],
        capture_output=True, text=True,
    )
    try:
        ts = float(probe.stdout.strip()) * timestamp_pct
    except Exception:
        ts = 60.0

    vf = _build_sub_vf(src_srt, trans_srt)
    logo_inputs, fc = _logo_inputs_and_filter(vf, 1)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        out = tmp.name

    if fc:
        cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", video_file,
               *logo_inputs, "-filter_complex", fc, "-vframes", "1", out]
    else:
        cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", video_file,
               "-vf", vf, "-vframes", "1", out]

    subprocess.run(cmd, capture_output=True)

    if os.path.exists(out) and os.path.getsize(out) > 0:
        with open(out, "rb") as f:
            data = f.read()
        os.unlink(out)
        return data
    return None
