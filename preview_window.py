import os
import tkinter as tk
from tkinter import ttk
import threading
import subprocess
from PIL import Image, ImageTk
from utils import resource_path, format_timestamp, get_duration, wrap_text_pyramid
import re
from tkinter import messagebox
import pygame
import uuid
import time

class PreviewWindow:
    def __init__(self, parent, video_path, estilo_var, color_p_getter, color_s_getter, color_b_getter, font_size_var, border_width_var, initial_margin, txt_path=None):
        self.p_root = tk.Toplevel(parent)
        self.p_root.title("Subtitle Editor & Preview")
        self.p_root.geometry("900x750")  # A bit more space
        self.p_root.resizable(True, True)
        self.p_root.configure(bg="#0f172a")
        
        # Modern Palette - Improved Contrast
        self.colors = {
            "bg": "#0f172a",
            "sidebar": "#1e293b",
            "card": "#334155",
            "text": "#f8fafc",
            "text_dim": "#94a3b8",
            "accent": "#38bdf8",
            "success": "#4ade80",
            "warning": "#fbbf24",
            "danger": "#f87171"
        }
        
        # Inicializar pygame mixer para audio
        self.audio_initialized = False
        
        self.video_path = video_path  # Proxy CON AUDIO
        self.txt_path = txt_path
        self.lines = []
        self.text_entries = []  # Para los Entry widgets del editor
        self.segments = []  # Para almacenar la info de cada segmento
        
        if txt_path and os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                self.lines = f.readlines()
        
        self.estilo_var = estilo_var
        self.get_color_p = color_p_getter
        self.get_color_s = color_s_getter
        self.get_color_b = color_b_getter
        self.font_size_var = font_size_var
        self.border_width_var = border_width_var
        
        self.duration = get_duration(video_path)
        self.global_margin = initial_margin
        self.pos_y = tk.IntVar(value=initial_margin)
        self.current_time = tk.DoubleVar(value=min(1.0, self.duration))
        self.is_dragging = False
        self.individual_mode = False
        
        self.canvas_w, self.canvas_h = 280, 498  # Más compacto para que quepa mejor verticalmente
        
        # Extraer AUDIO a WAV temporal
        self.audio_wav = os.path.join(os.environ.get("TEMP", "."), f"audio_{os.getpid()}.wav")
        self.audio_initialized = self.prepare_audio()

        self._last_after_id = None
        self.is_playing = False
        self._play_after_id = None
        
        # Suscribirse a cambios en tiempo real
        self.font_size_var.trace_add("write", lambda *args: self.update_text_ui())
        self.border_width_var.trace_add("write", lambda *args: self.update_text_ui())
        self.estilo_var.trace_add("write", lambda *args: self.update_text_ui())
        self.current_time.trace_add("write", lambda *args: self.update_text_ui())

        self.setup_ui()
        self.start_preview()

    def setup_ui(self):
        # Master container
        self.main_container = tk.Frame(self.p_root, bg=self.colors["bg"])
        self.main_container.pack(fill="both", expand=True)
        
        # --- LEFT SECTION: PREVIEW & CONTROLS ---
        left_section = tk.Frame(self.main_container, bg=self.colors["bg"], padx=20, pady=20)
        left_section.pack(side="left", fill="both")
        
        # Video Container (adds a nice border)
        video_frame = tk.Frame(left_section, bg=self.colors["accent"], padx=2, pady=2)
        video_frame.pack(pady=(0, 15))
        
        self.canvas = tk.Canvas(video_frame, width=self.canvas_w, height=self.canvas_h, 
                               bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # Controls Bar (Horizontal below video)
        controls_bar = tk.Frame(left_section, bg=self.colors["bg"])
        controls_bar.pack(fill="x")

        # Play/Pause with better styling
        self.btn_play = tk.Button(controls_bar, text="▶ PLAY", command=self.toggle_play,
                                 bg=self.colors["success"], fg="#0f172a", 
                                 font=("Segoe UI", 11, "bold"), relief="flat", 
                                 padx=20, pady=8, cursor="hand2")
        self.btn_play.pack(side="left", fill="x", expand=True)

        # Height/Position Button
        if self.txt_path and os.path.exists(self.txt_path):
            self.btn_individual = tk.Button(left_section, text="📌 AJUSTAR ALTURA DE ESTA FRASE", 
                                           command=self.toggle_individual_mode,
                                           bg=self.colors["warning"], fg="#0f172a", 
                                           font=("Segoe UI", 9, "bold"), 
                                           relief="flat", pady=10, cursor="hand2")
            self.btn_individual.pack(fill="x", pady=(15, 0))

        # Time Slider Container
        slider_frame = tk.Frame(left_section, bg=self.colors["sidebar"], pady=10, padx=15)
        slider_frame.pack(fill="x", pady=(15, 0))
        
        lbl_time = tk.Label(slider_frame, text="PROGRESO DEL VIDEO", bg=self.colors["sidebar"], 
                           fg=self.colors["accent"], font=("Segoe UI", 8, "bold"))
        lbl_time.pack(anchor="w")
        
        self.time_slider = tk.Scale(slider_frame, from_=0, to=self.duration, orient="horizontal", 
                                   variable=self.current_time, resolution=0.1, 
                                   command=self.on_slider_move, bg=self.colors["sidebar"], 
                                   fg=self.colors["accent"], highlightthickness=0, 
                                   troughcolor="#334155", activebackground=self.colors["accent"],
                                   sliderrelief="flat", sliderlength=15, width=8,
                                   showvalue=False)
        self.time_slider.pack(fill="x", pady=(5, 0))

        # Mouse bindings for canvas
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<Button-1>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        # --- RIGHT SECTION: TRANSCRIPTION EDITOR ---
        right_section = tk.Frame(self.main_container, bg=self.colors["sidebar"])
        right_section.pack(side="right", fill="both", expand=True)
        
        # Header
        editor_header = tk.Frame(right_section, bg=self.colors["sidebar"], padx=25, pady=20)
        editor_header.pack(fill="x")
        
        tk.Label(editor_header, text="TRANSCIPCIÓN", fg=self.colors["accent"], 
                bg=self.colors["sidebar"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(editor_header, text="Edita el texto y revisa los tiempos en tiempo real", 
                fg=self.colors["text_dim"], bg=self.colors["sidebar"], 
                font=("Segoe UI", 9)).pack(anchor="w")
        
        # Content area (Canvas + Scrollbar)
        editor_container = tk.Frame(right_section, bg=self.colors["sidebar"])
        editor_container.pack(fill="both", expand=True)

        self.editor_canvas = tk.Canvas(editor_container, bg=self.colors["sidebar"], 
                                      highlightthickness=0)
        editor_scrollbar = ttk.Scrollbar(editor_container, orient="vertical", 
                                       command=self.editor_canvas.yview)
        
        self.editor_scrollable = tk.Frame(self.editor_canvas, bg=self.colors["sidebar"])
        self.canvas_window_id = self.editor_canvas.create_window((0, 0), window=self.editor_scrollable, 
                                       anchor="nw")
        
        self.editor_scrollable.bind("<Configure>", self._on_frame_configure)
        self.editor_canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.editor_canvas.configure(yscrollcommand=editor_scrollbar.set)
        
        # Layout scrollable
        editor_scrollbar.pack(side="right", fill="y")
        self.editor_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        # Footer with Save button (ALWAYS BELOW)
        footer = tk.Frame(right_section, bg=self.colors["sidebar"], pady=20, padx=20)
        footer.pack(fill="x", side="bottom")
        
        self.btn_save = tk.Button(footer, text="💾 GUARDAR CAMBIOS", command=self.save_subtitles,
                                 bg=self.colors["success"], fg="#0f172a", 
                                 font=("Segoe UI", 11, "bold"), relief="flat", 
                                 padx=30, pady=12, cursor="hand2")
        self.btn_save.pack()
        
        # Load content into the editor
        self.load_editor_content()

        # Binding MouseWheel
        def _on_mousewheel(event):
            self.editor_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.p_root.bind_all("<MouseWheel>", _on_mousewheel)

    def _on_frame_configure(self, event):
        self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Match frame width to canvas width
        if hasattr(self, 'canvas_window_id'):
            self.editor_canvas.itemconfig(self.canvas_window_id, width=event.width)
    
    def load_editor_content(self):
        """Carga los subtítulos en el panel de edición con mejor diseño"""
        if not self.txt_path or not os.path.exists(self.txt_path):
            tk.Label(self.editor_scrollable, text="No hay subtítulos para editar\n(Archivo no encontrado)", 
                    font=("Segoe UI", 10, "italic"), fg=self.colors["text_dim"], 
                    bg=self.colors["sidebar"]).pack(pady=40)
            return
        
        if not self.lines:
            tk.Label(self.editor_scrollable, text="El archivo de subtítulos está vacío.", 
                    font=("Segoe UI", 10, "italic"), fg=self.colors["text_dim"], 
                    bg=self.colors["sidebar"]).pack(pady=40)
            return

        # Clear existing entries if any
        for child in self.editor_scrollable.winfo_children():
            child.destroy()
        self.text_entries = []
        self.segments = []

        count = 0
        try:
            for idx, line in enumerate(self.lines):
                line = line.strip()
                if not line: continue
                
                try:
                    partes = line.split("#")
                    if len(partes) < 3: continue
                    
                    display_time = partes[0].strip()
                    word_timestamps = partes[1].strip()
                    full_text = partes[2].strip()
                    
                    height = ""
                    if "{{" in full_text:
                        match = re.search(r"\{\{(\d+)\}\}", full_text)
                        if match:
                            height = match.group(0)
                            full_text = re.sub(r"\{\{\d+\}\}", "", full_text).strip()
                    
                    self.segments.append({
                        "display_time": display_time,
                        "word_timestamps": word_timestamps,
                        "height": height
                    })
                    
                    # Card Container
                    card = tk.Frame(self.editor_scrollable, bg=self.colors["card"], 
                                   padx=15, pady=12, highlightthickness=1, 
                                   highlightbackground="#334155")
                    card.pack(fill="x", padx=15, pady=8)
                    
                    # Time label
                    lbl_time = tk.Label(card, text=f"⏱ {display_time}", 
                                       font=("Consolas", 9, "bold"), 
                                       fg=self.colors["accent"], bg=self.colors["card"])
                    lbl_time.pack(side="left", padx=(0, 15))
                    
                    # Entry with better looks - Increased width for visibility
                    entry = tk.Entry(card, font=("Segoe UI", 10), relief="flat", 
                                    bg=self.colors["card"], fg=self.colors["text"], 
                                    insertbackground=self.colors["accent"])
                    entry.insert(0, full_text)
                    entry.pack(side="left", fill="x", expand=True)
                    
                    # Highlight if has custom height
                    if height:
                        tk.Label(card, text="🎯", fg=self.colors["warning"], 
                                 bg=self.colors["card"], font=("Arial", 10)).pack(side="right")
                    
                    # Sync entry with video on click
                    def jump_to_time(t_str=display_time):
                        try:
                            # display_time is MM:SS,mmm
                            parts = t_str.replace(",", ":").split(":")
                            if len(parts) == 3:
                                m, s, ms = parts
                            elif len(parts) == 2:
                                s, ms = parts; m = 0
                            else: return

                            total_s = int(m)*60 + int(s) + int(ms)/1000
                            self.current_time.set(total_s)
                            self.on_slider_move()
                        except Exception as ex: print(f"Time jump error: {ex}")
                    
                    lbl_time.bind("<Button-1>", lambda e, t=display_time: jump_to_time(t))
                    lbl_time.config(cursor="hand2")

                    self.text_entries.append(entry)
                    count += 1
                    
                except Exception as e:
                    print(f"Error parseando línea {idx}: {e}")
            
            if count == 0:
                 tk.Label(self.editor_scrollable, text="No se pudieron leer líneas válidas.", 
                    font=("Segoe UI", 10, "italic"), fg=self.colors["text_dim"], 
                    bg=self.colors["sidebar"]).pack(pady=40)
        
        except Exception as e:
             messagebox.showerror("Error Carga Editor", f"Error crítico cargando editor: {e}")
    
    def save_subtitles(self):
        """Guarda los cambios del editor al archivo"""
        try:
            with open(self.txt_path, "w", encoding="utf-8") as f:
                for idx, segment in enumerate(self.segments):
                    new_text = self.text_entries[idx].get().strip().upper()
                    line = f"{segment['display_time']} # {segment['word_timestamps']} # {new_text}"
                    if segment["height"]:
                        line += f" {segment['height']}"
                    f.write(line + "\n")
            
            # Recargar líneas
            with open(self.txt_path, "r", encoding="utf-8") as f:
                self.lines = f.readlines()
            
            self.update_text_ui()
            
            # Feedback visual
            self.p_root.title("✅ CAMBIOS GUARDADOS")
            self.p_root.after(1500, lambda: self.p_root.title("Editor de Subtítulos - Preview") 
                             if self.p_root.winfo_exists() else None)
            
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.config(text="PAUSE", bg=self.colors["danger"], fg="white")
            self.start_audio()
            self.play_loop()
        else:
            self.btn_play.config(text="▶ PLAY", bg=self.colors["success"], fg="#0f172a")
            self.pause_audio()
            if self._play_after_id:
                self.p_root.after_cancel(self._play_after_id)

    def prepare_audio(self):
        """Extrae el audio del video a un WAV temporal y lo carga en pygame"""
        try:
            ffmpeg = resource_path("ffmpeg.exe")
            # Extraer audio a WAV (44100Hz, mono) para máxima compatibilidad
            cmd = [ffmpeg, "-i", self.video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", self.audio_wav, "-y"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(self.audio_wav):
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=1)
                pygame.mixer.music.load(self.audio_wav)
                return True
        except Exception as e:
            print(f"Error preparando audio: {e}")
        return False

    def start_audio(self):
        """Inicia la reproducción de audio desde el tiempo actual"""
        if not self.audio_initialized:
            return
        
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1)
                pygame.mixer.music.load(self.audio_wav)
            
            # El start en WAV suele ser muy preciso
            pygame.mixer.music.play(start=self.current_time.get())
        except Exception as e:
            print(f"Error al reproducir audio: {e}")

    def pause_audio(self):
        """Pausa el audio"""
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
        except: pass

    def stop_audio(self):
        """Detiene el audio completamente"""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except: pass

    def play_loop(self):
        if not self.is_playing or not self.p_root.winfo_exists():
            return
        
        new_time = self.current_time.get() + 0.1
        if new_time >= self.duration:
            new_time = 0
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg=self.colors["success"], fg="#0f172a")
        
        self.current_time.set(new_time)
        # Extraer frame para este tiempo (uso Thread para no trabar)
        threading.Thread(target=self.extraction_task, args=(new_time,), daemon=True).start()
        
        # Programar siguiente frame a 100ms (10fps)
        self._play_after_id = self.p_root.after(100, self.play_loop)


    def extraction_task(self, t):
        ts = format_timestamp(t)
        # Unique filename to prevent thread collision
        unique_id = f"{uuid.uuid4().hex}_{int(time.time()*1000)}"
        temp_frame = os.path.join(os.environ.get("TEMP", "."), f"prev_{unique_id}.jpg")
        
        ffmpeg = resource_path("ffmpeg.exe")
        try:
            # -ss before -i is faster (input seeking)
            cmd = [ffmpeg, "-ss", ts, "-i", self.video_path, "-vframes", "1", "-f", "image2", "-q:v", "5", temp_frame, "-y"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(temp_frame):
                img = Image.open(temp_frame)
                img = img.resize((self.canvas_w, self.canvas_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                if self.p_root.winfo_exists():
                    self.p_root.after(0, lambda: self.apply_bg(photo))
                
                # Schedure removal to avoid file lock issues immediately
                try: os.remove(temp_frame)
                except: pass
            else:
                print(f"Frame not extracted for time {ts}")
        except Exception as e:
            print(f"Error extracting frame: {e}")

    def apply_bg(self, photo):
        if not self.p_root.winfo_exists(): return
        try:
            self.canvas.delete("bg")
            self.p_root.photo = photo
            self.canvas.create_image(0, 0, anchor="nw", image=photo, tags="bg")
            self.canvas.tag_lower("bg")
        except Exception as e:
            print(f"Error applying bg: {e}")

    def on_slider_move(self, _=None):
        if hasattr(self, '_last_after_id') and self._last_after_id:
            self.p_root.after_cancel(self._last_after_id)
        self._last_after_id = self.p_root.after(100, lambda: threading.Thread(target=self.extraction_task, args=(self.current_time.get(),), daemon=True).start())

    def on_mouse_drag(self, e):
        self.is_dragging = True
        y = max(40, min(e.y, self.canvas_h - 40))
        ass_margin = int((1 - (y / self.canvas_h)) * 1920)
        self.pos_y.set(ass_margin)
        
        if not self.individual_mode:
            # En modo normal, actualizamos la altura GLOBAL
            self.global_margin = ass_margin
            
        self.update_text_ui(y)

    def on_mouse_release(self, e):
        self.is_dragging = False
        self.update_text_ui()
    
    def start_preview(self):
        """Inicia el preview extrayendo el primer frame"""
        # Esperar a que la UI esté completamente renderizada
        self.p_root.update_idletasks()
        # Pequeño delay para asegurar que el canvas esté listo
        self.p_root.after(100, lambda: threading.Thread(target=self.extraction_task, args=(self.current_time.get(),), daemon=True).start())
        self.p_root.after(150, self.update_text_ui)

    def toggle_individual_mode(self):
        if not self.individual_mode:
            # Entrar en modo edición individual
            # Buscamos si la frase actual ya tiene una altura para poner el slider ahí
            t_now = self.current_time.get()
            current_h = self.global_margin
            for line in self.lines:
                try:
                    partes = line.split("#")
                    t_data = partes[1].strip().split("|"); t_start = float(t_data[0].split(":")[0]); t_end = float(t_data[-1].split(":")[1])
                    if t_start <= t_now <= t_end and "{{" in partes[2]:
                        match = re.search(r"\{\{(\d+)\}\}", partes[2])
                        if match: current_h = int(match.group(1))
                except: pass
            
            self.pos_y.set(current_h)
            self.individual_mode = True
            self.btn_individual.config(text="✅ CONFIRMAR NUEVA ALTURA", bg=self.colors["success"])
            self.update_text_ui()
        else:
            # Confirmar y salir
            self.guardar_posicion_frase()
            self.individual_mode = False
            self.btn_individual.config(text="📌 AJUSTAR ALTURA DE ESTA FRASE", bg=self.colors["warning"])
            # Volver a mostrar la global en el slider
            self.pos_y.set(self.global_margin)
            self.update_text_ui()

    def update_text_ui(self, y_coord=None):
        if not self.p_root.winfo_exists(): return
        
        try:
            if y_coord is None:
                y_coord = int((1 - (self.pos_y.get() / 1920)) * self.canvas_h)
            
            self.canvas.delete("text_item")
            is_animado = self.estilo_var.get() == "animado"
            x_center = self.canvas_w // 2
            
            color_p = self.get_color_p()
            color_s = self.get_color_s()
            color_b = self.get_color_b()
            f_size = self.font_size_var.get()
            b_width = self.border_width_var.get()

            # Ajuste de escala más preciso (libass vs tkinter)
            # 1080x1920 -> 270x480 (Factor 0.25)
            # Pero libass renderiza más pequeño, usamos 0.15 para compensar
            tk_font_size = max(8, int(f_size * 0.15))
            tk_border = max(1, int(b_width * 0.12))
            font_style = ("Arial Black", tk_font_size, "bold")

            # 1. Buscar si hay texto real para este tiempo
            display_text = "" 
            found_height = None
            
            t_now = self.current_time.get()
            
            # Optimization: If many lines, binary search would be better, but linear is fine for <1000 lines
            if self.lines:
                for line in self.lines:
                    try:
                        partes = line.split("#")
                        if len(partes) < 3: continue
                        
                        t_data = partes[1].strip().split("|")
                        t_start = float(t_data[0].split(":")[0])
                        t_end = float(t_data[-1].split(":")[1])
                        
                        if t_start <= t_now <= t_end:
                            display_text = partes[2].strip()
                            if "{{" in display_text:
                                match = re.search(r"\{\{(\d+)\}\}", display_text)
                                if match:
                                    found_height = int(match.group(1))
                                    display_text = re.sub(r"\{\{\d+\}\}", "", display_text).strip()
                            break
                    except Exception as e: 
                        print(f"Error parseando linea en update_text_ui: {e}")
                        continue
            else:
                 display_text = "ESPERANDO TRANSCRIPCIÓN..."

            # 2. Determinar la altura a mostrar
            if self.is_dragging or self.individual_mode:
                # Usar valor de arrastre o modo edición
                # (Si y_coord ya fue calculado arriba con pos_y, está bien)
                if y_coord is None: # Should be handled at top, but just in case
                     y_coord = int((1 - (self.pos_y.get() / 1920)) * self.canvas_h)
            elif found_height is not None:
                # Mostrar la altura guardada
                y_coord = int((1 - (found_height / 1920)) * self.canvas_h)
            elif y_coord is None:
                # Altura global (pos_y debería ser == global_margin cuando no editamos)
                y_coord = int((1 - (self.pos_y.get() / 1920)) * self.canvas_h)

            # Función para medir ancho real en el preview
            temp_label = tk.Label(self.p_root, font=font_style)
            def width_func_tk(t):
                temp_label.config(text=t)
                return temp_label.winfo_reqwidth()

            # Margen de seguridad en preview (270px de ancho total)
            # 1080 -> 270 (Factor 0.25). 1000px ASS -> 250px Tk
            max_w_px = int(self.canvas_w * 0.9)
            
            display_text_wrapped = wrap_text_pyramid(display_text, max_w_px, width_func_tk)
            lines = display_text_wrapped.split("\\N")
            
            # Calcular altura total para centrar verticalmente si se desea, 
            # o simplemente apilar hacia arriba. 
            # En ASS, el margen V es a la base.
            line_height = tk_font_size * 1.5
            
            total_lines = len(lines)
            word_idx_global = 0
            
            for i, line_text in enumerate(lines):
                # Calcular posición Y para esta línea
                # Para Alignment 8, la Y es el TOP del bloque.
                # La primera línea (i=0) siempre estará en y_coord, 
                # las siguientes crecen hacia abajo.
                offset_y = i * line_height
                current_y = y_coord + offset_y
                
                words = line_text.split()
                # Decidir qué palabras resaltar en esta línea
                line_parts = []
                for w in words:
                    # El resaltado original resaltaba la segunda palabra (index 1)
                    # Vamos a mantener esa lógica pero globalmente
                    color = color_p
                    if is_animado and word_idx_global == 1:
                        color = color_s
                    line_parts.append((w + " ", color))
                    word_idx_global += 1
                
                # Cálculo de ancho de línea
                line_width = 0
                for t, _ in line_parts:
                    temp_label.config(text=t)
                    line_width += temp_label.winfo_reqwidth()
                
                current_x = x_center - (line_width // 2)
                
                for text, color in line_parts:
                    temp_label.config(text=text)
                    w = temp_label.winfo_reqwidth()
                    
                    # Borde
                    offsets = []
                    for dx in range(-tk_border, tk_border + 1):
                        for dy in range(-tk_border, tk_border + 1):
                            if dx != 0 or dy != 0:
                                self.canvas.create_text(current_x + (w//2) + dx, current_y + dy, text=text, fill=color_b, 
                                                   font=font_style, tags="text_item")
                    
                    # Texto
                    self.canvas.create_text(current_x + (w//2), current_y, text=text, fill=color, 
                                       font=font_style, tags="text_item")
                    current_x += w
                    
            temp_label.destroy() # Cleanup
            
        except Exception as e:
            print(f"Error en update_text_ui: {e}")

    def tick_animacion(self):
        # Parpadeo desactivado por pedido del usuario
        pass


    def wait_and_get_margin(self):
        self.p_root.wait_window(self.p_root)
        self.stop_audio()
        if self.audio_initialized:
            try:
                pygame.mixer.music.unload()
                pygame.mixer.quit()
            except: pass
        if os.path.exists(self.audio_wav):
            try: os.remove(self.audio_wav)
            except: pass
        return self.global_margin 

    def guardar_posicion_frase(self):
        if not self.txt_path or not self.lines:
            return
        
        t_now = self.current_time.get()
        nueva_altura = self.pos_y.get()  # Ya está en escala 1920
        
        for i, line in enumerate(self.lines):
            try:
                partes = line.split("#")
                t_data = partes[1].strip().split("|")
                t_start = float(t_data[0].split(":")[0])
                t_end = float(t_data[-1].split(":")[1])
                
                if t_start <= t_now <= t_end:
                    texto_limpio = re.sub(r"\{\{\d+\}\}", "", partes[2]).strip()
                    self.lines[i] = f"{partes[0]}# {partes[1]} # {texto_limpio} {{{{{nueva_altura}}}}}\n"
                    
                    # Guardar archivo
                    with open(self.txt_path, "w", encoding="utf-8") as f:
                        f.writelines(self.lines)
                    
                    self.p_root.title("✅ POSICIÓN FIJADA!")
                    
                    # Volver el slider a la altura global para no confundir
                    self.pos_y.set(self.global_margin)
                    self.update_text_ui()
                    
                    self.p_root.after(1500, lambda: self.p_root.title("Editor de Subtítulos - Preview"))
                    return
            except: 
                continue
        
