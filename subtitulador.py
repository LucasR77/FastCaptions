import os
import sys
import threading
import re
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageTk
from faster_whisper import WhisperModel

# Importes locales
from utils import resource_path, get_duration, time_to_seconds, format_timestamp, rgb_to_ass, cargar_presets, guardar_preset, cargar_session, guardar_session, wrap_text_pyramid
from preview_window import PreviewWindow
from subtitle_editor import SubtitleEditor

# --- CONFIGURACIÓN ---
WORDS_PER_GROUP = 4

class SubtituladorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Subtitulador Pro v4.0")
        self.root.geometry("450x700+50+50") # Un poco más alta
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")
        
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
        
        # Configure TTK Styles for Dark Mode
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TProgressbar", thickness=8, troughcolor="#1e293b", 
                            background="#38bdf8", borderwidth=0)
        self.style.configure("TCombobox", fieldbackground="#1e293b", 
                            background="#1e293b", foreground="#f8fafc", 
                            arrowcolor="#38bdf8", bordercolor="#334155")
        self.style.map("TCombobox", fieldbackground=[('readonly', "#1e293b")], 
                      foreground=[('readonly', "#f8fafc")])

        # Cargar sesión previa
        session = cargar_session()

        self.path_vid_orig = ""
        self.path_proxy = "" # Para preview fluido
        self.path_txt_corr = ""
        self.margin_v = session.get("margin_v", 300)
        
        # Configuración Cargada o por defecto
        self.color_primario = session.get("color_p", "#FFFFFF")
        self.color_borde = session.get("color_b", "#000000")
        self.color_secundario = session.get("color_s", "#FFFF00")
        
        self.font_size = tk.IntVar(value=session.get("size", 91))
        self.border_width = tk.IntVar(value=session.get("border", 10))
        self.estilo = tk.StringVar(value=session.get("estilo", "animado"))
        self.preview_active = None 
        
        # Sincronizar minimizado/restaurado
        self.root.bind("<Map>", self.al_restaurar)
        self.root.bind("<Unmap>", self.al_minimizar)

        # Traces para autoguardar ante cualquier cambio
        self.font_size.trace_add("write", lambda *a: self.auto_guardar())
        self.border_width.trace_add("write", lambda *a: self.auto_guardar())
        self.estilo.trace_add("write", lambda *a: self.auto_guardar())

        self.setup_ui()

    def auto_guardar(self):
        datos = {
            "color_p": self.color_primario,
            "color_b": self.color_borde,
            "color_s": self.color_secundario,
            "size": self.font_size.get(),
            "border": self.border_width.get(),
            "margin_v": self.margin_v,
            "estilo": self.estilo.get()
        }
        guardar_session(datos)

    def setup_ui(self):
        # Header Area
        header = tk.Frame(self.root, bg=self.colors["bg"], pady=20)
        header.pack(fill="x")
        tk.Label(header, text="SUBTITULADOR PRO", fg=self.colors["accent"], 
                bg=self.colors["bg"], font=("Segoe UI", 16, "bold")).pack()
        tk.Label(header, text="Crea clips virales en segundos", fg=self.colors["text_dim"], 
                bg=self.colors["bg"], font=("Segoe UI", 9)).pack()

        # --- STEP 1: IMPORT & TRANSCRIPTION ---
        s1_frame = tk.Frame(self.root, bg=self.colors["sidebar"], padx=20, pady=15)
        s1_frame.pack(fill="x", padx=15, pady=5)
        
        tk.Label(s1_frame, text="PASO 1: TRANSCRIPCIÓN", fg=self.colors["text"], 
                bg=self.colors["sidebar"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        
        self.btn_trans = tk.Button(s1_frame, text="📂 SELECCIONAR Y TRANSCRIBIR", 
                                   command=self.iniciar_transcripcion, 
                                   bg=self.colors["accent"], fg="#282a36", 
                                   font=("Segoe UI", 9, "bold"), relief="flat", pady=8, cursor="hand2")
        self.btn_trans.pack(fill="x", pady=(10, 5))
        
        self.progress1 = ttk.Progressbar(s1_frame, orient="horizontal", mode="determinate")
        self.progress1.pack(fill="x", pady=5)
        self.status_trans = tk.Label(s1_frame, text="Esperando archivo...", 
                                    bg=self.colors["sidebar"], fg=self.colors["text_dim"], 
                                    font=("Segoe UI", 8, "italic"))
        self.status_trans.pack()

        # --- STEP 2: STYLING ---
        s2_frame = tk.Frame(self.root, bg=self.colors["sidebar"], padx=20, pady=15)
        s2_frame.pack(fill="x", padx=15, pady=5)
        
        tk.Label(s2_frame, text="PASO 2: ESTILO Y AJUSTES", fg=self.colors["text"], 
                bg=self.colors["sidebar"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

        # Files quick look (simplified)
        f_files = tk.Frame(s2_frame, bg=self.colors["sidebar"])
        f_files.pack(fill="x", pady=(10, 5))
        
        self.btn_vid_orig = tk.Button(f_files, text="🎥 VIDEO", command=self.set_video_orig, 
                                     bg="#334155", fg=self.colors["text"], relief="flat", 
                                     font=("Segoe UI", 8), width=15)
        self.btn_vid_orig.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.btn_txt_corr = tk.Button(f_files, text="📄 TXT", command=self.set_txt_corr, 
                                     bg="#334155", fg=self.colors["text"], relief="flat", 
                                     font=("Segoe UI", 8), width=15)
        self.btn_txt_corr.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Color Pickers
        f_colors = tk.Frame(s2_frame, bg=self.colors["sidebar"])
        f_colors.pack(fill="x", pady=10)
 
        def create_color_picker(parent, label, attr_name):
            frame = tk.Frame(parent, bg=self.colors["sidebar"])
            frame.pack(side="left", expand=True)
            tk.Label(frame, text=label, font=("Segoe UI", 7, "bold"), 
                    fg=self.colors["text_dim"], bg=self.colors["sidebar"]).pack()
            box = tk.Button(frame, width=4, height=1, bg=getattr(self, attr_name), 
                            command=lambda: self.elegir_color(attr_name, box), relief="flat",
                            highlightthickness=1, highlightbackground="#334155")
            box.pack(pady=2)
            return box
 
        self.box_p = create_color_picker(f_colors, "TEXTO", "color_primario")
        self.box_b = create_color_picker(f_colors, "BORDE", "color_borde")
        self.box_s = create_color_picker(f_colors, "RESALTE", "color_secundario")

        # Sliders
        f_sliders = tk.Frame(s2_frame, bg=self.colors["sidebar"])
        f_sliders.pack(fill="x")
        
        def create_modern_scale(parent, label, var, from_, to_):
            frame = tk.Frame(parent, bg=self.colors["sidebar"])
            frame.pack(side="left", fill="x", expand=True, padx=5)
            tk.Label(frame, text=label, font=("Segoe UI", 7, "bold"), 
                    fg=self.colors["text_dim"], bg=self.colors["sidebar"]).pack(anchor="w")
            s = tk.Scale(frame, from_=from_, to=to_, orient="horizontal", variable=var, 
                        bg=self.colors["sidebar"], fg=self.colors["text"], 
                        highlightthickness=0, troughcolor="#1a1a1a", 
                        activebackground=self.colors["accent"], showvalue=True, font=("Segoe UI", 7))
            s.pack(fill="x")
            return s

        create_modern_scale(f_sliders, "TAMAÑO", self.font_size, 20, 200)
        create_modern_scale(f_sliders, "BORDE", self.border_width, 0, 40)

        # Style Choice
        f_bottom = tk.Frame(s2_frame, bg=self.colors["sidebar"])
        f_bottom.pack(fill="x", pady=(10, 0))
        
        tk.Radiobutton(f_bottom, text="Animado", variable=self.estilo, value="animado", 
                      font=("Segoe UI", 9), bg=self.colors["sidebar"], fg=self.colors["text"],
                      selectcolor="#0f172a", activebackground=self.colors["sidebar"]).pack(side="left", padx=10)
        tk.Radiobutton(f_bottom, text="Estático", variable=self.estilo, value="estatico", 
                      font=("Segoe UI", 9), bg=self.colors["sidebar"], fg=self.colors["text"],
                      selectcolor="#0f172a", activebackground=self.colors["sidebar"]).pack(side="left", padx=10)

        # --- STEP 3: PREVIEW & RENDER ---
        s3_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=10)
        s3_frame.pack(fill="x", padx=15)

        self.progress2 = ttk.Progressbar(s3_frame, orient="horizontal", mode="determinate")
        self.progress2.pack(fill="x", pady=(0, 10))
        
        self.status_render = tk.Label(s3_frame, text="Listo para renderizar", 
                                     bg=self.colors["bg"], fg=self.colors["text_dim"], 
                                     font=("Segoe UI", 9, "italic"))
        self.status_render.pack()
 
        self.btn_preview = tk.Button(self.root, text="🔍 PREVISUALIZAR Y EDITAR", 
                                     command=self.abrir_preview, 
                                     bg="#475569", fg="white", 
                                     font=("Segoe UI", 10, "bold"), relief="flat", pady=10, cursor="hand2")
        self.btn_preview.pack(fill="x", padx=30, pady=5)
  
        self.btn_render = tk.Button(self.root, text="🚀 GENERAR VIDEO FINAL", 
                                    command=self.iniciar_render, 
                                    bg=self.colors["success"], fg="#0f172a", 
                                    font=("Segoe UI", 12, "bold"), relief="flat", pady=12, cursor="hand2")
        self.btn_render.pack(fill="x", padx=30, pady=(5, 20))

    def al_restaurar(self, event=None):
        if event and event.widget != self.root:
            return
        # Si restauramos la principal y existe el preview, restaurarlo también
        if self.preview_active and self.preview_active.p_root.winfo_exists():
            if self.preview_active.p_root.state() == "iconic":
                self.preview_active.p_root.deiconify()

    def al_minimizar(self, event=None):
        if event and event.widget != self.root:
            return
        # Si minimizamos la principal, minimizamos el preview
        if self.preview_active and self.preview_active.p_root.winfo_exists():
            if self.preview_active.p_root.state() == "normal":
                self.preview_active.p_root.iconify()

    def elegir_color(self, attr_name, button_widget):
        color = colorchooser.askcolor(title=f"Elegir color")[1]
        if color:
            setattr(self, attr_name, color)
            button_widget.config(bg=color)
            self.auto_guardar()
            if self.preview_active and self.preview_active.p_root.winfo_exists():
                self.preview_active.update_text_ui()


    def abrir_preview(self):
        if not self.path_vid_orig:
            return
        
        if self.preview_active and self.preview_active.p_root.winfo_exists():
            self.preview_active.p_root.lift()
            return self.margin_v

        v_path = self.path_proxy if self.path_proxy and os.path.exists(self.path_proxy) else self.path_vid_orig

        self.preview_active = PreviewWindow(
            self.root, 
            v_path,  # Proxy CON AUDIO incluido
            self.estilo, 
            lambda: self.color_primario, 
            lambda: self.color_secundario, 
            lambda: self.color_borde,
            self.font_size, 
            self.border_width,
            self.margin_v,
            self.path_txt_corr
        )
        
        # Posicionar a la derecha de la ventana principal
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        
        # 10px de margen entre ventanas
        self.preview_active.p_root.geometry(f"+{main_x + main_w + 10}+{main_y}")
        
        self.preview_active.p_root.bind("<Map>", self.al_restaurar_desde_preview)
        self.preview_active.p_root.bind("<Unmap>", self.al_minimizar_desde_preview)

        self.margin_v = self.preview_active.wait_and_get_margin()
        self.auto_guardar()
        return self.margin_v

    def al_restaurar_desde_preview(self, event=None):
        if event and event.widget != self.preview_active.p_root:
            return
        if self.root.state() == "iconic":
            self.root.deiconify()

    def al_minimizar_desde_preview(self, event=None):
        if event and event.widget != self.preview_active.p_root:
            return
        if self.root.state() == "normal":
            self.root.iconify()

    def iniciar_transcripcion(self):
        video = filedialog.askopenfilename(title="Seleccionar Video", filetypes=[("Video", "*.mp4 *.mov *.avi")])
        if video:
            self.btn_trans.config(state="disabled")
            threading.Thread(target=self.proceso_transcripcion, args=(video,), daemon=True).start()

    def proceso_transcripcion(self, video):
        try:
            self.status_trans.config(text="Cargando IA...", fg="orange")
            model = WhisperModel("small", device="cpu", compute_type="int8")
            self.progress1["value"] = 50
            segments, _ = model.transcribe(video, word_timestamps=True)
            all_words = [w for s in segments for w in s.words]
            txt_path = os.path.splitext(video)[0] + "_PARA_CORREGIR.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                for i in range(0, len(all_words), WORDS_PER_GROUP):
                    g = all_words[i : i + WORDS_PER_GROUP]
                    timestamps = "|".join([f"{w.start}:{w.end}" for w in g])
                    texto = " ".join([w.word.strip().upper() for w in g])
                    f.write(f"{format_timestamp(g[0].start)} # {timestamps} # {texto}\n")
            self.progress1["value"] = 100
            self.status_trans.config(text="¡TXT Generado!", fg="green")
            self.path_txt_corr = txt_path
            self.root.after(0, lambda: self.btn_txt_corr.config(text="✅ TXT CARGADO", bg="#d1ffd1", fg="#0f172a"))
            self.root.after(0, self.abrir_editor)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_trans.config(state="normal")

    def set_video_orig(self):
        self.path_vid_orig = filedialog.askopenfilename(title="Video original", filetypes=[("Video", "*.mp4 *.mov *.avi")])
        if self.path_vid_orig: 
            self.btn_vid_orig.config(text="⏳ GENERANDO PROXY...", bg="#fff3cd", fg="#0f172a")
            # Crear proxy en segundo plano
            threading.Thread(target=self.generar_proxy_async, daemon=True).start()

    def generar_proxy_async(self):
        from utils import crear_proxy_video
        proxy_name = f"proxy_{os.getpid()}.mp4"
        proxy_path = os.path.join(os.environ.get("TEMP", "."), proxy_name)
        crear_proxy_video(self.path_vid_orig, proxy_path)
        self.path_proxy = proxy_path
        self.root.after(0, lambda: self.btn_vid_orig.config(text="✅ VIDEO CON PROXY", bg="#d1ffd1", fg="#0f172a"))

    def set_txt_corr(self):
        self.path_txt_corr = filedialog.askopenfilename(title="TXT corregido", filetypes=[("Texto", "*.txt")])
        if self.path_txt_corr: 
            self.btn_txt_corr.config(text="✅ TXT CARGADO", bg="#d1ffd1", fg="#0f172a")
            
    def abrir_editor(self):
        if not self.path_txt_corr or not os.path.exists(self.path_txt_corr):
            return
        
        def al_guardar():
            if self.preview_active and self.preview_active.p_root.winfo_exists():
                # Forzar recarga de líneas en el preview
                with open(self.path_txt_corr, "r", encoding="utf-8") as f:
                    self.preview_active.lines = f.readlines()
                self.preview_active.update_text_ui()
                
        SubtitleEditor(self.root, self.path_txt_corr, on_save_callback=al_guardar)

    def iniciar_render(self):
        if not self.path_vid_orig or not self.path_txt_corr:
            return
            
        # Ya no preguntamos ni abrimos preview, usamos el margin_v guardado
        self.btn_render.config(state="disabled")
        threading.Thread(target=self.proceso_render, args=(self.margin_v,), daemon=True).start()

    def proceso_render(self, margin_v):
        try:
            total_duration = get_duration(self.path_vid_orig)
            ass_temp = os.path.join(os.path.dirname(self.path_vid_orig), "temp_render.ass")
            
            # Colores en formato ASS
            ass_white = rgb_to_ass(self.color_primario)
            ass_yellow = rgb_to_ass(self.color_secundario)
            ass_border = rgb_to_ass(self.color_borde)
            
            header = f"[Script Info]\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial Black,{self.font_size.get()},{ass_white},{ass_white},{ass_border},&H00000000,1,0,0,0,100,100,0,0,1,{self.border_width.get()},0,8,10,10,{margin_v},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            with open(self.path_txt_corr, "r", encoding="utf-8") as f:
                lineas = f.readlines()
            with open(ass_temp, "w", encoding="utf-8") as f:
                f.write(header)
                for linea in lineas:
                    partes = linea.split("#")
                    t_data = partes[1].strip().split("|")
                    texto_completo = partes[2].strip()
                    
                    # Detectar altura específica
                    dialog_margin = margin_v
                    if "{{" in texto_completo:
                        match = re.search(r"\{\{(\d+)\}\}", texto_completo)
                        if match:
                            dialog_margin = int(match.group(1))
                            texto_completo = re.sub(r"\{\{\d+\}\}", "", texto_completo).strip()

                    texto_corr = texto_completo.split(" ")
                    start_g, end_g = partes[0].strip(), format_timestamp(float(t_data[-1].split(":")[1]))
                    
                    # Función para estimar el ancho en el render (PlayResX=1080)
                    # Arial Black es ancha, estimamos ~0.6 del font_size por caracter
                    f_size = self.font_size.get()
                    def width_func_ass(t):
                        return len(t) * f_size * 0.6
                    
                    texto_wrapped = wrap_text_pyramid(texto_completo, 1000, width_func_ass) # 1000 de margen de seguridad
                    
                    f.write(f"Dialogue: 0,{start_g},{end_g},Default,,0,0,{dialog_margin},,{texto_wrapped}\n")
                    if self.estilo.get() == "animado":
                        # Para el animado, el wrap complica el resalte de colores si no se maneja bien \N.
                        # Por simplicidad, si hay \N, lo tratamos como espacio para el cálculo de palabras
                        # pero al escribir el resalte, debemos mantener la estructura.
                        # Una forma simple es usar el texto_wrapped y reemplazar la palabra actual.
                        
                        palabras_wrapped = texto_wrapped.replace("\\N", " ").split(" ")
                        
                        for idx, t_range in enumerate(t_data):
                            if idx >= len(palabras_wrapped): break
                            s_w, e_w = t_range.split(":"); w_start, w_end = format_timestamp(float(s_w)), format_timestamp(float(e_w))
                            
                            # Reconstruir el texto con el resalte
                            # Buscamos la palabra i-ésima en el texto wrapped para cambiarle el color
                            count = 0
                            res_parts = []
                            for p in texto_wrapped.split(" "):
                                if "\\N" in p:
                                    sub_p = p.split("\\N")
                                    # Caso "palabra\\Npalabra"
                                    new_sub = []
                                    for sp in sub_p:
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
                            f.write(f"Dialogue: 1,{w_start},{w_end},Default,,0,0,{dialog_margin},,{{\\c{ass_white}}}{res}\n")

            output = os.path.splitext(self.path_vid_orig)[0] + "_FINAL.mp4"
            ass_path_fixed = os.path.abspath(ass_temp).replace("\\", "/").replace(":", "\\:")
            ffmpeg = resource_path("ffmpeg.exe")
            
            cmd = [ffmpeg, '-i', self.path_vid_orig, '-vf', f"ass='{ass_path_fixed}'", '-c:v', 'libx264', '-crf', '18', '-c:a', 'copy', output, '-y', '-progress', 'pipe:1']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            
            for line in process.stdout:
                if "out_time=" in line:
                    match = re.search(r'out_time=(\d{2}:\d{2}:\d{2})', line)
                    if match:
                        cur = time_to_seconds(match.group(1))
                        perc = min((cur / total_duration) * 100, 100)
                        self.progress2["value"] = perc
                        self.status_render.config(text=f"Renderizando: {int(perc)}%", fg="orange")
                        self.root.update_idletasks()

            process.wait()
            
            # Forzar 100% al terminar
            self.progress2["value"] = 100
            self.status_render.config(text="¡Video terminado!", fg="green")
            self.root.update_idletasks()

            if os.path.exists(ass_temp): os.remove(ass_temp)
            messagebox.showinfo("Éxito", "¡Video terminado!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            if os.path.exists(ass_temp):
                try: os.remove(ass_temp)
                except: pass 
            self.btn_render.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtituladorApp(root)
    root.mainloop()