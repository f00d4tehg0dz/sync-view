<p align="center">
  <img src="logo.png" alt="Sync View" width="200">
</p>

<h1 align="center">Sync View</h1>

<p align="center">
  Show what you're streaming as Discord Rich Presence — automatically.
  <br>
  A browser extension + Windows companion app that syncs your media activity to Discord.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/browser-Firefox-FF7139?logo=firefox" alt="Firefox">
  <img src="https://img.shields.io/badge/browser-Chrome-4285F4?logo=googlechrome" alt="Chrome">
  <img src="https://img.shields.io/badge/browser-Edge-0078D7?logo=microsoftedge" alt="Edge">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License">
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
| Plex | Watching/Listening | Title, show/artist, progress, live TV |

## Installation

### Quick Start (Installer)

1. Download **SyncView-Setup-3.1.0.exe** from the [Releases](../../releases) page
2. Run the installer — it will set up the companion app, native messaging host, and registry entries for Firefox, Chrome, and Edge
3. Install the browser extension for your browser (see below)
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

### Installing the Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **"Load unpacked"**
4. Select the `chrome/` folder (or `dist/extension-chrome/` after building)
5. **Copy your extension ID** — it's the long string shown below the extension name (e.g., `knldjmfmopnpolahpmmgbagdohdnhkik`)
6. Open **SyncView.exe** → click the gear icon → **Settings**
7. Paste the extension ID into the **"Chrome / Edge Extension IDs"** field
8. Click **"Save IDs"** — this registers the extension with the native messaging host

> **Important:** Chrome requires the extension ID to be registered in the native messaging manifest. Without step 5-8, you'll see "Specified native messaging host not found" errors.

### Installing the Edge Extension

1. Open Edge and go to `edge://extensions/`
2. Enable **Developer mode** (toggle in the bottom-left)
3. Click **"Load unpacked"**
4. Select the `edge/` folder (or `dist/extension-edge/` after building)
5. **Copy your extension ID** from the extension card
6. Open **SyncView.exe** → Settings → paste the ID into **"Chrome / Edge Extension IDs"**
7. Click **"Save IDs"**

> **Tip:** You can enter multiple extension IDs (comma-separated) if you use both Chrome and Edge.

## How It Works

Sync View has three components:

```
Browser Extension  ──stdin/stdout──▶  syncviewhost.exe  ──named pipe──▶  Discord
                                                                             │
SyncView.exe (setup / config / monitoring) ──named pipe──▶  Discord          │
```

1. **Browser Extension** — A content script that detects media playback on supported sites and extracts metadata (title, artist/channel, progress, thumbnails). Uses the Media Session API where available, with DOM selector fallbacks for reliability. Available as Firefox (MV2) and Chrome/Edge (MV3) variants.

2. **syncviewhost.exe** — A headless native messaging host that the browser launches automatically. It receives messages from the extension via stdin/stdout and forwards them to Discord's local IPC pipe.

3. **SyncView.exe** — A desktop companion app that handles first-time setup, registers the native messaging host in the Windows registry (for Firefox, Chrome, and Edge), and provides a settings panel, activity log, and connection monitoring.

## Configuration

SyncView stores its config at `%APPDATA%\SyncView\config.json`. Available settings (also accessible from the SyncView GUI):

| Setting | Description |
|---------|-------------|
| Start with Windows | Launch SyncView automatically on login |
| Minimize to tray | Minimize to system tray instead of taskbar |
| Start minimized | Launch minimized (useful with startup enabled) |
| Chrome / Edge Extension IDs | Register your Chromium extension IDs for native messaging |

## Requirements

- **Windows 10/11**
- **Firefox** v142+, **Chrome** v130+, or **Microsoft Edge** v130+
- **Discord** desktop app (must be running for Rich Presence)

## Building from Source

### Prerequisites

- Python 3.8+ with pip (ensure "Add to PATH" is checked during install)
- [Inno Setup 6+](https://jrsoftware.org/isinfo.php) (optional, for building the installer)

### Build

```bash
# Run the build script — installs deps, compiles executables, packages extensions
build.bat
```

This produces:
- `dist/SyncView.exe` — GUI companion app
- `dist/syncviewhost.exe` — Native messaging host
- `dist/extension-firefox/` — Firefox extension files
- `dist/sync-view.xpi` — Firefox extension package
- `dist/extension-chrome/` — Chrome extension files
- `dist/sync-view-chrome.zip` — Chrome Web Store upload package
- `dist/extension-edge/` — Edge extension files
- `dist/sync-view-edge.zip` — Edge Add-ons upload package
- `dist/site/` — Landing page (deploy to Cloudflare Pages)

To build the installer:
```bash
# Requires Inno Setup
ISCC.exe installer.iss
# Output: installer_output/SyncView-Setup-3.1.0.exe
```

## Project Structure

```
sync-view/
├── manifest.json            # Firefox extension manifest (MV2)
├── content.js               # Firefox content script
├── background.js            # Firefox background script
├── chrome/                  # Chrome extension (MV3)
│   ├── manifest.json
│   ├── content.js
│   ├── background.js        # Service worker
│   └── popup/popup.js
├── edge/                    # Edge extension (MV3)
│   ├── manifest.json
│   ├── content.js
│   ├── background.js        # Service worker
│   └── popup/popup.js
├── popup/                   # Shared popup UI (HTML + CSS)
├── icons/                   # Extension and app icons
├── native-host/
│   ├── host.py              # Native messaging host → syncviewhost.exe
│   ├── app.py               # Desktop GUI app → SyncView.exe
│   └── requirements.txt     # Python dependencies (pystray, Pillow)
├── site/                    # Landing page (deploy to Cloudflare Pages)
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── version.json         # Version manifest for update checking
├── build.bat                # Build script (PyInstaller + extension packaging)
└── installer.iss            # Inno Setup installer script
```

## Troubleshooting

### Extension popup says "Disconnected"
- Make sure Discord is running
- Run SyncView.exe at least once to register the native host
- Click **Reconnect** in the SyncView app
- Verify `syncviewhost.exe` exists in the same directory as `SyncView.exe`

### Chrome/Edge: "Specified native messaging host not found"
- Open SyncView.exe → Settings
- Paste your extension ID into **"Chrome / Edge Extension IDs"** and click **"Save IDs"**
- Find your extension ID at `chrome://extensions/` or `edge://extensions/` (the long string under the extension name)
- Reload the extension after saving

### Rich Presence doesn't appear on Discord
- Go to Discord Settings → Activity Privacy → enable **"Display current activity as a status message"**
- Rich Presence is **not visible to yourself** — ask a friend to check, or use a second account
- Make sure the media is actually playing (paused content may clear the status)

### Native host not found
- Open SyncView and go to Settings → **"Re-register Native Host"**
- Check the registry key for your browser:
  - **Firefox:** `HKCU\Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc`
  - **Chrome:** `HKCU\Software\Google\Chrome\NativeMessagingHosts\youtube_discord_rpc`
  - **Edge:** `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\youtube_discord_rpc`
- The manifest's `path` field must point to the actual location of `syncviewhost.exe`

### Extension doesn't detect media
- Confirm you're on a supported site (see table above)
- Wait a few seconds after the page loads — the content script runs at `document_idle`
- Some DRM-protected players may limit metadata availability

## License

[AGPL-3.0](LICENSE)
