import tkinter as tk
from tkinter import ttk, messagebox
import os
import re

class SubtitleEditor:
    def __init__(self, parent, txt_path, on_save_callback=None):
        self.root = tk.Toplevel(parent)
        self.root.title("Editor de Subtítulos")
        self.root.geometry("800x600")  # Más ancho para ver mejor el texto
        self.root.transient(parent)
        # self.root.grab_set() # Quitamos el grab para que pueda interactuar con el preview simultáneamente

        self.txt_path = txt_path
        self.on_save_callback = on_save_callback
        self.entries = []
        self.segments = []
        self.pin_labels = []

        self.setup_ui()
        self.load_subtitles()

    def setup_ui(self):
        # Header refinado
        header = tk.Frame(self.root, bg="#1a1a1a", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="Correction de Subtítulos", fg="#ecf0f1", bg="#1a1a1a", font=("Arial", 14, "bold")).pack()
        tk.Label(header, text="Podés dejar esta ventana abierta mientras usás el preview.", fg="#95a5a6", bg="#1a1a1a", font=("Arial", 9)).pack()

        # Canvas con scroll
        container = tk.Frame(self.root, bg="#f0f0f0")
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # El frame contenedor del texto ahora tiene un ancho más generoso
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f0f0f0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=780)
        self.root.bind("<Configure>", self._on_window_resize)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Footer con botones más modernos
        footer = tk.Frame(self.root, pady=12, bg="#ffffff")
        footer.pack(fill="x")
        
        btn_save = tk.Button(footer, text="💾 GUARDAR CAMBIOS", command=self.save_and_exit, 
                             bg="#27ae60", fg="white", font=("Arial", 10, "bold"), padx=25, pady=8, relief="flat", cursor="hand2")
        btn_save.pack(side="right", padx=20)

        btn_reset = tk.Button(footer, text="🔄 RESETEAR ALTURAS", command=self.reset_all_heights, 
                              bg="#95a5a6", fg="white", font=("Arial", 10), padx=15, pady=8, relief="flat", cursor="hand2")
        btn_reset.pack(side="right")
        
        btn_cancel = tk.Button(footer, text="Cerrar", command=self.root.destroy, 
                               bg="white", fg="#7f8c8d", font=("Arial", 10), padx=15, pady=8, relief="flat", cursor="hand2")
        btn_cancel.pack(side="right")

    def _on_window_resize(self, event):
        # Ajustar el ancho del contenido al del canvas si la ventana cambia de tamaño
        canvas_width = event.width - 20 # Pequeño margen
        if canvas_width > 100:
            self.canvas.itemconfig(self.canvas_frame, width=canvas_width)

    def _on_mousewheel(self, event):
        if self.root.winfo_exists():
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_subtitles(self):
        if not os.path.exists(self.txt_path):
            messagebox.showerror("Error", "No se encontró el archivo de texto.")
            self.root.destroy()
            return

        with open(self.txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines):
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

                # Row UI mejorada - Renglones largos
                row_wrapper = tk.Frame(self.scrollable_frame, bg="#f0f0f0", padx=10, pady=2)
                row_wrapper.pack(fill="x")
                
                row = tk.Frame(row_wrapper, bg="white", padx=10, pady=8, highlightthickness=1, highlightbackground="#e0e0e0")
                row.pack(fill="x", expand=True)
                
                lbl_time = tk.Label(row, text=display_time, font=("Segoe UI", 9), width=8, anchor="w", fg="#95a5a6", bg="white")
                lbl_time.pack(side="left")
                
                # Input Field más largo y estético
                entry = tk.Entry(row, font=("Segoe UI", 11), relief="flat", bg="#ffffff", fg="#2c3e50")
                entry.insert(0, full_text)
                entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
                
                lbl_h = None
                if height:
                    lbl_h = tk.Label(row, text="📌", fg="#f39c12", bg="white", font=("Arial", 10))
                    lbl_h.pack(side="right")
                
                self.pin_labels.append(lbl_h)
                self.entries.append(entry)
                
            except Exception as e:
                print(f"Error parseando línea {idx}: {e}")

    def reset_all_heights(self):
        # Limpiar alturas en los datos
        for segment in self.segments:
            segment["height"] = ""
        
        # Quitar los emojis de pin de la UI
        for lbl in self.pin_labels:
            if lbl:
                lbl.destroy()
        self.pin_labels = [None] * len(self.segments)
        
        # Guardar cambios inmediatamente para aplicar el reseteo
        self.save_and_exit()

    def save_and_exit(self):
        try:
            with open(self.txt_path, "w", encoding="utf-8") as f:
                for idx, segment in enumerate(self.segments):
                    new_text = self.entries[idx].get().strip().upper()
                    line = f"{segment['display_time']} # {segment['word_timestamps']} # {new_text}"
                    if segment["height"]:
                        line += f" {segment['height']}"
                    f.write(line + "\n")
            
            if self.on_save_callback:
                self.on_save_callback()
            
            # self.root.destroy() # Podría no cerrarse para permitir seguir editando
            self.root.title("✅ CAMBIOS GUARDADOS")
            self.root.after(1000, lambda: self.root.title("Editor de Subtítulos") if self.root.winfo_exists() else None)
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

if __name__ == "__main__":
    # Test
    root = tk.Tk()
    root.withdraw()
    # Create dummy file for test
    with open("test.txt", "w", encoding="utf-8") as f:
        f.write("00:00:01 # 1.0:2.0|2.0:3.0 # HOLA MUNDO\n")
        f.write("00:00:03 # 3.0:4.0|4.0:5.0 # ESTO ES TEST {{300}}\n")
    SubtitleEditor(root, "test.txt")
    root.mainloop()
