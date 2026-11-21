import pytest
from app.services.hardware_accel import detect_hardware_encoder, get_video_encode_args

def test_detect_hardware_encoder():
    info = detect_hardware_encoder()
    assert isinstance(info, dict)
    assert "encoder" in info
    assert "type" in info
    assert info["type"] in ("gpu", "cpu")
    assert info["encoder"] in ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_vaapi", "libx264")

def test_get_video_encode_args():
    args = get_video_encode_args(target_height=1080, quality_preset="balanced", crf="23")
    assert "-c:v" in args
    assert "-pix_fmt" in args
    assert "yuv420p" in args

    # Check preset variations
    args_light = get_video_encode_args(target_height=720, quality_preset="light")
    assert "-c:v" in args_light

    args_discord = get_video_encode_args(target_height=480, quality_preset="discord")
    assert "-c:v" in args_discord
