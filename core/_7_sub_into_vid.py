import os, subprocess, time
from core._1_ytdlp import find_video_files
import cv2
import numpy as np
import platform
from core.utils import *

SRC_FONT_SIZE = 15
TRANS_FONT_SIZE = 17
FONT_NAME = 'Arial'
TRANS_FONT_NAME = 'Arial'

# Linux need to install google noto fonts: apt-get install fonts-noto
if platform.system() == 'Linux':
    FONT_NAME = 'NotoSansCJK-Regular'
    TRANS_FONT_NAME = 'NotoSansCJK-Regular'
# Mac OS has different font names
elif platform.system() == 'Darwin':
    FONT_NAME = 'Arial Unicode MS'
    TRANS_FONT_NAME = 'Arial Unicode MS'

SRC_FONT_COLOR = '&HFFFFFF'
SRC_OUTLINE_COLOR = '&H000000'
SRC_OUTLINE_WIDTH = 1
SRC_SHADOW_COLOR = '&H80000000'
TRANS_FONT_COLOR = '&H00FFFF'
TRANS_OUTLINE_COLOR = '&H000000'
TRANS_OUTLINE_WIDTH = 1 
TRANS_BACK_COLOR = '&H33000000'

OUTPUT_DIR = "output"
OUTPUT_VIDEO = f"{OUTPUT_DIR}/output_sub.mp4"
SRC_SRT = f"{OUTPUT_DIR}/src.srt"
TRANS_SRT = f"{OUTPUT_DIR}/trans.srt"
    
def check_gpu_available():
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        return 'h264_nvenc' in result.stdout
    except:
        return False

def merge_subtitles_to_video():
    video_file = find_video_files()
    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)

    # Check resolution
    if not load_key("burn_subtitles"):
        rprint("[bold yellow]Warning: A 0-second black video will be generated as a placeholder as subtitles are not burned in.[/bold yellow]")

        # Create a black frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()

        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    if not os.path.exists(SRC_SRT) or not os.path.exists(TRANS_SRT):
        rprint("Subtitle files not found in the 'output' directory.")
        exit(1)

    video = cv2.VideoCapture(video_file)
    TARGET_WIDTH = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    TARGET_HEIGHT = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    rprint(f"[bold green]Video resolution: {TARGET_WIDTH}x{TARGET_HEIGHT}[/bold green]")
    abs_src_srt = os.path.abspath(SRC_SRT)
    abs_trans_srt = os.path.abspath(TRANS_SRT)

    s = load_key("subtitle_style") or {}
    _src_size  = s.get("src_font_size",    SRC_FONT_SIZE)
    _src_col   = s.get("src_font_color",   SRC_FONT_COLOR)
    _src_out   = s.get("src_outline_color",SRC_OUTLINE_COLOR)
    _tr_size   = s.get("trans_font_size",  TRANS_FONT_SIZE)
    _tr_col    = s.get("trans_font_color", TRANS_FONT_COLOR)
    _tr_out    = s.get("trans_outline_color", TRANS_OUTLINE_COLOR)
    _tr_back   = s.get("trans_back_color", TRANS_BACK_COLOR)
    _margin_v  = s.get("margin_v", 27)

    sub_vf = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"subtitles=filename='{abs_src_srt}':force_style='FontSize={_src_size},FontName={FONT_NAME},"
        f"PrimaryColour={_src_col},OutlineColour={_src_out},OutlineWidth={SRC_OUTLINE_WIDTH},"
        f"ShadowColour={SRC_SHADOW_COLOR},BorderStyle=1',"
        f"subtitles=filename='{abs_trans_srt}':force_style='FontSize={_tr_size},FontName={TRANS_FONT_NAME},"
        f"PrimaryColour={_tr_col},OutlineColour={_tr_out},OutlineWidth={TRANS_OUTLINE_WIDTH},"
        f"BackColour={_tr_back},Alignment=2,MarginV={_margin_v},BorderStyle=4'"
    )

    logo_path = load_key("logo.path") or ""
    logo_enabled = load_key("logo.enabled")
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
        fc = f"[0:v]{sub_vf}[sub];[1:v]scale={logo_w}:-1[logo];[sub][logo]overlay={pos}"
        ffmpeg_cmd = ['ffmpeg', '-i', video_file, '-i', logo_path, '-filter_complex', fc]
    else:
        ffmpeg_cmd = ['ffmpeg', '-i', video_file, '-vf', sub_vf]

    ffmpeg_gpu = load_key("ffmpeg_gpu")
    if ffmpeg_gpu:
        rprint("[bold green]will use GPU acceleration.[/bold green]")
        ffmpeg_cmd.extend(['-c:v', 'h264_nvenc'])
    ffmpeg_cmd.extend(['-y', OUTPUT_VIDEO])

    rprint("🎬 Start merging subtitles to video...")
    start_time = time.time()
    process = subprocess.Popen(ffmpeg_cmd)

    try:
        process.wait()
        if process.returncode == 0:
            rprint(f"\n✅ Done! Time taken: {time.time() - start_time:.2f} seconds")
        else:
            rprint("\n❌ FFmpeg execution error")
    except Exception as e:
        rprint(f"\n❌ Error occurred: {e}")
        if process.poll() is None:
            process.kill()

if __name__ == "__main__":
    merge_subtitles_to_video()