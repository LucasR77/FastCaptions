import os
import pytest
import sys

# Agregar el directorio raíz al path para importar utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils import format_timestamp

def test_transcription_formatting_logic():
    # Simulamos el formato que usa subtitulador.py para el TXT
    class MockWord:
        def __init__(self, start, end, word):
            self.start = start
            self.end = end
            self.word = word

    all_words = [
        MockWord(0.0, 1.0, "hola"),
        MockWord(1.0, 2.0, "esto"),
        MockWord(2.0, 3.0, "es"),
        MockWord(3.0, 4.0, "una"),
        MockWord(4.0, 5.0, "prueba")
    ]
    
    WORDS_PER_GROUP = 4
    formatted_lines = []
    
    for i in range(0, len(all_words), WORDS_PER_GROUP):
        g = all_words[i : i + WORDS_PER_GROUP]
        timestamps = "|".join([f"{w.start}:{w.end}" for w in g])
        texto = " ".join([w.word.strip().upper() for w in g])
        line = f"{format_timestamp(g[0].start)} # {timestamps} # {texto}"
        formatted_lines.append(line)
        
    assert len(formatted_lines) == 2
    assert formatted_lines[0].startswith("0:00:00.00 # 0.0:1.0|1.0:2.0|2.0:3.0|3.0:4.0 # HOLA ESTO ES UNA")
    assert formatted_lines[1].startswith("0:00:04.00 # 4.0:5.0 # PRUEBA")

def test_parse_subtitle_line():
    # Lógica de parseo que se encuentra en SubtitleEditor.load_subtitles
    import re
    
    line = "0:00:03.00 # 3.0:4.0|4.0:5.0 # ESTO ES TEST {{300}}"
    
    partes = line.split("#")
    display_time = partes[0].strip()
    word_timestamps = partes[1].strip()
    full_text = partes[2].strip()
    
    height = ""
    if "{{" in full_text:
        match = re.search(r"\{\{(\d+)\}\}", full_text)
        if match:
            height = match.group(0)
            full_text = re.sub(r"\{\{\d+\}\}", "", full_text).strip()
            
    assert display_time == "0:00:03.00"
    assert word_timestamps == "3.0:4.0|4.0:5.0"
    assert full_text == "ESTO ES TEST"
    assert height == "{{300}}"
