"""
Módulo para el renderizado de subtítulos ASS
Separa la lógica de generación de subtítulos de la interfaz
"""
import re
import os
from utils import format_timestamp, rgb_to_ass, wrap_text_pyramid


class SubtitleRenderer:
    """Clase para generar archivos ASS con la configuración especificada"""
    
    def __init__(self, font_size, border_width, color_primary, color_secondary, color_border):
        self.font_size = font_size
        self.border_width = border_width
        self.color_primary = color_primary
        self.color_secondary = color_secondary
        self.color_border = color_border
    
    def generate_ass_file(self, txt_path, ass_path, global_margin, estilo="estatico"):
        """
        Genera un archivo ASS a partir del archivo de texto con timestamps
        
        Args:
            txt_path: Ruta al archivo de texto con subtítulos
            ass_path: Ruta donde guardar el archivo ASS
            global_margin: Margen vertical global (0-1920, donde 0 es arriba y 1920 es abajo)
            estilo: "animado" o "estatico"
        """
        # Colores en formato ASS
        ass_white = rgb_to_ass(self.color_primary)
        ass_yellow = rgb_to_ass(self.color_secondary)
        ass_border = rgb_to_ass(self.color_border)
        
        # Header del archivo ASS con Alignment 8 (Top-Center)
        # MarginV con Alignment 8 representa la distancia desde ARRIBA
        header = (
            "[Script Info]\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,Arial Black,{self.font_size},{ass_white},{ass_white},{ass_border},&H00000000,1,0,0,0,100,100,0,0,1,{self.border_width},0,8,10,10,{global_margin},1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        
        with open(txt_path, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            
            for linea in lineas:
                linea = linea.strip()
                if not linea:
                    continue
                    
                partes = linea.split("#")
                if len(partes) < 3:
                    continue
                
                t_data = partes[1].strip().split("|")
                texto_completo = partes[2].strip()
                
                # Detectar altura específica (marcada con {{altura}})
                dialog_margin = global_margin
                if "{{" in texto_completo:
                    match = re.search(r"\{\{(\d+)\}\}", texto_completo)
                    if match:
                        dialog_margin = int(match.group(1))
                        # Limpiar el marcador de altura del texto
                        texto_completo = re.sub(r"\{\{\d+\}\}", "", texto_completo).strip()
                
                start_g = partes[0].strip()
                end_g = format_timestamp(float(t_data[-1].split(":")[1]))
                
                # Función para estimar el ancho en el render (PlayResX=1080)
                # Arial Black es ancha, estimamos ~0.6 del font_size por caracter
                def width_func_ass(t):
                    return len(t) * self.font_size * 0.6
                
                # Aplicar wrap de texto con pirámide invertida
                texto_wrapped = wrap_text_pyramid(texto_completo, 1000, width_func_ass)
                
                # Diálogo base (capa 0)
                f.write(f"Dialogue: 0,{start_g},{end_g},Default,,0,0,{dialog_margin},,{texto_wrapped}\n")
                
                # Si es animado, agregar resaltado de palabras
                if estilo == "animado":
                    self._add_animated_highlights(f, texto_wrapped, t_data, start_g, end_g, 
                                                  dialog_margin, ass_white, ass_yellow)
    
    def _add_animated_highlights(self, file_handle, texto_wrapped, t_data, start_g, end_g, 
                                 dialog_margin, ass_white, ass_yellow):
        """Agrega los resaltados animados palabra por palabra"""
        # Convertir el texto wrapped a lista de palabras
        palabras_wrapped = texto_wrapped.replace("\\N", " ").split()
        
        for idx, t_range in enumerate(t_data):
            if idx >= len(palabras_wrapped):
                break
                
            try:
                s_w, e_w = t_range.split(":")
                w_start = format_timestamp(float(s_w))
                w_end = format_timestamp(float(e_w))
                
                # Reconstruir el texto con el resalte en la palabra actual
                count = 0
                res_parts = []
                
                for p in texto_wrapped.split(" "):
                    if "\\N" in p:
                        # Manejar palabras que contienen saltos de línea
                        sub_p = p.split("\\N")
                        new_sub = []
                        for sp in sub_p:
                            if sp:  # Solo si no está vacío
                                if count == idx:
                                    new_sub.append(f"{{\\c{ass_yellow}}}{sp}{{\\c{ass_white}}}")
                                else:
                                    new_sub.append(sp)
                                count += 1
                        res_parts.append("\\N".join(new_sub))
                    else:
                        if count == idx:
                            res_parts.append(f"{{\\c{ass_yellow}}}{p}{{\\c{ass_white}}}")
                        else:
                            res_parts.append(p)
                        count += 1
                
                res = " ".join(res_parts)
                # Diálogo de resaltado (capa 1)
                file_handle.write(f"Dialogue: 1,{w_start},{w_end},Default,,0,0,{dialog_margin},,{{\\c{ass_white}}}{res}\n")
                
            except Exception as e:
                print(f"Error procesando palabra {idx}: {e}")
                continue
