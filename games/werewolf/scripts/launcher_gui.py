import os
import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox

# Simple GUI launcher to run backend/frontend hidden (no separate terminals)
# - Starts backend/frontend as subprocesses with stdout/stderr redirected to log files
# - Uses Windows-specific hiding flag CREATE_NO_WINDOW when available
# - Shows live-tail of logs in an embedded text area and provides Start/Stop controls
#
# Usage: python games/werewolf/scripts/launcher_gui.py
#
# Notes for packaging to exe:
# - When packaging, run this as the main GUI exe (PyInstaller --noconsole).
# - The backend/frontend subprocesses are started hidden so user can't accidentally close them.
# - Logs are written to games/werewolf/logs/*.log and shown in the UI.

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_PY = os.path.join(REPO_ROOT, "games", "werewolf", "backend", "app.py")
FRONTEND_DIR = os.path.join(REPO_ROOT, "games", "werewolf", "frontend")
LOGS_DIR = os.path.join(REPO_ROOT, "games", "werewolf", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

BACKEND_LOG = os.path.join(LOGS_DIR, "backend.log")
BACKEND_ERR = BACKEND_LOG + ".err"
FRONTEND_LOG = os.path.join(LOGS_DIR, "frontend.log")
FRONTEND_ERR = FRONTEND_LOG + ".err"

# Windows-specific flag to hide console windows for subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

class LauncherGUI:
    def __init__(self, master):
        self.master = master
        master.title("Werewolf Launcher (GUI)")

        self.backend_proc = None
        self.frontend_proc = None

        # Controls
        frm = tk.Frame(master)
        frm.pack(fill="x", padx=6, pady=6)

        self.start_backend_btn = tk.Button(frm, text="Start Backend", command=self.start_backend)
        self.start_backend_btn.pack(side="left", padx=4)
        self.stop_backend_btn = tk.Button(frm, text="Stop Backend", command=self.stop_backend, state="disabled")
        self.stop_backend_btn.pack(side="left", padx=4)

        self.start_frontend_btn = tk.Button(frm, text="Start Frontend", command=self.start_frontend)
        self.start_frontend_btn.pack(side="left", padx=4)
        self.stop_frontend_btn = tk.Button(frm, text="Stop Frontend", command=self.stop_frontend, state="disabled")
        self.stop_frontend_btn.pack(side="left", padx=4)

        self.run_eval_btn = tk.Button(frm, text="Run Eval", command=self.run_eval)
        self.run_eval_btn.pack(side="left", padx=10)

        self.clear_btn = tk.Button(frm, text="Clear Logs View", command=self.clear_view)
        self.clear_btn.pack(side="right", padx=4)

        # Log view
        self.log_view = scrolledtext.ScrolledText(master, height=30, width=120, state="disabled")
        self.log_view.pack(fill="both", expand=True, padx=6, pady=(0,6))

        # background thread to tail logs
        self._stop_tail = threading.Event()
        self._tail_thread = threading.Thread(target=self._tail_logs_loop, daemon=True)
        self._tail_thread.start()

    def _append_text(self, text: str):
        self.log_view.configure(state="normal")
        self.log_view.insert("end", text)
        self.log_view.see("end")
        self.log_view.configure(state="disabled")

    def clear_view(self):
        self.log_view.configure(state="normal")
        self.log_view.delete("1.0", "end")
        self.log_view.configure(state="disabled")

    def start_backend(self):
        if self.backend_proc:
            messagebox.showinfo("Info", "Backend already running")
            return
        # Use same Python executable; start backend as script with hidden window
        args = [sys.executable, BACKEND_PY]
        with open(BACKEND_LOG, "a", encoding="utf-8") as out, open(BACKEND_ERR, "a", encoding="utf-8") as err:
            try:
                self.backend_proc = subprocess.Popen(
                    args,
                    stdout=out,
                    stderr=err,
                    creationflags=CREATE_NO_WINDOW,
                    cwd=REPO_ROOT,
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start backend: {e}")
                self.backend_proc = None
                return
        self.start_backend_btn.config(state="disabled")
        self.stop_backend_btn.config(state="normal")
        self._append_text(f"[Launcher] Started backend (pid={self.backend_proc.pid})\n")

    def stop_backend(self):
        if not self.backend_proc:
            return
        try:
            self.backend_proc.terminate()
            self.backend_proc.wait(timeout=5)
        except Exception:
            try:
                self.backend_proc.kill()
            except Exception:
                pass
        self._append_text(f"[Launcher] Stopped backend\n")
        self.backend_proc = None
        self.start_backend_btn.config(state="normal")
        self.stop_backend_btn.config(state="disabled")

    def start_frontend(self):
        if self.frontend_proc:
            messagebox.showinfo("Info", "Frontend already running")
            return
        if not os.path.exists(FRONTEND_DIR):
            messagebox.showwarning("Warning", f"Frontend dir not found: {FRONTEND_DIR}")
            return
        # Run `npm run dev` hidden; ensure node/npm is in PATH
        args = ["npm", "run", "dev", "--", "--port", "5173"]
        with open(FRONTEND_LOG, "a", encoding="utf-8") as out, open(FRONTEND_ERR, "a", encoding="utf-8") as err:
            try:
                self.frontend_proc = subprocess.Popen(
                    args,
                    stdout=out,
                    stderr=err,
                    creationflags=CREATE_NO_WINDOW,
                    cwd=FRONTEND_DIR,
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start frontend: {e}")
                self.frontend_proc = None
                return
        self.start_frontend_btn.config(state="disabled")
        self.stop_frontend_btn.config(state="normal")
        self._append_text(f"[Launcher] Started frontend (pid={self.frontend_proc.pid})\n")

    def stop_frontend(self):
        if not self.frontend_proc:
            return
        try:
            self.frontend_proc.terminate()
            self.frontend_proc.wait(timeout=5)
        except Exception:
            try:
                self.frontend_proc.kill()
            except Exception:
                pass
        self._append_text(f"[Launcher] Stopped frontend\n")
        self.frontend_proc = None
        self.start_frontend_btn.config(state="normal")
        self.stop_frontend_btn.config(state="disabled")

    def run_eval(self):
        eval_script = os.path.join(REPO_ROOT, "games", "werewolf", "scripts", "run_eval.py")
        if not os.path.exists(eval_script):
            messagebox.showwarning("Warning", f"Eval script not found: {eval_script}")
            return
        eval_log = os.path.join(LOGS_DIR, "eval.log")
        eval_err = eval_log + ".err"
        with open(eval_log, "a", encoding="utf-8") as out, open(eval_err, "a", encoding="utf-8") as err:
            try:
                # Run blocking so user knows it completed; hide console
                proc = subprocess.Popen(
                    [sys.executable, eval_script],
                    stdout=out,
                    stderr=err,
                    creationflags=CREATE_NO_WINDOW,
                    cwd=REPO_ROOT,
                )
                self._append_text(f"[Launcher] Running eval (pid={proc.pid})\n")
                proc.wait()
                self._append_text(f"[Launcher] Eval completed (exit={proc.returncode})\n")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run eval: {e}")

    def _tail_file(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                while not self._stop_tail.is_set():
                    line = f.readline()
                    if line:
                        self._append_text(f"[{os.path.basename(path)}] {line}")
                    else:
                        time.sleep(0.3)
        except FileNotFoundError:
            # wait and retry until file exists or stop
            while not self._stop_tail.is_set():
                if os.path.exists(path):
                    return self._tail_file(path)
                time.sleep(0.5)

    def _tail_logs_loop(self):
        # spawn tail threads for all logs
        threads = []
        for p in [BACKEND_LOG, FRONTEND_LOG, os.path.join(LOGS_DIR, "eval.log")]:
            t = threading.Thread(target=self._tail_file, args=(p,), daemon=True)
            t.start()
            threads.append(t)
        # keep running until GUI stops
        while not self._stop_tail.is_set():
            time.sleep(0.5)

    def on_close(self):
        if messagebox.askyesno("Exit", "Stop all processes and exit?"):
            self._stop_tail.set()
            try:
                if self.backend_proc:
                    self.stop_backend()
                if self.frontend_proc:
                    self.stop_frontend()
            except Exception:
                pass
            self.master.destroy()

def main():
    root = tk.Tk()
    app = LauncherGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()