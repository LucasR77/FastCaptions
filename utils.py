import os
import sys
import subprocess
import json

def resource_path(relative_path):
    """ Obtiene la ruta absoluta para recursos empaquetados o busca en el sistema """
    try:
        base_path = sys._MEIPASS
        return os.path.join(base_path, relative_path)
    except Exception:
        # 1. Buscar en el directorio actual
        local_path = os.path.abspath(relative_path)
        if os.path.exists(local_path):
            return local_path
            
        # 2. Buscar en la carpeta interna de la build (por si el usuario lo tiene ahí)
        internal_path = os.path.join(os.path.dirname(__file__), "dist", "FastCaptions", "_internal", relative_path)
        if os.path.exists(internal_path):
            return internal_path
            
        # 3. Fallback al PATH del sistema para binarios
        return relative_path

def get_duration(file):
    ffprobe = resource_path("ffprobe.exe")
    cmd = [ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file]
    
    # Prevenir que se abran consolas en Windows
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo)
    try:
        return float(result.stdout.strip())
    except:
        return 0.0

def time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds % 1) * 100)
    return f"{hours:01}:{minutes:02}:{secs:02}.{msecs:02}"

def rgb_to_ass(hex_color):
    """ Convierte #RRGGBB a formato ASS &H00BBGGRR """
    hex_color = hex_color.lstrip('#')
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b}{g}{r}"

def guardar_preset(nombre, datos):
    presets = cargar_presets()
    presets[nombre] = datos
    with open("presets_sub.json", "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=4)

def cargar_presets():
    if not os.path.exists("presets_sub.json"):
        return {}
    try:
        with open("presets_sub.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def crear_proxy_video(input_video, output_proxy):
    """ Crea una versión ligera (proxy) para previsualización fluida CON AUDIO """
    ffmpeg = resource_path("ffmpeg.exe")
    # 360p, bitrate bajo, preset ultrafast, MANTENER AUDIO para preview sincronizado
    cmd = [
        ffmpeg, "-i", input_video, 
        "-vf", "scale=-2:360", 
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "32", 
        "-c:a", "aac", "-b:a", "64k",  # Audio comprimido pero presente
        "-y", output_proxy
    ]
    
    # Prevenir que se abran consolas en Windows
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)

def guardar_session(datos):
    with open("session_sub.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)

def cargar_session():
    if not os.path.exists("session_sub.json"):
        return {}
    try:
        with open("session_sub.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def wrap_text_pyramid(text, max_width, width_func):
    """
    Divide el texto en líneas intentando que la superior sea más larga (pirámide invertida).
    """
    words = text.split()
    if not words:
        return ""
    
    # Intentar en 1 línea
    if width_func(text) <= max_width:
        return text
    
    # Intentar en 2 líneas
    # Buscamos el punto de corte donde la línea 1 sea >= línea 2
    # y la diferencia sea mínima, pero ambas dentro del max_width.
    best_split = 1
    min_diff = float('inf')
    found_valid_2_lines = False
    
    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])
        w1 = width_func(line1)
        w2 = width_func(line2)
        
        if w1 <= max_width and w2 <= max_width:
            if w1 >= w2:
                found_valid_2_lines = True
                diff = w1 - w2
                if diff < min_diff:
                    min_diff = diff
                    best_split = i
    
    if found_valid_2_lines:
        return " ".join(words[:best_split]) + "\\N" + " ".join(words[best_split:])

    # Si no entra en 2, probamos un wrap básico pero manteniendo el \\N para ASS
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        if width_func(test_line) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
        
    return "\\N".join(lines)
