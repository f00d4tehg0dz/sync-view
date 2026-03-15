#!/usr/bin/env python3
"""
Sync View — Desktop Application.

Full GUI with:
  - First-run install wizard (registers native messaging host, optional startup)
  - Main window showing connection status and current media
  - Settings panel (startup toggle, minimize-to-tray toggle)
  - System tray icon when minimized
  - Native messaging bridge for the Firefox extension
  - Supports YouTube, Netflix, Spotify, Twitch, Hulu, Disney+, Prime Video,
    SoundCloud, Crunchyroll, Max, Apple TV+, YouTube Music, and Plex
"""

import ctypes
import ctypes.wintypes
import json
import os
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
import urllib.request
import uuid
import webbrowser
import winreg

# ── Constants ────────────────────────────────────────────────────────────────

APP_NAME = "Sync View"
APP_VERSION = "3.0.1"
DISCORD_CLIENT_ID = "1482383187882545233"
UPDATE_CHECK_URL = "https://syncview.app/version.json"

STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_VALUE = "SyncView"
NATIVE_HOST_REG_KEY = r"Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc"

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "SyncView")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def get_app_dir():
    """Get the directory where this app lives (works for frozen exe or .py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Dark theme colors (Discord-inspired)
C_BG = "#1e1e2e"
C_BG_SECONDARY = "#181825"
C_BG_CARD = "#313244"
C_BG_INPUT = "#45475a"
C_TEXT = "#cdd6f4"
C_TEXT_DIM = "#6c7086"
C_TEXT_BRIGHT = "#ffffff"
C_ACCENT = "#cba6f7"       # Purple accent
C_GREEN = "#a6e3a1"
C_RED = "#f38ba8"
C_YELLOW = "#f9e2af"
C_BLUE = "#89b4fa"
C_BORDER = "#45475a"


# ── Config ───────────────────────────────────────────────────────────────────


def load_config():
    defaults = {
        "first_run_complete": False,
        "start_with_windows": False,
        "minimize_to_tray": True,
        "start_minimized": False,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ── Update Checker ──────────────────────────────────────────────────────────


def _parse_version(v):
    """Parse a version string like '2.1.0' into a tuple of ints."""
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0, 0, 0)


def check_for_update():
    """Check the remote version.json and return (new_version, release_url, changelog) or None."""
    try:
        req = urllib.request.Request(UPDATE_CHECK_URL, headers={"User-Agent": f"SyncView/{APP_VERSION}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        remote_version = data.get("version", "")
        if _parse_version(remote_version) > _parse_version(APP_VERSION):
            return (remote_version, data.get("release_url", ""), data.get("changelog", ""))
    except Exception:
        pass
    return None


# ── Discord IPC ──────────────────────────────────────────────────────────────


class DiscordIPC:
    OP_HANDSHAKE = 0
    OP_FRAME = 1

    def __init__(self, client_id):
        self.client_id = client_id
        self.pipe_handle = None
        self.is_connected = False
        self._lock = threading.Lock()

    def connect(self):
        with self._lock:
            if self.is_connected:
                return True
            kernel32 = ctypes.windll.kernel32
            for pipe_num in range(10):
                pipe_path = f"\\\\.\\pipe\\discord-ipc-{pipe_num}"
                try:
                    handle = kernel32.CreateFileW(
                        pipe_path, 0x80000000 | 0x40000000, 0, None, 3, 0, None
                    )
                    if handle in (-1, 0xFFFFFFFF):
                        continue
                    self.pipe_handle = handle
                    self._raw_send(self.OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
                    resp = self._raw_recv()
                    if resp and resp.get("cmd") == "DISPATCH" and resp.get("evt") == "READY":
                        self.is_connected = True
                        return True
                    kernel32.CloseHandle(handle)
                    self.pipe_handle = None
                except Exception:
                    continue
            return False

    def _raw_send(self, op, data):
        payload = json.dumps(data).encode("utf-8")
        msg = struct.pack("<II", op, len(payload)) + payload
        written = ctypes.wintypes.DWORD()
        ctypes.windll.kernel32.WriteFile(self.pipe_handle, msg, len(msg), ctypes.byref(written), None)

    def _raw_recv(self):
        try:
            buf = ctypes.create_string_buffer(65536)
            nread = ctypes.wintypes.DWORD()
            ok = ctypes.windll.kernel32.ReadFile(self.pipe_handle, buf, 65536, ctypes.byref(nread), None)
            if not ok or nread.value < 8:
                return None
            data = buf.raw[: nread.value]
            _op, length = struct.unpack("<II", data[:8])
            return json.loads(data[8 : 8 + length].decode("utf-8"))
        except Exception:
            return None

    def set_activity(self, activity):
        with self._lock:
            if not self.is_connected:
                return False
            try:
                self._raw_send(self.OP_FRAME, {
                    "cmd": "SET_ACTIVITY",
                    "args": {"pid": os.getpid(), "activity": activity},
                    "nonce": str(uuid.uuid4()),
                })
                self._raw_recv()
                return True
            except Exception:
                self.is_connected = False
                return False

    def clear_activity(self):
        with self._lock:
            if not self.is_connected:
                return False
            try:
                self._raw_send(self.OP_FRAME, {
                    "cmd": "SET_ACTIVITY",
                    "args": {"pid": os.getpid()},
                    "nonce": str(uuid.uuid4()),
                })
                self._raw_recv()
                return True
            except Exception:
                self.is_connected = False
                return False

    def close(self):
        with self._lock:
            try:
                if self.pipe_handle:
                    ctypes.windll.kernel32.CloseHandle(self.pipe_handle)
            except Exception:
                pass
            self.pipe_handle = None
            self.is_connected = False


# ── Native Messaging I/O ────────────────────────────────────────────────────


def read_native_message():
    raw = sys.stdin.buffer.read(4)
    if not raw or len(raw) < 4:
        return None
    length = struct.unpack("<I", raw)[0]
    if length == 0:
        return None
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode("utf-8")) if data else None


def send_native_message(msg):
    encoded = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


# ── Startup / Registry Helpers ───────────────────────────────────────────────


def get_exe_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, STARTUP_REG_VALUE)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_startup(enabled):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        if enabled:
            exe = get_exe_path()
            cmd = f'pythonw "{exe}" --minimized' if exe.endswith(".py") else f'"{exe}" --minimized'
            winreg.SetValueEx(key, STARTUP_REG_VALUE, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, STARTUP_REG_VALUE)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def is_native_host_registered():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, NATIVE_HOST_REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def register_native_host():
    """Create the native messaging manifest and register it in the Windows registry."""
    app_dir = get_app_dir()

    # Determine the native host executable path
    host_exe = os.path.join(app_dir, "host.exe")
    if os.path.exists(host_exe):
        host_path = host_exe
    else:
        # Dev mode: create a .bat wrapper for host.py
        host_py = os.path.join(app_dir, "host.py")
        host_path = os.path.join(app_dir, "youtube_discord_rpc.bat")
        with open(host_path, "w") as f:
            f.write(f'@echo off\npython "{host_py}" %*\n')

    # Create the JSON manifest
    manifest_path = os.path.join(CONFIG_DIR, "youtube_discord_rpc.json")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    manifest = {
        "name": "youtube_discord_rpc",
        "description": "Sync View native messaging host",
        "path": host_path.replace("/", "\\"),
        "type": "stdio",
        "allowed_extensions": ["sync-view@syncview.app"],
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Register in Windows registry
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, NATIVE_HOST_REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ── Tray Icon (pystray, optional) ───────────────────────────────────────────

_pystray_available = False
try:
    import pystray
    from PIL import Image, ImageDraw
    _pystray_available = True
except ImportError:
    pass


def _create_tray_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill=(255, 0, 0, 255))
    d.polygon([(size * 0.38, size * 0.28), (size * 0.72, size * 0.5), (size * 0.38, size * 0.72)], fill=(255, 255, 255, 255))
    r = 8
    cx, cy = size - 12, size - 12
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(88, 101, 242, 255))
    return img


# ── Tkinter Widgets ─────────────────────────────────────────────────────────


class StatusDot(tk.Canvas):
    """Small colored status dot."""
    def __init__(self, parent, color=C_RED, size=12, **kw):
        super().__init__(parent, width=size, height=size, bg=C_BG_CARD, highlightthickness=0, **kw)
        self._size = size
        self._oval = self.create_oval(1, 1, size - 1, size - 1, fill=color, outline="")

    def set_color(self, color):
        self.itemconfig(self._oval, fill=color)


class Card(tk.Frame):
    """Rounded-look card container."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C_BG_CARD, padx=16, pady=12, **kw)


# ── Setup Wizard ─────────────────────────────────────────────────────────────


class SetupWizard(tk.Toplevel):
    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete = on_complete
        self.title(f"{APP_NAME} — Setup")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.geometry("520x420")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set()

        self.steps = [self._step_welcome, self._step_install, self._step_options, self._step_done]
        self.current_step = 0

        # Variables for options
        self.var_startup = tk.BooleanVar(value=True)
        self.var_minimize_tray = tk.BooleanVar(value=True)
        self.var_start_minimized = tk.BooleanVar(value=False)

        self.content = tk.Frame(self, bg=C_BG)
        self.content.pack(fill="both", expand=True, padx=30, pady=20)

        self.btn_frame = tk.Frame(self, bg=C_BG)
        self.btn_frame.pack(fill="x", padx=30, pady=(0, 20))

        self.btn_back = tk.Button(self.btn_frame, text="Back", command=self._back,
                                  bg=C_BG_INPUT, fg=C_TEXT, activebackground=C_BORDER,
                                  activeforeground=C_TEXT_BRIGHT, relief="flat", padx=20, pady=6,
                                  font=("Segoe UI", 10))
        self.btn_next = tk.Button(self.btn_frame, text="Next", command=self._next,
                                  bg=C_ACCENT, fg="#1e1e2e", activebackground="#b491d4",
                                  activeforeground="#1e1e2e", relief="flat", padx=20, pady=6,
                                  font=("Segoe UI", 10, "bold"))

        self._show_step()

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _show_step(self):
        self._clear()
        self.steps[self.current_step]()

        # Button visibility
        self.btn_back.pack_forget()
        self.btn_next.pack_forget()
        if self.current_step > 0 and self.current_step < len(self.steps) - 1:
            self.btn_back.pack(side="left")
        self.btn_next.pack(side="right")

        if self.current_step == len(self.steps) - 1:
            self.btn_next.configure(text="Finish")
        else:
            self.btn_next.configure(text="Next")

    def _next(self):
        if self.current_step == len(self.steps) - 1:
            self._finish()
            return
        if self.current_step == 1:
            self._do_install()
        if self.current_step == 2:
            self._apply_options()
        self.current_step += 1
        self._show_step()

    def _back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step()

    def _finish(self):
        config = load_config()
        config["first_run_complete"] = True
        config["start_with_windows"] = self.var_startup.get()
        config["minimize_to_tray"] = self.var_minimize_tray.get()
        config["start_minimized"] = self.var_start_minimized.get()
        save_config(config)
        self.destroy()
        self.on_complete(config)

    def _on_close(self):
        if self.current_step < len(self.steps) - 1:
            if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel setup?", parent=self):
                self.destroy()
                sys.exit(0)
        else:
            self._finish()

    # ── Steps ──

    def _step_welcome(self):
        tk.Label(self.content, text="Welcome to", font=("Segoe UI", 12), bg=C_BG, fg=C_TEXT_DIM).pack(pady=(30, 0))
        tk.Label(self.content, text=APP_NAME, font=("Segoe UI", 22, "bold"), bg=C_BG, fg=C_TEXT_BRIGHT).pack(pady=(4, 8))
        tk.Label(self.content, text=f"v{APP_VERSION}", font=("Segoe UI", 10), bg=C_BG, fg=C_TEXT_DIM).pack()
        tk.Label(self.content, text=(
            "This wizard will set up the native messaging host\n"
            "so Firefox can send your streaming activity to Discord.\n\n"
            "Supports YouTube, Netflix, Spotify, Twitch, and more.\n"
            "Make sure Discord is running before continuing."
        ), font=("Segoe UI", 11), bg=C_BG, fg=C_TEXT, justify="center").pack(pady=(30, 0))

    def _step_install(self):
        tk.Label(self.content, text="Install Components", font=("Segoe UI", 16, "bold"), bg=C_BG, fg=C_TEXT_BRIGHT).pack(anchor="w", pady=(10, 16))

        self.install_status = tk.Frame(self.content, bg=C_BG)
        self.install_status.pack(fill="x", pady=4)

        items = [
            ("Native messaging manifest", "Allows Firefox to talk to this app"),
            ("Windows registry entry", "Registers the host with Firefox"),
        ]
        self._install_labels = []
        for title, desc in items:
            row = tk.Frame(self.install_status, bg=C_BG)
            row.pack(fill="x", pady=6)
            dot = StatusDot(row, color=C_YELLOW, size=10)
            dot.configure(bg=C_BG)
            dot.pack(side="left", padx=(0, 10))
            f = tk.Frame(row, bg=C_BG)
            f.pack(side="left")
            tk.Label(f, text=title, font=("Segoe UI", 11, "bold"), bg=C_BG, fg=C_TEXT).pack(anchor="w")
            tk.Label(f, text=desc, font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_DIM).pack(anchor="w")
            self._install_labels.append(dot)

        tk.Label(self.content, text=(
            "Click Next to install. This writes a small JSON file\n"
            "and a registry key under HKCU (no admin required)."
        ), font=("Segoe UI", 10), bg=C_BG, fg=C_TEXT_DIM, justify="left").pack(anchor="w", pady=(20, 0))

    def _do_install(self):
        success = register_native_host()
        if success:
            for dot in self._install_labels:
                dot.set_color(C_GREEN)
        else:
            for dot in self._install_labels:
                dot.set_color(C_RED)

    def _step_options(self):
        tk.Label(self.content, text="Settings", font=("Segoe UI", 16, "bold"), bg=C_BG, fg=C_TEXT_BRIGHT).pack(anchor="w", pady=(10, 16))

        opts = [
            (self.var_startup, "Start with Windows", "Launch automatically when you log in"),
            (self.var_minimize_tray, "Minimize to system tray", "Hide to tray instead of taskbar when minimized"),
            (self.var_start_minimized, "Start minimized", "Launch straight to the system tray"),
        ]
        for var, title, desc in opts:
            row = tk.Frame(self.content, bg=C_BG)
            row.pack(fill="x", pady=8)
            cb = tk.Checkbutton(row, variable=var, bg=C_BG, fg=C_TEXT, selectcolor=C_BG_INPUT,
                                activebackground=C_BG, activeforeground=C_TEXT, highlightthickness=0)
            cb.pack(side="left", padx=(0, 8))
            f = tk.Frame(row, bg=C_BG)
            f.pack(side="left")
            tk.Label(f, text=title, font=("Segoe UI", 11), bg=C_BG, fg=C_TEXT).pack(anchor="w")
            tk.Label(f, text=desc, font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_DIM).pack(anchor="w")

    def _apply_options(self):
        set_startup(self.var_startup.get())

    def _step_done(self):
        tk.Label(self.content, text="Setup Complete!", font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_GREEN).pack(pady=(40, 12))
        tk.Label(self.content, text=(
            "Everything is configured.\n\n"
            "Next steps:\n"
            "1. Load the Firefox extension (about:debugging)\n"
            "2. Play something on YouTube, Netflix, Spotify, etc.\n"
            "3. Check your Discord profile!"
        ), font=("Segoe UI", 11), bg=C_BG, fg=C_TEXT, justify="center").pack(pady=(10, 0))


# ── Main Application Window ─────────────────────────────────────────────────


class MainApp:
    def __init__(self):
        self.config = load_config()
        self.discord = DiscordIPC(DISCORD_CLIENT_ID)
        self.current_video = None
        self.running = True
        self.tray_icon = None

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.configure(bg=C_BG)
        self.root.geometry("480x520")
        self.root.minsize(400, 440)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Try to set window icon
        try:
            app_dir = get_app_dir()
            for candidate in [
                os.path.join(app_dir, "icon-48.png"),
                os.path.join(app_dir, "..", "icons", "icon-48.png"),
                os.path.join(os.path.dirname(app_dir), "icons", "icon-48.png"),
            ]:
                if os.path.exists(candidate):
                    self.root.iconphoto(True, tk.PhotoImage(file=candidate))
                    break
        except Exception:
            pass

        self._build_ui()

        # Check first run
        if not self.config.get("first_run_complete"):
            self.root.withdraw()
            SetupWizard(self.root, self._on_wizard_complete)
        else:
            if self.config.get("start_minimized") and "--minimized" in sys.argv:
                self.root.withdraw()
                self._show_tray()
            self._start_services()

    def _on_wizard_complete(self, config):
        self.config = config
        if config.get("start_minimized"):
            self.root.withdraw()
            self._show_tray()
        else:
            self.root.deiconify()
        self._start_services()

    def _start_services(self):
        # Connect to Discord in background
        threading.Thread(target=self._connect_discord, daemon=True).start()
        # Start native messaging listener only if stdin is available
        # (not available when built with --windowed / no console)
        if sys.stdin is not None:
            threading.Thread(target=self._native_messaging_loop, daemon=True).start()
        # Check for updates in background
        threading.Thread(target=self._check_update, daemon=True).start()
        # Periodic UI update
        self._poll_ui()

    def _connect_discord(self):
        if self.discord.connect():
            self._set_status("connected")
        else:
            self._set_status("disconnected")

    def _check_update(self):
        result = check_for_update()
        if result:
            new_ver, release_url, changelog = result
            self._log(f"Update available: v{new_ver}")
            self.root.after(0, lambda: self._show_update_banner(new_ver, release_url, changelog))

    def _show_update_banner(self, version, release_url, changelog):
        banner = tk.Frame(self.root, bg="#45475a", pady=8)
        banner.pack(fill="x", before=self.root.winfo_children()[1])  # After header

        tk.Label(banner, text=f"Update available: v{version}",
                 font=("Segoe UI", 10, "bold"), bg="#45475a", fg=C_YELLOW
                 ).pack(side="left", padx=(16, 8))

        if changelog:
            tk.Label(banner, text=f"— {changelog}", font=("Segoe UI", 9),
                     bg="#45475a", fg=C_TEXT_DIM).pack(side="left", padx=(0, 8))

        def open_release():
            url = release_url or "https://github.com/f00d4tehg0dz/sync-view/releases"
            webbrowser.open(url)

        tk.Button(banner, text="Download", command=open_release,
                  bg=C_ACCENT, fg="#1e1e2e", activebackground="#b491d4",
                  activeforeground="#1e1e2e", relief="flat",
                  padx=12, pady=2, font=("Segoe UI", 9, "bold"), cursor="hand2"
                  ).pack(side="right", padx=16)

        tk.Button(banner, text="x", command=banner.destroy,
                  bg="#45475a", fg=C_TEXT_DIM, activebackground="#45475a",
                  activeforeground=C_TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2", width=2
                  ).pack(side="right")

    # ── UI ──

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=C_BG_SECONDARY, pady=14)
        header.pack(fill="x")
        tk.Label(header, text=APP_NAME, font=("Segoe UI", 16, "bold"),
                 bg=C_BG_SECONDARY, fg=C_TEXT_BRIGHT).pack(side="left", padx=20)
        tk.Label(header, text=f"v{APP_VERSION}", font=("Segoe UI", 9),
                 bg=C_BG_SECONDARY, fg=C_TEXT_DIM).pack(side="left", pady=(4, 0))

        # Gear icon for settings
        self.btn_settings = tk.Button(header, text="\u2699", font=("Segoe UI", 16),
                                      bg=C_BG_SECONDARY, fg=C_TEXT_DIM, relief="flat",
                                      activebackground=C_BG_SECONDARY, activeforeground=C_ACCENT,
                                      command=self._open_settings, cursor="hand2")
        self.btn_settings.pack(side="right", padx=20)

        container = tk.Frame(self.root, bg=C_BG)
        container.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Discord Status Card ──
        card1 = Card(container)
        card1.pack(fill="x", pady=(0, 12))

        row = tk.Frame(card1, bg=C_BG_CARD)
        row.pack(fill="x")
        self.status_dot = StatusDot(row, color=C_RED)
        self.status_dot.pack(side="left", padx=(0, 10))
        self.lbl_discord = tk.Label(row, text="Discord: Connecting...",
                                    font=("Segoe UI", 12, "bold"), bg=C_BG_CARD, fg=C_TEXT)
        self.lbl_discord.pack(side="left")

        self.btn_reconnect = tk.Button(row, text="Reconnect", command=self._reconnect,
                                       bg=C_BG_INPUT, fg=C_TEXT, activebackground=C_BORDER,
                                       activeforeground=C_TEXT_BRIGHT, relief="flat",
                                       padx=12, pady=2, font=("Segoe UI", 9), cursor="hand2")
        self.btn_reconnect.pack(side="right")

        self.lbl_client_id = tk.Label(card1, text=f"App ID: {DISCORD_CLIENT_ID}",
                                      font=("Segoe UI", 9), bg=C_BG_CARD, fg=C_TEXT_DIM)
        self.lbl_client_id.pack(anchor="w", pady=(8, 0))

        # ── Now Playing Card ──
        card2 = Card(container)
        card2.pack(fill="x", pady=(0, 12))

        tk.Label(card2, text="NOW PLAYING", font=("Segoe UI", 9, "bold"),
                 bg=C_BG_CARD, fg=C_TEXT_DIM).pack(anchor="w", pady=(0, 8))

        self.now_playing_frame = tk.Frame(card2, bg=C_BG_CARD)
        self.now_playing_frame.pack(fill="x")

        self.lbl_video_title = tk.Label(self.now_playing_frame, text="No media playing",
                                        font=("Segoe UI", 13, "bold"), bg=C_BG_CARD, fg=C_TEXT,
                                        wraplength=380, justify="left", anchor="w")
        self.lbl_video_title.pack(anchor="w")

        self.lbl_video_channel = tk.Label(self.now_playing_frame, text="",
                                          font=("Segoe UI", 10), bg=C_BG_CARD, fg=C_TEXT_DIM)
        self.lbl_video_channel.pack(anchor="w", pady=(2, 0))

        self.lbl_video_progress = tk.Label(self.now_playing_frame, text="",
                                           font=("Segoe UI", 10), bg=C_BG_CARD, fg=C_BLUE)
        self.lbl_video_progress.pack(anchor="w", pady=(4, 0))

        # ── Activity Log Card ──
        card3 = Card(container)
        card3.pack(fill="both", expand=True)

        tk.Label(card3, text="ACTIVITY LOG", font=("Segoe UI", 9, "bold"),
                 bg=C_BG_CARD, fg=C_TEXT_DIM).pack(anchor="w", pady=(0, 6))

        log_frame = tk.Frame(card3, bg=C_BG_INPUT)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, bg=C_BG_INPUT, fg=C_TEXT, font=("Consolas", 9),
                                relief="flat", wrap="word", state="disabled", padx=8, pady=6,
                                insertbackground=C_TEXT, selectbackground=C_ACCENT,
                                selectforeground=C_BG)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Footer
        footer = tk.Frame(self.root, bg=C_BG_SECONDARY, pady=6)
        footer.pack(fill="x", side="bottom")

        self.lbl_native_status = tk.Label(footer, text="Native host: checking...",
                                          font=("Segoe UI", 9), bg=C_BG_SECONDARY, fg=C_TEXT_DIM)
        self.lbl_native_status.pack(side="left", padx=20)

        # Check native host status
        if is_native_host_registered():
            self.lbl_native_status.configure(text="Native host: registered", fg=C_GREEN)
        else:
            self.lbl_native_status.configure(text="Native host: not registered", fg=C_RED)

    def _log(self, message):
        """Append a line to the activity log (thread-safe)."""
        timestamp = time.strftime("%H:%M:%S")
        def _do():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{timestamp}] {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _do)

    def _set_status(self, status):
        """Update Discord connection status (thread-safe)."""
        def _do():
            if status == "connected":
                self.status_dot.set_color(C_GREEN)
                self.lbl_discord.configure(text="Discord: Connected")
            else:
                self.status_dot.set_color(C_RED)
                self.lbl_discord.configure(text="Discord: Disconnected")
        self.root.after(0, _do)
        self._log(f"Discord {'connected' if status == 'connected' else 'disconnected'}")

    def _set_now_playing(self, title=None, channel=None, progress=None):
        def _do():
            if title:
                self.lbl_video_title.configure(text=title, fg=C_TEXT_BRIGHT)
                self.lbl_video_channel.configure(text=channel or "")
                self.lbl_video_progress.configure(text=progress or "")
            else:
                self.lbl_video_title.configure(text="No media playing", fg=C_TEXT_DIM)
                self.lbl_video_channel.configure(text="")
                self.lbl_video_progress.configure(text="")
        self.root.after(0, _do)

    def _reconnect(self):
        self.lbl_discord.configure(text="Discord: Reconnecting...")
        self.status_dot.set_color(C_YELLOW)
        threading.Thread(target=self._do_reconnect, daemon=True).start()

    def _do_reconnect(self):
        self.discord.close()
        if self.discord.connect():
            self._set_status("connected")
        else:
            self._set_status("disconnected")

    def _poll_ui(self):
        """Periodic UI refresh."""
        if self.running:
            self.root.after(5000, self._poll_ui)

    # ── Settings Window ──

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=C_BG)
        win.geometry("400x380")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Settings", font=("Segoe UI", 16, "bold"),
                 bg=C_BG, fg=C_TEXT_BRIGHT).pack(anchor="w", padx=24, pady=(20, 16))

        settings_frame = tk.Frame(win, bg=C_BG)
        settings_frame.pack(fill="x", padx=24)

        # Startup
        var_startup = tk.BooleanVar(value=is_startup_enabled())
        var_tray = tk.BooleanVar(value=self.config.get("minimize_to_tray", True))
        var_minimized = tk.BooleanVar(value=self.config.get("start_minimized", False))

        options = [
            (var_startup, "Start with Windows", "Launch when you log in to Windows"),
            (var_tray, "Minimize to system tray", "Hide to tray instead of closing"),
            (var_minimized, "Start minimized", "Open directly to the system tray"),
        ]

        for var, title, desc in options:
            row = tk.Frame(settings_frame, bg=C_BG)
            row.pack(fill="x", pady=8)
            cb = tk.Checkbutton(row, variable=var, bg=C_BG, fg=C_TEXT, selectcolor=C_BG_INPUT,
                                activebackground=C_BG, activeforeground=C_TEXT, highlightthickness=0)
            cb.pack(side="left", padx=(0, 8))
            f = tk.Frame(row, bg=C_BG)
            f.pack(side="left")
            tk.Label(f, text=title, font=("Segoe UI", 11), bg=C_BG, fg=C_TEXT).pack(anchor="w")
            tk.Label(f, text=desc, font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_DIM).pack(anchor="w")

        # Separator
        tk.Frame(settings_frame, bg=C_BORDER, height=1).pack(fill="x", pady=16)

        # Re-run setup
        tk.Button(settings_frame, text="Re-register Native Host", command=self._reregister_host,
                  bg=C_BG_INPUT, fg=C_TEXT, activebackground=C_BORDER,
                  activeforeground=C_TEXT_BRIGHT, relief="flat",
                  padx=14, pady=6, font=("Segoe UI", 10), cursor="hand2").pack(anchor="w")

        # Info
        tk.Label(settings_frame, text=f"Discord App ID: {DISCORD_CLIENT_ID}",
                 font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_DIM).pack(anchor="w", pady=(16, 0))
        tk.Label(settings_frame, text=f"Config: {CONFIG_FILE}",
                 font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_DIM).pack(anchor="w", pady=(4, 0))

        # Save button
        def save():
            set_startup(var_startup.get())
            self.config["start_with_windows"] = var_startup.get()
            self.config["minimize_to_tray"] = var_tray.get()
            self.config["start_minimized"] = var_minimized.get()
            save_config(self.config)
            self._log("Settings saved")
            win.destroy()

        tk.Button(win, text="Save", command=save,
                  bg=C_ACCENT, fg="#1e1e2e", activebackground="#b491d4",
                  activeforeground="#1e1e2e", relief="flat",
                  padx=24, pady=6, font=("Segoe UI", 10, "bold"), cursor="hand2"
                  ).pack(side="bottom", pady=16)

    def _reregister_host(self):
        if register_native_host():
            self.lbl_native_status.configure(text="Native host: registered", fg=C_GREEN)
            self._log("Native host re-registered successfully")
            messagebox.showinfo("Success", "Native messaging host registered.", parent=self.root)
        else:
            self._log("Failed to register native host")
            messagebox.showerror("Error", "Failed to register native host.", parent=self.root)

    # ── System Tray ──

    def _show_tray(self):
        if not _pystray_available:
            return
        if self.tray_icon:
            return

        def on_show(icon, item):
            icon.stop()
            self.tray_icon = None
            self.root.after(0, self.root.deiconify)

        def on_quit(icon, item):
            icon.stop()
            self.tray_icon = None
            self.root.after(0, self._quit)

        menu = pystray.Menu(
            pystray.MenuItem("Show", on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        )
        self.tray_icon = pystray.Icon("youtube_discord_rpc", _create_tray_image(), APP_NAME, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _on_close(self):
        if self.config.get("minimize_to_tray") and _pystray_available:
            self.root.withdraw()
            self._show_tray()
            self._log("Minimized to system tray")
        else:
            self._quit()

    def _quit(self):
        self.running = False
        self.discord.clear_activity()
        self.discord.close()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()

    # ── Native Messaging ──

    def _native_messaging_loop(self):
        """Listen for messages from the Firefox extension on stdin."""
        while self.running:
            try:
                message = read_native_message()
                if message is None:
                    break

                if message["type"] == "SET_ACTIVITY":
                    activity = message.get("activity", {})
                    discord_activity = {
                        k: activity[k] for k in ("details", "state", "timestamps", "assets", "buttons")
                        if k in activity and activity[k]
                    }

                    title = activity.get("details", "Unknown")
                    channel = activity.get("state", "")
                    self.current_video = title

                    success = self.discord.set_activity(discord_activity)
                    if not success:
                        if self.discord.connect():
                            self.discord.set_activity(discord_activity)
                            self._set_status("connected")
                        else:
                            self._set_status("disconnected")
                            send_native_message({"type": "DISCONNECTED"})
                            continue

                    self._set_status("connected")
                    self._set_now_playing(title, channel)
                    self._log(f"Now playing: {title}")
                    send_native_message({"type": "CONNECTED"})

                elif message["type"] == "CLEAR_ACTIVITY":
                    self.discord.clear_activity()
                    self.current_video = None
                    self._set_now_playing()
                    self._log("Playback stopped")
                    send_native_message({"type": "CONNECTED"})

            except Exception as e:
                self._log(f"Error: {e}")
                try:
                    send_native_message({"type": "ERROR", "error": str(e)})
                except Exception:
                    pass

    # ── Run ──

    def run(self):
        self.root.mainloop()


# ── Entry Point ──────────────────────────────────────────────────────────────


def main():
    app = MainApp()
    app.run()


if __name__ == "__main__":
    main()
