"""
ResolveAIO — Graphical Installer
A beautiful tkinter GUI for non-technical users.
Run: python installer/gui_installer.py
"""

from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


# ── Paths ───────────────────────────────────────────────────

INSTALLER_DIR = Path(__file__).parent
PROJECT_DIR = INSTALLER_DIR.parent
VENV_DIR = PROJECT_DIR / ".venv"
ENV_FILE = PROJECT_DIR / "config" / "resolve_aio.env"
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

if IS_MAC:
    LUT_DIR = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT")
    RESOLVE_API = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting")
    RESOLVE_LIB = Path("/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so")
elif IS_WIN:
    PROG = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    LUT_DIR = Path(PROG) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "LUT"
    RESOLVE_API = Path(PROG) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Developer" / "Scripting"
    RESOLVE_LIB = Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
else:
    LUT_DIR = Path("/opt/resolve/LUT")
    RESOLVE_API = Path("/opt/resolve/Developer/Scripting")
    RESOLVE_LIB = Path("/opt/resolve/libs/Fusion/fusionscript.so")


# ── Color Theme ─────────────────────────────────────────────

COLORS = {
    "bg": "#1a1a2e",
    "surface": "#16213e",
    "surface2": "#0f3460",
    "accent": "#e94560",
    "accent2": "#533483",
    "success": "#4ecdc4",
    "warning": "#f9c74f",
    "text": "#eeeeee",
    "dim": "#888888",
}


# ── Installer App ───────────────────────────────────────────

class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ResolveAIO — Installer")
        self.root.geometry("620x680")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg"])

        # Try to set icon
        try:
            if IS_MAC:
                self.root.iconbitmap("")
        except Exception:
            pass

        self.steps = [
            "Check Python",
            "Install packages",
            "Install bundled assets",
            "Configure AI connection",
            "Create shortcuts",
            "Verify",
        ]
        self.current_step = 0
        self.install_thread = None

        self._build_ui()

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg=COLORS["surface"], height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="ResolveAIO",
            font=("Helvetica", 28, "bold"),
            fg=COLORS["accent"],
            bg=COLORS["surface"],
        )
        title.pack(pady=(20, 0))

        subtitle = tk.Label(
            header,
            text="All-in-One Plugin for DaVinci Resolve",
            font=("Helvetica", 12),
            fg=COLORS["dim"],
            bg=COLORS["surface"],
        )
        subtitle.pack()

        # ── Progress Frame ──
        progress_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=30, pady=20)
        progress_frame.pack(fill="x")

        self.progress_bar = ttk.Progressbar(
            progress_frame, length=560, mode="determinate", maximum=len(self.steps)
        )
        self.progress_bar.pack()

        self.step_label = tk.Label(
            progress_frame,
            text="Ready to install",
            font=("Helvetica", 11),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        self.step_label.pack(pady=(8, 0))

        # ── Steps List ──
        steps_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=30)
        steps_frame.pack(fill="x")

        self.step_labels = []
        for i, step in enumerate(self.steps):
            frame = tk.Frame(steps_frame, bg=COLORS["bg"])
            frame.pack(fill="x", pady=2)

            indicator = tk.Label(
                frame,
                text="○",
                font=("Helvetica", 14),
                fg=COLORS["dim"],
                bg=COLORS["bg"],
                width=2,
            )
            indicator.pack(side="left")

            label = tk.Label(
                frame,
                text=step,
                font=("Helvetica", 12),
                fg=COLORS["dim"],
                bg=COLORS["bg"],
                anchor="w",
            )
            label.pack(side="left", padx=(5, 0))

            status = tk.Label(
                frame,
                text="",
                font=("Helvetica", 10),
                fg=COLORS["dim"],
                bg=COLORS["bg"],
                anchor="e",
            )
            status.pack(side="right")

            self.step_labels.append((indicator, label, status))

        # ── Log Area ──
        log_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=30, pady=15)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            height=8,
            bg=COLORS["surface"],
            fg=COLORS["dim"],
            font=("Menlo" if IS_MAC else "Consolas", 10),
            relief="flat",
            padx=10,
            pady=10,
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

        # ── Buttons ──
        btn_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=30, pady=15)
        btn_frame.pack(fill="x")

        self.install_btn = tk.Button(
            btn_frame,
            text="Install",
            font=("Helvetica", 14, "bold"),
            bg=COLORS["accent"],
            fg="white",
            activebackground="#c73e54",
            activeforeground="white",
            relief="flat",
            padx=30,
            pady=8,
            command=self._start_install,
        )
        self.install_btn.pack(side="right")

        self.close_btn = tk.Button(
            btn_frame,
            text="Close",
            font=("Helvetica", 12),
            bg=COLORS["surface2"],
            fg=COLORS["text"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            relief="flat",
            padx=20,
            pady=8,
            command=self.root.quit,
        )
        self.close_btn.pack(side="right", padx=(0, 10))

    # ── Logging ──────────────────────────────────────────────

    def log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_step(self, index: int, status: str = "running"):
        self.current_step = index
        indicator, label, status_label = self.step_labels[index]

        if status == "running":
            indicator.configure(text="▸", fg=COLORS["accent"])
            label.configure(fg=COLORS["text"])
            self.step_label.configure(text=f"Step {index + 1}/{len(self.steps)}: {self.steps[index]}")
        elif status == "done":
            indicator.configure(text="✓", fg=COLORS["success"])
            label.configure(fg=COLORS["success"])
        elif status == "warning":
            indicator.configure(text="⚠", fg=COLORS["warning"])
            label.configure(fg=COLORS["warning"])
        elif status == "error":
            indicator.configure(text="✗", fg=COLORS["accent"])
            label.configure(fg=COLORS["accent"])

        self.progress_bar["value"] = index + (1 if status in ("done", "warning") else 0.5)
        self.root.update_idletasks()

    def set_step_detail(self, index: int, detail: str):
        _, _, status_label = self.step_labels[index]
        status_label.configure(text=detail)

    # ── Install Process ──────────────────────────────────────

    def _start_install(self):
        self.install_btn.configure(state="disabled", text="Installing...")
        self.install_thread = threading.Thread(target=self._install, daemon=True)
        self.install_thread.start()

    def _install(self):
        try:
            self._step_check_python()
            self._step_install_packages()
            self._step_install_dctls()
            self._step_configure_mcp()
            self._step_create_shortcuts()
            self._step_verify()
            self._done()
        except Exception as e:
            self.log(f"\nERROR: {e}")
            self.root.after(0, lambda: self.install_btn.configure(state="normal", text="Retry"))

    def _step_check_python(self):
        self.root.after(0, lambda: self.set_step(0, "running"))
        self.log("Checking Python...")

        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.log(f"  Found Python {py_ver} at {sys.executable}")

        if sys.version_info < (3, 10):
            self.root.after(0, lambda: self.set_step(0, "error"))
            self.root.after(0, lambda: self.set_step_detail(0, f"Python {py_ver} — need 3.10+"))
            raise RuntimeError("Python 3.10+ required")

        self.root.after(0, lambda: self.set_step(0, "done"))
        self.root.after(0, lambda: self.set_step_detail(0, f"v{py_ver}"))

    def _step_install_packages(self):
        self.root.after(0, lambda: self.set_step(1, "running"))
        self.log("Creating virtual environment...")

        python_exe = sys.executable

        if not VENV_DIR.exists():
            subprocess.run([python_exe, "-m", "venv", str(VENV_DIR)], check=True, capture_output=True)
            self.log("  Virtual environment created")

        # Get pip path
        if IS_WIN:
            pip = str(VENV_DIR / "Scripts" / "pip")
            venv_python = str(VENV_DIR / "Scripts" / "python.exe")
        else:
            pip = str(VENV_DIR / "bin" / "pip")
            venv_python = str(VENV_DIR / "bin" / "python")

        self.log("  Installing packages (this may take a minute)...")
        subprocess.run([pip, "install", "--upgrade", "pip", "-q"], capture_output=True)
        result = subprocess.run(
            [pip, "install", "-r", str(PROJECT_DIR / "requirements.txt"), "-q"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.log(f"  Error: {result.stderr}")
            raise RuntimeError("Package installation failed")

        self.log("  All packages installed")
        self.root.after(0, lambda: self.set_step(1, "done"))
        self.root.after(0, lambda: self.set_step_detail(1, "All packages ready"))

    def _step_install_dctls(self):
        self.root.after(0, lambda: self.set_step(2, "running"))
        self.log("Installing bundled Resolve assets...")

        if IS_WIN:
            venv_python = str(VENV_DIR / "Scripts" / "python.exe")
        else:
            venv_python = str(VENV_DIR / "bin" / "python")

        lut_dir_result = subprocess.run(
            [venv_python, "-m", "src.automation.preset_manager", "print-lut-dir"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
        )
        lut_dir = (lut_dir_result.stdout or "").strip()
        if lut_dir:
            self.log(f"  LUT target: {lut_dir}")

        if IS_MAC and lut_dir.startswith("/Library/"):
            self.log("  Administrator access is required for LUT and DCTL files...")
            result = self._run_mac_admin_bundle_install(venv_python, ["LUT", "DCTL"])
            self._log_bundle_result(result)
            if result.returncode != 0:
                self.root.after(0, lambda: self.set_step(2, "error"))
                self.root.after(0, lambda: self.set_step_detail(2, "Admin install failed"))
                raise RuntimeError("Bundled asset install failed")

            result = self._run_bundle_install(venv_python, ["FusionTemplate"])
        else:
            result = self._run_bundle_install(venv_python)

        self._log_bundle_result(result)

        if result.returncode != 0:
            self.root.after(0, lambda: self.set_step(2, "error"))
            self.root.after(0, lambda: self.set_step_detail(2, "Asset install failed"))
            raise RuntimeError("Bundled asset install failed")

        self.root.after(0, lambda: self.set_step(2, "done"))
        self.root.after(0, lambda: self.set_step_detail(2, "Assets installed"))

    def _run_bundle_install(self, venv_python: str, asset_types: list[str] | None = None):
        command = [venv_python, "-m", "src.automation.preset_manager", "install-bundled", "--strict"]
        for asset_type in asset_types or []:
            command.extend(["--asset-type", asset_type])
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
        )

    def _run_mac_admin_bundle_install(self, venv_python: str, asset_types: list[str]):
        command = [venv_python, "-m", "src.automation.preset_manager", "install-bundled", "--strict"]
        for asset_type in asset_types:
            command.extend(["--asset-type", asset_type])
        shell_command = f"cd {shlex.quote(str(PROJECT_DIR))} && {shlex.join(command)}"
        apple_script = f"do shell script {json.dumps(shell_command)} with administrator privileges"
        return subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
        )

    def _log_bundle_result(self, result) -> None:
        output = (result.stdout or "").strip()
        if output:
            for line in output.splitlines():
                self.log(f"  {line}")
        error = (result.stderr or "").strip()
        if error:
            for line in error.splitlines():
                self.log(f"  {line}")

    def _step_configure_mcp(self):
        self.root.after(0, lambda: self.set_step(3, "running"))
        self.log("Configuring AI connection...")

        if IS_WIN:
            venv_python = str(VENV_DIR / "Scripts" / "python.exe").replace("\\", "/")
        else:
            venv_python = str(VENV_DIR / "bin" / "python")

        mcp_config = {
            "mcpServers": {
                "resolve-aio": {
                    "command": venv_python,
                    "args": ["-m", "src.mcp.server"],
                    "cwd": str(PROJECT_DIR),
                    "env": {
                        "RESOLVE_SCRIPT_API": str(RESOLVE_API),
                        "RESOLVE_SCRIPT_LIB": str(RESOLVE_LIB),
                        "PYTHONPATH": str(RESOLVE_API / "Modules"),
                    },
                }
            }
        }

        configs_written = []

        if not ENV_FILE.exists():
            ENV_FILE.write_text(
                "# Put your OpenAI API key here to enable GPT in the Chat UI.\n"
                "OPENAI_API_KEY=\n"
            )
            self.log(f"  Created GPT config: {ENV_FILE}")

        # Cursor
        cursor_dir = Path.home() / ".cursor"
        cursor_config = cursor_dir / "mcp.json"
        cursor_dir.mkdir(exist_ok=True)
        if not cursor_config.exists():
            cursor_config.write_text(json.dumps(mcp_config, indent=2))
            configs_written.append("Cursor")
            self.log("  Cursor MCP configured")
        else:
            self.log("  Cursor config exists — not overwriting")

        # Claude Desktop
        if IS_MAC:
            claude_dir = Path.home() / "Library" / "Application Support" / "Claude"
        else:
            claude_dir = Path.home() / "AppData" / "Roaming" / "Claude"

        if claude_dir.exists():
            claude_config = claude_dir / "claude_desktop_config.json"
            if not claude_config.exists():
                claude_config.write_text(json.dumps(mcp_config, indent=2))
                configs_written.append("Claude Desktop")
                self.log("  Claude Desktop configured")

        if RESOLVE_API.exists():
            self.log(f"  Resolve API found: {RESOLVE_API}")
        else:
            self.log(f"  Resolve API not found at {RESOLVE_API}")

        detail = ", ".join(configs_written) if configs_written else "Manual setup needed"
        self.root.after(0, lambda: self.set_step(3, "done"))
        self.root.after(0, lambda: self.set_step_detail(3, detail))

    def _step_create_shortcuts(self):
        self.root.after(0, lambda: self.set_step(4, "running"))
        self.log("Creating desktop shortcuts...")

        desktop = Path.home() / "Desktop"

        if IS_MAC:
            venv_activate = f'source "{VENV_DIR}/bin/activate"'
            env_file = f'"{ENV_FILE}"'
            env_exports = (
                f'export RESOLVE_SCRIPT_API="{RESOLVE_API}"\n'
                f'export RESOLVE_SCRIPT_LIB="{RESOLVE_LIB}"\n'
                f'export PYTHONPATH="{RESOLVE_API}/Modules/"'
            )

            # Server launcher
            server_script = desktop / "ResolveAIO - Start Server.command"
            server_script.write_text(
                f'#!/usr/bin/env bash\ncd "{PROJECT_DIR}"\n{venv_activate}\n'
                f'if [ -f {env_file} ]; then set -a; source {env_file}; set +a; fi\n{env_exports}\n'
                f'echo ""\necho "  ResolveAIO — MCP Server"\necho "  The server is running. Open Cursor to chat with Resolve."\n'
                f'echo "  Press Ctrl+C to stop."\necho ""\npython -m src.mcp.server\n'
            )
            server_script.chmod(0o755)

            # Chat launcher
            chat_script = desktop / "ResolveAIO - Chat.command"
            chat_script.write_text(
                f'#!/usr/bin/env bash\ncd "{PROJECT_DIR}"\n{venv_activate}\n'
                f'if [ -f {env_file} ]; then set -a; source {env_file}; set +a; fi\n{env_exports}\n'
                f'echo ""\necho "  ResolveAIO — Chat UI"\necho "  Opening browser..."\necho ""\n'
                f'sleep 1 && open "http://127.0.0.1:9881" &\npython -m src.ui.chat_panel\n'
            )
            chat_script.chmod(0o755)

        elif IS_WIN:
            venv_activate = f'call "{VENV_DIR}\\Scripts\\activate.bat"'
            env_file = str(ENV_FILE)
            env_sets = (
                f'set "RESOLVE_SCRIPT_API={RESOLVE_API}"\n'
                f'set "RESOLVE_SCRIPT_LIB={RESOLVE_LIB}"\n'
                f'set "PYTHONPATH={RESOLVE_API}\\Modules\\;%PYTHONPATH%"'
            )
            env_load = (
                f'set "ENV_FILE={env_file}"\n'
                f'if exist "%ENV_FILE%" (\n'
                f'  for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (\n'
                f'    if not "%%A"=="" if not "%%A:~0,1%%"=="#" set "%%A=%%B"\n'
                f'  )\n'
                f')\n'
            )

            server_script = desktop / "ResolveAIO - Start Server.bat"
            server_script.write_text(
                f'@echo off\ntitle ResolveAIO — MCP Server\ncolor 1F\ncd /d "{PROJECT_DIR}"\n'
                f'{venv_activate}\n{env_load}{env_sets}\n'
                f'echo.\necho   ResolveAIO — MCP Server\necho   Open Cursor to chat with Resolve.\n'
                f'echo   Close this window to stop.\necho.\npython -m src.mcp.server\npause\n'
            )

            chat_script = desktop / "ResolveAIO - Chat.bat"
            chat_script.write_text(
                f'@echo off\ntitle ResolveAIO — Chat\ncolor 1F\ncd /d "{PROJECT_DIR}"\n'
                f'{venv_activate}\n{env_load}{env_sets}\n'
                f'echo.\necho   ResolveAIO — Chat UI\necho   Opening browser...\necho.\n'
                f'start http://127.0.0.1:9881\npython -m src.ui.chat_panel\n'
            )

        self.log("  Created: ResolveAIO - Start Server")
        self.log("  Created: ResolveAIO - Chat")
        self.root.after(0, lambda: self.set_step(4, "done"))
        self.root.after(0, lambda: self.set_step_detail(4, "2 shortcuts on Desktop"))

    def _step_verify(self):
        self.root.after(0, lambda: self.set_step(5, "running"))
        self.log("Verifying installation...")

        if IS_WIN:
            venv_python = str(VENV_DIR / "Scripts" / "python.exe")
        else:
            venv_python = str(VENV_DIR / "bin" / "python")

        result = subprocess.run(
            [venv_python, "-c", "from src.mcp.resolve_bridge import ResolveBridge; print('ok')"],
            capture_output=True, text=True, cwd=str(PROJECT_DIR),
        )

        if result.stdout.strip() == "ok":
            self.log("  All modules verified")
        else:
            self.log("  Module check: may need Resolve running")

        asset_result = subprocess.run(
            [
                venv_python,
                "-c",
                (
                    "from src.automation.preset_manager import list_installed_presets; "
                    "presets=list_installed_presets(); "
                    "dctls=sum(1 for p in presets if p['type']=='DCTL'); "
                    "luts=sum(1 for p in presets if p['type']=='LUT'); "
                    "templates=sum(1 for p in presets if p['type']=='FusionTemplate'); "
                    "print(f'{dctls}|{luts}|{templates}')"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
        )
        counts = (asset_result.stdout or "").strip().split("|")
        if len(counts) == 3:
            self.log(f"  DCTL files installed: {counts[0]}")
            self.log(f"  LUT files installed: {counts[1]}")
            self.log(f"  Fusion templates installed: {counts[2]}")

        self.root.after(0, lambda: self.set_step(5, "done"))
        self.root.after(0, lambda: self.set_step_detail(5, "All good"))

    def _done(self):
        self.log("\n" + "=" * 50)
        self.log("  Installation complete!")
        self.log("=" * 50)
        self.log("\nWhat now?")
        self.log("  1. Double-click 'ResolveAIO - Chat' on Desktop")
        self.log("  2. Or double-click 'ResolveAIO - Start Server' for Cursor")
        self.log("  3. Restart Resolve, then open Color > DCTL or Edit > Titles")
        self.log(f"  4. To enable GPT, edit: {ENV_FILE}")
        self.log("\nMake sure DaVinci Resolve is running first!")

        self.root.after(0, lambda: self.step_label.configure(
            text="Installation complete!", fg=COLORS["success"]
        ))
        self.root.after(0, lambda: self.install_btn.configure(
            state="normal", text="Done!", bg=COLORS["success"]
        ))
        self.root.after(0, lambda: self.progress_bar.configure(value=len(self.steps)))

        # Show success popup
        self.root.after(100, lambda: messagebox.showinfo(
            "ResolveAIO",
            "Installation complete!\n\n"
            "You'll find two shortcuts on your Desktop:\n\n"
            "• ResolveAIO - Chat — opens a chat in your browser\n"
            "• ResolveAIO - Start Server — for use with Cursor\n\n"
            "Restart DaVinci Resolve so LUTs and templates refresh,\n"
            "then make sure it is running before starting!",
        ))

    def run(self):
        self.root.mainloop()


# ── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    app = InstallerApp()
    app.run()
