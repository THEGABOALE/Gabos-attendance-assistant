import sys
import subprocess
import threading
import time
import json
import runpy
from pathlib import Path
import customtkinter as ctk
import psutil

# --- INYECCIÓN DEL PATH ---
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from attendance_assistant.config.settings import config

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class AttendanceBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Attendance Assistant")
        self.geometry("900x540")
        self.resizable(False, False)

        self.bot_process = None
        self.log_file = config.LOGS_DIR / "attendance_bot.log"
        self.schedule_dest = config.SCHEDULE_FILE
        self.pid_file = config.PID_FILE
        self.env_file = config.BASE_DIR / ".env"

        self._build_ui()
        self._start_log_reader()
        self._recover_bot_state()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # AL INICIAR: Verifica si el usuario nuevo ya configuró sus datos
        self.after(500, self._check_env_exists)

    def _check_env_exists(self):
        """Si no hay archivo .env, lanza la ventana de configuración obligatoria."""
        if not self.env_file.exists():
            self.open_settings(force_setup=True)

    def open_settings(self, force_setup=False):
        """Abre la ventana de configuración para ingresar credenciales."""
        # Evita abrir múltiples ventanas
        if hasattr(self, "settings_win") and self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.focus()
            return

        self.settings_win = ctk.CTkToplevel(self)
        self.settings_win.title("Configurar Attendance Assistant" if force_setup else "Ajustes de Credenciales")
        self.settings_win.geometry("430x600")
        self.settings_win.resizable(False, False)
        self.settings_win.transient(self) # Se mantiene por encima de la principal
        self.settings_win.grab_set() # Bloquea la ventana de atrás hasta que termine

        # Título
        title_lbl = ctk.CTkLabel(self.settings_win, text="🔐 Credenciales de acceso", font=ctk.CTkFont(size=20, weight="bold"))
        title_lbl.pack(pady=(20, 10))
        
        desc_lbl = ctk.CTkLabel(self.settings_win, text="Configura tu acceso a UAM Virtual y WhatsApp.", text_color="gray")
        desc_lbl.pack(pady=(0, 20))

        # Lectura de datos actuales (por si quiere editar)
        current_cif = ""
        current_pass = ""
        current_phone = ""
        current_semester_start = ""
        current_semester_end = ""
        if self.env_file.exists():
            try:
                with open(self.env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("UAM_USERNAME="): current_cif = line.split("=")[1].strip().strip('"')
                        if line.startswith("UAM_PASSWORD="): current_pass = line.split("=")[1].strip().strip('"')
                        if line.startswith("WA_PHONE_NUMBER="): 
                            full_phone = line.split("=")[1].strip().strip('"')
                            if full_phone.startswith("505"): current_phone = full_phone[3:]
                        if line.startswith("SEMESTER_START="): current_semester_start = line.split("=")[1].strip().strip('"')
                        if line.startswith("SEMESTER_END="): current_semester_end = line.split("=")[1].strip().strip('"')
            except Exception: pass

        # --- CAMPO CIF ---
        ctk.CTkLabel(self.settings_win, text="CIF / Usuario UAM:", anchor="w").pack(fill="x", padx=40)
        cif_entry = ctk.CTkEntry(self.settings_win, placeholder_text="Ej: 21000000")
        cif_entry.insert(0, current_cif)
        cif_entry.pack(fill="x", padx=40, pady=(0, 15))

        # --- CAMPO CONTRASEÑA ---
        ctk.CTkLabel(self.settings_win, text="Contraseña UAM:", anchor="w").pack(fill="x", padx=40)
        pass_entry = ctk.CTkEntry(self.settings_win, placeholder_text="Tu contraseña", show="*")
        pass_entry.insert(0, current_pass)
        pass_entry.pack(fill="x", padx=40, pady=(0, 15))

        # --- CAMPO TELÉFONO (DISEÑO ESPECIAL) ---
        ctk.CTkLabel(self.settings_win, text="WhatsApp de Notificaciones:", anchor="w").pack(fill="x", padx=40)
        
        phone_frame = ctk.CTkFrame(self.settings_win, fg_color="transparent")
        phone_frame.pack(fill="x", padx=40, pady=(0, 15))
        
        # Etiqueta con bandera y código de Nicaragua
        prefix_lbl = ctk.CTkLabel(phone_frame, text="🇳🇮 +505", font=ctk.CTkFont(weight="bold"), fg_color="#1f538d", corner_radius=5)
        prefix_lbl.pack(side="left", ipadx=10, ipady=4, padx=(0, 10))
        
        phone_entry = ctk.CTkEntry(phone_frame, placeholder_text="Ej: 88887777")
        phone_entry.insert(0, current_phone)
        phone_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(self.settings_win, text="Inicio del semestre (opcional):", anchor="w").pack(fill="x", padx=40)
        semester_start_entry = ctk.CTkEntry(self.settings_win, placeholder_text="YYYY-MM-DD")
        semester_start_entry.insert(0, current_semester_start)
        semester_start_entry.pack(fill="x", padx=40, pady=(0, 12))

        ctk.CTkLabel(self.settings_win, text="Final del semestre (opcional):", anchor="w").pack(fill="x", padx=40)
        semester_end_entry = ctk.CTkEntry(self.settings_win, placeholder_text="YYYY-MM-DD")
        semester_end_entry.insert(0, current_semester_end)
        semester_end_entry.pack(fill="x", padx=40, pady=(0, 18))

        # --- FUNCIÓN DE GUARDADO ---
        def save_settings():
            c = cif_entry.get().strip()
            p = pass_entry.get().strip()
            num = phone_entry.get().strip()
            semester_start = semester_start_entry.get().strip()
            semester_end = semester_end_entry.get().strip()
            
            if not c or not p or not num:
                self._write_to_terminal("\n[ERROR] Faltan datos en la configuración.\n")
                return

            # Construimos el .env exactamente como el bot lo necesita
            env_content = f"""# Credenciales de UAM Virtual
UAM_USERNAME="{c}"
UAM_PASSWORD="{p}"

# Configuraciones del Navegador (Playwright)
HEADLESS_MODE=True
BROWSER_TIMEOUT=30000

# Notificaciones
WA_PHONE_NUMBER="505{num}"

# Resumen web del semestre
SEMESTER_START="{semester_start}"
SEMESTER_END="{semester_end}"
"""
            # Guardamos el archivo .env
            self.env_file.write_text(env_content, encoding="utf-8")
            self._write_to_terminal("\n[Attendance Assistant] Credenciales actualizadas localmente.\n")
            self.settings_win.destroy()

        save_btn = ctk.CTkButton(self.settings_win, text="💾 GUARDAR Y APLICAR", command=save_settings, fg_color="#28a745", hover_color="#218838")
        save_btn.pack(fill="x", padx=40, pady=10)

        # Si es la primera vez y cierra a la fuerza sin guardar, cerramos toda la app
        def on_close_settings():
            if force_setup:
                self.destroy()
            else:
                self.settings_win.destroy()
                
        self.settings_win.protocol("WM_DELETE_WINDOW", on_close_settings)

    def _recover_bot_state(self):
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text())
                if psutil.pid_exists(pid):
                    p = psutil.Process(pid)
                    try:
                        cmdline = " ".join(p.cmdline()).lower()
                    except psutil.AccessDenied:
                        cmdline = ""

                    if "--bot" in cmdline or "monitor.py" in cmdline:
                        self.bot_process = p
                        self.toggle_bot_btn.configure(text="■ DETENER BOT", fg_color="#dc3545", hover_color="#c82333")
                        self.status_label.configure(text="Estado: OPERATIVO", text_color="#28a745")
                        self._write_to_terminal("\n[SISTEMA] Conexión establecida con el bot en segundo plano.\n")
                        return
                self.pid_file.unlink(missing_ok=True)
            except Exception:
                self.pid_file.unlink(missing_ok=True)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#101828")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1) # Empujamos el estatus hacia abajo

        self.logo_label = ctk.CTkLabel(self.sidebar, text="Attendance\nAssistant", font=ctk.CTkFont(size=28, weight="bold"), justify="left")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        self.subtitle_label = ctk.CTkLabel(self.sidebar, text="AutoAttendance Bot", font=ctk.CTkFont(size=11), text_color="gray")
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 40))

        # NUEVO BOTÓN: Ajustes
        self.settings_btn = ctk.CTkButton(self.sidebar, text="⚙️ Ajustes", command=self.open_settings, fg_color="#475467", hover_color="#344054", height=35)
        self.settings_btn.grid(row=2, column=0, padx=20, pady=(0, 15))

        self.upload_btn = ctk.CTkButton(self.sidebar, text="📁 Cargar Horario", command=self.upload_json, fg_color="#2563eb", hover_color="#1d4ed8", height=40)
        self.upload_btn.grid(row=3, column=0, padx=20, pady=10)

        self.toggle_bot_btn = ctk.CTkButton(self.sidebar, text="▶ INICIAR BOT", command=self.toggle_bot, fg_color="#28a745", hover_color="#218838", height=40)
        self.toggle_bot_btn.grid(row=4, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar, text="Estado: INACTIVO", text_color="#dc3545", font=ctk.CTkFont(weight="bold"))
        self.status_label.grid(row=6, column=0, padx=20, pady=(10, 30), sticky="s")

        self.main_frame = ctk.CTkFrame(self, corner_radius=18, fg_color="#111827")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.terminal_label = ctk.CTkLabel(self.main_frame, text="REGISTRO DEL BOT", font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaaa")
        self.terminal_label.pack(anchor="w", padx=20, pady=(15, 0))

        self.textbox = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#030712", text_color="#86efac", corner_radius=10)
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        self.textbox.insert("0.0", "Iniciando Attendance Assistant...\n[Sistema] Listo para operar.\n")
        self.textbox.configure(state="disabled")

    def upload_json(self):
        file_path = ctk.filedialog.askopenfilename(title="Selecciona tu horario descargado", filetypes=[("Archivos JSON", "*.json")])
        if file_path:
            try:
                self.schedule_dest.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'r', encoding='utf-8-sig') as f_in: data = json.load(f_in)
                if not data or "events" not in data: raise ValueError("Estructura incorrecta.")
                with open(self.schedule_dest, 'w', encoding='utf-8') as f_out: json.dump(data, f_out, indent=4, ensure_ascii=False)
                self._write_to_terminal(f"\n[Attendance Assistant] Horario validado y cargado: {Path(file_path).name}\n")
            except Exception as e:
                self._write_to_terminal(f"\n[ERROR] Falla al procesar el horario: {e}\n")

    def toggle_bot(self):
        # Escudo protector: No arrancar si no hay .env o no hay horario
        if not self.env_file.exists():
            self._write_to_terminal("\n[ERROR] Faltan credenciales. Abre '⚙️ Ajustes'.\n")
            return
        if not self.schedule_dest.exists():
            self._write_to_terminal("\n[ERROR] Falta cargar el horario JSON.\n")
            return

        if self.bot_process is None:
            executable = sys.executable 
            script_args = ["--bot"]
            if not getattr(sys, 'frozen', False):
                script_args.insert(0, str(Path(__file__).resolve()))
                
            popen_kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "cwd": str(config.BASE_DIR),
            }

            if sys.platform.startswith("win"):
                popen_kwargs["creationflags"] = (
                    0x00000008  # DETACHED_PROCESS
                    | 0x00000200  # CREATE_NEW_PROCESS_GROUP
                    | 0x08000000  # CREATE_NO_WINDOW
                )
            else:
                popen_kwargs["start_new_session"] = True

            p = subprocess.Popen([executable] + script_args, **popen_kwargs)
            self.bot_process = p
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(str(p.pid))
            
            self.toggle_bot_btn.configure(text="■ DETENER BOT", fg_color="#dc3545", hover_color="#c82333")
            self.status_label.configure(text="Estado: OPERATIVO", text_color="#28a745")
            self._write_to_terminal("\n[SISTEMA] Bot de asistencia iniciado en segundo plano. Puedes cerrar esta ventana y seguirá activo.\n")
        else:
            try: self.bot_process.terminate()
            except Exception: pass 
            self.bot_process = None
            self.pid_file.unlink(missing_ok=True)
            self.toggle_bot_btn.configure(text="▶ INICIAR BOT", fg_color="#28a745", hover_color="#218838")
            self.status_label.configure(text="Estado: INACTIVO", text_color="#dc3545")
            self._write_to_terminal("\n[SISTEMA] Bot de asistencia detenido.\n")

    def _write_to_terminal(self, text):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end") 
        self.textbox.configure(state="disabled")

    def _start_log_reader(self):
        def tail_logs():
            if not self.log_file.exists(): return
            with open(self.log_file, "r", encoding="utf-8") as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    self.after(0, self._write_to_terminal, line)
        threading.Thread(target=tail_logs, daemon=True).start()

    def on_closing(self):
        if self.bot_process is not None:
            self._write_to_terminal("\n[SISTEMA] Interfaz cerrada. Attendance Assistant sigue activo en segundo plano...\n")
            self.after(200, self.destroy)
        else:
            self.destroy()

# ======================================================================
if __name__ == "__main__":
    if "--bot" in sys.argv:
        runpy.run_module('attendance_assistant.scheduler.monitor', run_name='__main__')
    else:
        app = AttendanceBotGUI()
        app.mainloop()