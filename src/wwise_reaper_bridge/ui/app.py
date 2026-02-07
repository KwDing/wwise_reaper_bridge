# ui/app.py
import tkinter as tk
from tkinter import filedialog, messagebox
from core.bridge_logic import open_in_reaper, modify_source, check_render_format
from core.models import DEFAULT_RENDER_FORMAT
from utils.app_paths import config_json_path, last_selected_jsonl_path
from utils.settings_store import load_settings, save_settings

class UIApi:
    def show_error(self, title, msg): messagebox.showerror(title, msg)
    def show_info(self, title, msg): messagebox.showinfo(title, msg)
    def ask_yes_no(self, title, msg): return messagebox.askyesno(title, msg)

class WwiseReaperBridge:
    def __init__(self, root):
        self.root = root
        self.root.title("Wwise-Reaper Bridge")
        self.root.geometry("400x300")

        self.config_path = config_json_path
        self.last_path = last_selected_jsonl_path
        self.ui = UIApi()

        self.settings = load_settings(config_json_path)
        self.setup_ui()

    def _cooldown_group(self, buttons: list[tk.Button], seconds: float = 2.0) -> None:
        """Disable a group of buttons temporarily."""
        for b in buttons:
            b.config(state="disabled")

        def restore():
            for b in buttons:
                b.config(state="normal")

        self.root.after(int(seconds * 1000), restore)

    def _run_with_group_cooldown(self, func, seconds: float = 2.0) -> None:
        """Lock both main buttons, run func, unlock after cooldown."""
        self._cooldown_group([self.btn_open, self.btn_modify], seconds)

        try:
            func()
        except Exception:
            # If immediate error, unlock early
            for b in [self.btn_open, self.btn_modify]:
                b.config(state="normal")
            raise

    def setup_ui(self):
        self.gear_btn = tk.Button(self.root, text="⚙", command=self.open_settings)
        self.gear_btn.place(x=10, y=10)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(expand=True)

        # Open button (locks both)
        self.btn_open = tk.Button(
            btn_frame,
            text="Open in REAPER",
            width=25,
            command=lambda: self._run_with_group_cooldown(self.on_open, seconds=2.0),
        )
        self.btn_open.pack(pady=10)

        # Modify button (locks both)
        self.btn_modify = tk.Button(
            btn_frame,
            text="Modify Source in Wwise",
            width=25,
            command=lambda: self._run_with_group_cooldown(self.on_modify, seconds=2.0),
        )
        self.btn_modify.pack(pady=10)

        tk.Button(btn_frame, text="Exit", width=25, command=self.root.quit).pack(pady=10)

        self.status_label = tk.Label(self.root, text="", fg="red")
        self.status_label.pack(side="bottom", pady=5)

    def set_status(self, result):
        self.status_label.config(text=result.message, fg=("red" if result.level == "error" else "green"))

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("520x230")  # <-- bigger so you can see everything
        win.resizable(True, False)

        # --- REAPER Path ---
        tk.Label(win, text="REAPER Path:").pack(pady=(10, 4))
        path_var = tk.StringVar(value=getattr(self.settings, "reaper_path", ""))
        entry = tk.Entry(win, textvariable=path_var, width=70)
        entry.pack(pady=(0, 8))

        def browse():
            filename = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
            if filename:
                path_var.set(filename)
                # IMPORTANT: don't overwrite the whole Settings object or you'll lose reaper_render_format
                self.settings.reaper_path = filename
                save_settings(self.config_path, self.settings)

        tk.Button(win, text="Browse", command=browse).pack(pady=(0, 10))

        # --- Render Config (one line) ---
        tk.Label(win, text="REAPER Render Config (RENDER_FORMAT):").pack(pady=(0, 4))

        render_var = tk.StringVar(value=getattr(self.settings, "reaper_render_format", "") or "")
        render_entry = tk.Entry(win, textvariable=render_var, width=70)
        render_entry.pack(pady=(0, 8))

        # --- render config buttons ---
        btn_row = tk.Frame(win)
        btn_row.pack(pady=(0, 10))

        def on_check_render_format():
            check_render_format(self.ui)

        def on_set_default_render_format():
            render_var.set(DEFAULT_RENDER_FORMAT)
            self.settings.reaper_render_format = DEFAULT_RENDER_FORMAT
            save_settings(self.config_path, self.settings)

        def on_save_render_config():
            self.settings.reaper_path = path_var.get().strip()
            self.settings.reaper_render_format = render_var.get().strip()
            save_settings(self.config_path, self.settings)

        tk.Button(btn_row, text="Save Config", command=on_save_render_config).pack(side="left", padx=6)
        tk.Button(btn_row, text="Check in REAPER", command=on_check_render_format).pack(side="left", padx=6)
        tk.Button(btn_row, text="Set to default", command=on_set_default_render_format).pack(side="left", padx=6)

        # --- show config is stored ---
        tk.Label(win, text=f"Config: {self.config_path}", fg="gray").pack(pady=(6, 2))

    def on_open(self):
        r = open_in_reaper(self.config_path, self.last_path, ui=self.ui)
        self.set_status(r)

    def on_modify(self):
        r = modify_source(self.config_path, self.last_path,  ui=self.ui)
        self.set_status(r)

def run():
    root = tk.Tk()
    app = WwiseReaperBridge(root)
    root.mainloop()
