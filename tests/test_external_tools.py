import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Agregar el directorio raíz al path para importar utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils import get_duration, crear_proxy_video

@patch("subprocess.run")
@patch("utils.resource_path")
def test_get_duration(mock_resource_path, mock_run):
    # Mock resource path for ffprobe
    mock_resource_path.return_value = "fake_ffprobe.exe"
    
    # Mock subprocess output
    mock_result = MagicMock()
    mock_result.stdout = "120.5\n"
    mock_run.return_value = mock_result
    
    duration = get_duration("test_video.mp4")
    
    assert duration == 120.5
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "fake_ffprobe.exe" in args[0]
    assert "-show_entries" in args[0]
    assert "test_video.mp4" in args[0]

@patch("subprocess.run")
@patch("utils.resource_path")
def test_crear_proxy_video(mock_resource_path, mock_run):
    mock_resource_path.return_value = "fake_ffmpeg.exe"
    
    crear_proxy_video("input.mp4", "output_proxy.mp4")
    
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    command = args[0]
    
    assert command[0] == "fake_ffmpeg.exe"
    assert "-i" in command
    assert "input.mp4" in command
    assert "output_proxy.mp4" in command
    assert "scale=-2:360" in command
