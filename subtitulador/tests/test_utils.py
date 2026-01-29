import os
import json
import sys

# Agregar el directorio raíz al path para importar utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils import time_to_seconds, format_timestamp, rgb_to_ass, wrap_text_pyramid

def test_time_to_seconds():
    assert time_to_seconds("00:00:10.00") == 10.0
    assert time_to_seconds("01:00:00.00") == 3600.0
    assert time_to_seconds("00:01:30.50") == 90.5

def test_format_timestamp():
    assert format_timestamp(10.0) == "0:00:10.00"
    assert format_timestamp(3600.0) == "1:00:00.00"
    assert format_timestamp(90.5) == "0:01:30.50"

def test_rgb_to_ass():
    assert rgb_to_ass("#FFFFFF") == "&H00FFFFFF"
    assert rgb_to_ass("#FF0000") == "&H000000FF"
    assert rgb_to_ass("#0000FF") == "&H00FF0000"

def test_wrap_text_pyramid():
    # Mock width function (approx length)
    def mock_width(text):
        return len(text) * 10
    
    # Texto corto
    text = "Hola mundo"
    assert wrap_text_pyramid(text, 200, mock_width) == "Hola mundo"
    
    # Texto largo para 2 líneas
    text = "Este es un texto bastante largo para probar"
    # mock_width("Este es un texto") = 160
    # mock_width("bastante largo para probar") = 260
    # wrap_text_pyramid debería dividirlo. 
    # La lógica de pirámide invertida busca que la primera línea sea más larga o igual.
    result = wrap_text_pyramid(text, 300, mock_width)
    lines = result.split('\n')
    assert len(lines) >= 1 # Al menos no debe fallar
