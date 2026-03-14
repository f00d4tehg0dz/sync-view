<p align="center">
  <img src="logo.png" alt="Sync View" width="200">
</p>

<h1 align="center">Sync View</h1>

<p align="center">
  Show what you're streaming as Discord Rich Presence — automatically.
  <br>
  A Firefox extension + Windows companion app that syncs your media activity to Discord.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/browser-Firefox-FF7139?logo=firefox" alt="Firefox">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## What It Does

Play a video on YouTube, a song on Spotify, or a show on Netflix — Sync View detects it and updates your Discord profile in real time with the title, progress, artwork, and a link to what you're watching or listening to.

### Supported Services

| Service | Type | Details |
|---------|------|---------|
| YouTube | Watching | Title, channel, progress, thumbnail, watch link |
| YouTube Music | Listening | Title, artist, progress, album art |
| Netflix | Watching | Title, show name, progress |
| Spotify | Listening | Title, artist, progress, album art |
| Twitch | Watching | Stream title, streamer, game, LIVE indicator, watch link |
| Hulu | Watching | Title, show name, progress |
| Disney+ | Watching | Title, show name, progress |
| Prime Video | Watching | Title, show name, progress |
| SoundCloud | Listening | Title, artist, progress, artwork, listen link |
| Crunchyroll | Watching | Title, show name, progress |
| Max | Watching | Title, show name, progress |
| Apple TV+ | Watching | Title, show name, progress |

## Installation

### Quick Start (Installer)

1. Download **SyncView-Setup-3.0.0.exe** from the [Releases](../../releases) page
2. Run the installer — it will set up the companion app, native messaging host, and registry entries
3. Install the Firefox extension from the `extension` folder included in the install directory (see [Installing the Extension](#installing-the-firefox-extension) below)
4. Make sure **Discord** is running
5. Play something on a supported site — your Discord status updates automatically

### Installing the Firefox Extension

**From file (recommended):**

1. Open Firefox and go to `about:addons`
2. Click the gear icon and select **"Install Add-on From File..."**
3. Select the `sync-view.xpi` file from the install directory

> **Note:** Installing unsigned extensions requires Firefox Developer Edition, Nightly, or ESR with `xpinstall.signatures.required` set to `false` in `about:config`.

**For development (temporary):**

1. Open Firefox and go to `about:debugging#/runtime/this-firefox`
2. Click **"Load Temporary Add-on..."**
3. Select `manifest.json` from the project root
4. The extension stays active until Firefox restarts

## How It Works

Sync View has three components:

```
Firefox Extension  ──stdin/stdout──▶  host.exe  ──named pipe──▶  Discord
                                                                    │
SyncView.exe (setup / config / monitoring) ──named pipe──▶  Discord │
```

1. **Firefox Extension** — A content script that detects media playback on supported sites and extracts metadata (title, artist/channel, progress, thumbnails). Uses the Media Session API where available, with DOM selector fallbacks for reliability.

2. **host.exe** — A headless native messaging host that Firefox launches automatically. It receives messages from the extension via stdin/stdout and forwards them to Discord's local IPC pipe.

3. **SyncView.exe** — A desktop companion app that handles first-time setup, registers the native messaging host in the Windows registry, and provides a settings panel, activity log, and connection monitoring.

## Configuration

SyncView stores its config at `%APPDATA%\SyncView\config.json`. Available settings (also accessible from the SyncView GUI):

| Setting | Description |
|---------|-------------|
| Start with Windows | Launch SyncView automatically on login |
| Minimize to tray | Minimize to system tray instead of taskbar |
| Start minimized | Launch minimized (useful with startup enabled) |

## Requirements

- **Windows 10/11**
- **Firefox** v91+
- **Discord** desktop app (must be running for Rich Presence)

## Building from Source

### Prerequisites

- Python 3.8+ with pip (ensure "Add to PATH" is checked during install)
- [Inno Setup 6+](https://jrsoftware.org/isinfo.php) (optional, for building the installer)

### Build

```bash
# Run the build script — installs deps, compiles executables, packages the extension
build.bat
```

This produces:
- `dist/SyncView.exe` — GUI companion app
- `dist/host.exe` — Native messaging host
- `dist/extension/` — Packaged Firefox extension files

To build the installer:
```bash
# Requires Inno Setup
ISCC.exe installer.iss
# Output: installer_output/SyncView-Setup-3.0.0.exe
```

## Project Structure

```
sync-view/
├── manifest.json            # Firefox extension manifest (v2)
├── content.js               # Content script — detects media on streaming sites
├── background.js            # Background script — bridges content script ↔ native host
├── popup/                   # Extension popup UI (status, now playing)
├── icons/                   # Extension and app icons
├── native-host/
│   ├── host.py              # Native messaging host → host.exe
│   ├── app.py               # Desktop GUI app → SyncView.exe
│   └── requirements.txt     # Python dependencies (pystray, Pillow)
├── build.bat                # Build script (PyInstaller + extension packaging)
└── installer.iss            # Inno Setup installer script
```

## Troubleshooting

### Extension popup says "Disconnected"
- Make sure Discord is running
- Run SyncView.exe at least once to register the native host
- Click **Reconnect** in the SyncView app
- Verify `host.exe` exists in the same directory as `SyncView.exe`

### Rich Presence doesn't appear on Discord
- Go to Discord Settings → Activity Privacy → enable **"Display current activity as a status message"**
- Rich Presence is **not visible to yourself** — ask a friend to check, or use a second account
- Make sure the media is actually playing (paused content may clear the status)

### Native host not found
- Open SyncView and go to Settings → **"Re-register Native Host"**
- Or verify the registry key: `HKCU\Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc` points to a valid JSON manifest
- The manifest's `path` field must point to the actual location of `host.exe`

### Extension doesn't detect media
- Confirm you're on a supported site (see table above)
- Wait a few seconds after the page loads — the content script runs at `document_idle`
- Some DRM-protected players may limit metadata availability

## License

[MIT](LICENSE)
