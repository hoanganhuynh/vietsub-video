import os
import platform
import subprocess

import cv2
import numpy as np
from rich.console import Console

from core._1_ytdlp import find_video_files
from core.asr_backend.audio_preprocess import normalize_audio_volume
from core.utils import *
from core.utils.models import *

console = Console()

DUB_VIDEO = "output/output_dub.mp4"
DUB_SUB_FILE = 'output/dub.srt'
SRC_SUB_FILE = 'output/src.srt'
DUB_AUDIO = 'output/dub.mp3'

SRC_FONT_SIZE = 15
SRC_FONT_COLOR = '&HFFFFFF'
SRC_OUTLINE_COLOR = '&H000000'
SRC_OUTLINE_WIDTH = 1
SRC_SHADOW_COLOR = '&H80000000'

TRANS_FONT_SIZE = 17
TRANS_FONT_NAME = 'Arial'
SRC_FONT_NAME = 'Arial'
if platform.system() == 'Linux':
    TRANS_FONT_NAME = 'NotoSansCJK-Regular'
    SRC_FONT_NAME = 'NotoSansCJK-Regular'
if platform.system() == 'Darwin':
    TRANS_FONT_NAME = 'Arial Unicode MS'
    SRC_FONT_NAME = 'Arial Unicode MS'

TRANS_FONT_COLOR = '&H00FFFF'
TRANS_OUTLINE_COLOR = '&H000000'
TRANS_OUTLINE_WIDTH = 1
TRANS_BACK_COLOR = '&H33000000'

def merge_video_audio():
    """Merge video and audio, and reduce video volume"""
    VIDEO_FILE = find_video_files()
    background_file = _BACKGROUND_AUDIO_FILE
    
    if not load_key("burn_subtitles"):
        rprint("[bold yellow]Warning: A 0-second black video will be generated as a placeholder as subtitles are not burned in.[/bold yellow]")

        # Create a black frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(DUB_VIDEO, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()

        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    # Normalize dub audio
    normalized_dub_audio = 'output/normalized_dub.wav'
    normalize_audio_volume(DUB_AUDIO, normalized_dub_audio)
    
    # Merge video and audio with translated subtitles
    video = cv2.VideoCapture(VIDEO_FILE)
    TARGET_WIDTH = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    TARGET_HEIGHT = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    rprint(f"[bold green]Video resolution: {TARGET_WIDTH}x{TARGET_HEIGHT}[/bold green]")
    
    abs_dub_sub = os.path.abspath(DUB_SUB_FILE)
    abs_src_sub = os.path.abspath(SRC_SUB_FILE)

    s = load_key("subtitle_style") or {}
    _src_size  = s.get("src_font_size",       SRC_FONT_SIZE)
    _src_col   = s.get("src_font_color",      SRC_FONT_COLOR)
    _src_out   = s.get("src_outline_color",   SRC_OUTLINE_COLOR)
    _tr_size   = s.get("trans_font_size",     TRANS_FONT_SIZE)
    _tr_col    = s.get("trans_font_color",    TRANS_FONT_COLOR)
    _tr_out    = s.get("trans_outline_color", TRANS_OUTLINE_COLOR)
    _tr_back   = s.get("trans_back_color",    TRANS_BACK_COLOR)
    _margin_v  = s.get("margin_v", 27)

    subtitle_filter = (
        f"subtitles=filename='{abs_src_sub}':force_style='FontSize={_src_size},"
        f"FontName={SRC_FONT_NAME},PrimaryColour={_src_col},"
        f"OutlineColour={_src_out},OutlineWidth={SRC_OUTLINE_WIDTH},"
        f"ShadowColour={SRC_SHADOW_COLOR},BorderStyle=1',"
        f"subtitles=filename='{abs_dub_sub}':force_style='FontSize={_tr_size},"
        f"FontName={TRANS_FONT_NAME},PrimaryColour={_tr_col},"
        f"OutlineColour={_tr_out},OutlineWidth={TRANS_OUTLINE_WIDTH},"
        f"BackColour={_tr_back},Alignment=2,MarginV={_margin_v},BorderStyle=4'"
    )
    
    logo_path    = load_key("logo.path") or ""
    logo_enabled = load_key("logo.enabled")
    extra_inputs = []
    if logo_enabled and logo_path and os.path.exists(logo_path):
        logo_w      = load_key("logo.width")  or 150
        logo_margin = load_key("logo.margin") or 20
        pos_map = {
            "top-left":     f"{logo_margin}:{logo_margin}",
            "top-right":    f"W-w-{logo_margin}:{logo_margin}",
            "bottom-left":  f"{logo_margin}:H-h-{logo_margin}",
            "bottom-right": f"W-w-{logo_margin}:H-h-{logo_margin}",
        }
        pos = pos_map.get(load_key("logo.position") or "bottom-right", f"W-w-{logo_margin}:H-h-{logo_margin}")
        extra_inputs = ['-i', logo_path]
        video_fc = (
            f'[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,'
            f'pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,'
            f'{subtitle_filter}[sub];[3:v]scale={logo_w}:-1[logo];[sub][logo]overlay={pos}[v]'
        )
    else:
        video_fc = (
            f'[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,'
            f'pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,'
            f'{subtitle_filter}[v]'
        )

    cmd = [
        'ffmpeg', '-y', '-i', VIDEO_FILE, '-i', background_file, '-i', normalized_dub_audio,
        *extra_inputs,
        '-filter_complex', video_fc + ';[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=3[a]'
    ]

    if load_key("ffmpeg_gpu"):
        rprint("[bold green]Using GPU acceleration...[/bold green]")
        cmd.extend(['-map', '[v]', '-map', '[a]', '-c:v', 'h264_nvenc'])
    else:
        cmd.extend(['-map', '[v]', '-map', '[a]'])
    
    cmd.extend(['-c:a', 'aac', '-b:a', '96k', DUB_VIDEO])
    
    subprocess.run(cmd)
    rprint(f"[bold green]Video and audio successfully merged into {DUB_VIDEO}[/bold green]")

if __name__ == '__main__':
    merge_video_audio()
