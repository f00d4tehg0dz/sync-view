# Sync View

A Firefox extension that displays your streaming activity as Discord Rich Presence. Supports YouTube, YouTube Music, Netflix, Spotify, Twitch, Hulu, Disney+, Prime Video, SoundCloud, Crunchyroll, Max, and Apple TV+.

## How It Works

Sync View has three parts:

1. **Firefox Extension** — A content script that detects media playback on supported streaming sites and extracts metadata (title, channel, progress, thumbnail).
2. **host.exe** — A headless native messaging host that Firefox spawns automatically. It receives messages from the extension via stdin/stdout and forwards them to Discord's local IPC pipe.
3. **SyncView.exe** — A desktop GUI companion app for first-time setup, configuration, and monitoring. It registers the native messaging host in the Windows registry and provides a settings panel and activity log.

```
Firefox Extension  --stdin/stdout-->  host.exe  --named pipe-->  Discord
                                                                    |
SyncView.exe (setup/config/monitoring) ----named pipe--->  Discord  |
```

## Prerequisites

- **Windows 10/11**
- **Python 3.8+** with pip (check "Add to PATH" during install)
- **Firefox** (v91+)
- **Discord** desktop app (must be running)

## Building from Source

### 1. Clone the repository

```bash
git clone https://github.com/f00d4tehg0dz/firefox-youtube-discord-richpresence-exentison.git
cd firefox-youtube-discord-richpresence-exentison
```

### 2. Run the build script

```bash
build.bat
```

This will:
- Install Python dependencies (PyInstaller, pystray, Pillow)
- Build `dist/host.exe` (native messaging host)
- Build `dist/SyncView.exe` (desktop GUI app)
- Copy extension files to `dist/extension/`
- Package the extension as `dist/sync-view.xpi`

### 3. Build the installer (optional)

If you have [Inno Setup 6+](https://jrsoftware.org/isinfo.php) installed:

```bash
ISCC.exe installer.iss
```

This creates `installer_output/SyncView-Setup-2.0.0.exe`, a full Windows installer that handles native host registration, startup configuration, and uninstallation.

## Installation & Setup

### Option A: Using the Installer

1. Run `build.bat` to build everything
2. Run `ISCC.exe installer.iss` to create the installer
3. Run the installer — it will register the native host and set up everything automatically
4. Install the Firefox extension (see Step 2 below)

### Option B: Manual Setup

#### Step 1: Register the Native Messaging Host

Run `SyncView.exe` from the `dist/` folder. On first launch, the setup wizard will:
- Create a native messaging manifest JSON file
- Register it in the Windows registry under `HKCU\Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc`
- Configure startup and tray preferences

You can also register manually:

1. Create a file at `%APPDATA%\SyncView\youtube_discord_rpc.json`:

```json
{
  "name": "youtube_discord_rpc",
  "description": "Sync View native messaging host",
  "path": "C:\\path\\to\\dist\\host.exe",
  "type": "stdio",
  "allowed_extensions": ["sync-view@example.com"]
}
```

2. Add a registry key:
   - Key: `HKEY_CURRENT_USER\Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc`
   - Default value: the full path to the JSON manifest file above

#### Step 2: Install the Firefox Extension

**For development/testing (temporary):**

1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`
2. Click **"Load Temporary Add-on..."**
3. Select `dist/extension/manifest.json` (or any file inside the extension folder)
4. The extension will be active until Firefox is restarted

**For permanent local install (unsigned):**

1. Open Firefox and navigate to `about:config`
2. Set `xpinstall.signatures.required` to `false` (only works in Firefox Developer Edition, Nightly, or ESR)
3. Open `about:addons`
4. Click the gear icon and select **"Install Add-on From File..."**
5. Select `dist/sync-view.xpi`

#### Step 3: Verify It Works

1. Make sure **Discord** is running
2. Make sure **SyncView.exe** has been run at least once (to register the native host)
3. Open a supported streaming site in Firefox (e.g., YouTube)
4. Play a video
5. Check your Discord profile — you should see a Rich Presence status with the media details

## Supported Services

| Service | Activity Type | Features |
|---------|--------------|----------|
| YouTube | Watching | Title, channel, progress, thumbnail, watch link |
| YouTube Music | Listening | Title, artist, progress, album art |
| Netflix | Watching | Title, show name, progress |
| Spotify | Listening | Title, artist, progress, album art |
| Twitch | Watching | Stream title, streamer, game, live indicator, watch link |
| Hulu | Watching | Title, show name, progress |
| Disney+ | Watching | Title, show name, progress |
| Prime Video | Watching | Title, show name, progress |
| SoundCloud | Listening | Title, artist, progress, artwork, listen link |
| Crunchyroll | Watching | Title, show name, progress |
| Max | Watching | Title, show name, progress |
| Apple TV+ | Watching | Title, show name, progress |

## Publishing to Firefox Add-ons (AMO)

To publish Sync View as a signed extension on [addons.mozilla.org](https://addons.mozilla.org):

### 1. Create a Mozilla Developer Account

1. Go to [addons.mozilla.org/developers](https://addons.mozilla.org/developers/)
2. Sign in with a Firefox Account (or create one)
3. Agree to the developer terms

### 2. Update the Extension ID

Before submitting, replace the placeholder extension ID in `manifest.json`:

```json
"browser_specific_settings": {
  "gecko": {
    "id": "sync-view@your-domain.com"
  }
}
```

Use an email-style ID you own, or generate a UUID (`{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}`).

**Important:** Also update `allowed_extensions` in the native messaging manifest to match. This is set in `native-host/app.py` (line 281) and `installer.iss` (line 87).

### 3. Package the Extension

Run `build.bat` — it outputs `dist/sync-view.xpi`. Alternatively, manually zip the extension files:

```bash
cd dist/extension
zip -r ../sync-view.xpi *
```

The `.xpi` must contain these files at the root (not inside a subfolder):
- `manifest.json`
- `content.js`
- `background.js`
- `popup/` (popup.html, popup.js, popup.css)
- `icons/` (icon-48.png, icon-96.png)

### 4. Submit to AMO

1. Go to the [AMO submission page](https://addons.mozilla.org/developers/addon/submit/distribution)
2. Choose **"On this site"** for public listing (or **"On your own"** for self-distribution with signing only)
3. Upload `dist/sync-view.xpi`
4. AMO will run automated validation — fix any errors it reports
5. Fill in the listing details:
   - **Name:** Sync View
   - **Summary:** Shows your streaming activity on Discord Rich Presence
   - **Description:** Detailed description of supported services and features
   - **Categories:** Social & Communication
   - **Screenshots:** Add screenshots of the popup UI and Discord Rich Presence output
   - **Privacy policy:** Note that no data is collected — all processing is local via native messaging
6. Submit for review

### 5. AMO Review Notes

Mozilla reviewers will need to know:

- The extension uses the `nativeMessaging` permission to communicate with a local companion app (`host.exe`)
- No data is sent to any remote server — all communication is local (Firefox -> host.exe -> Discord IPC pipe)
- The `tabs` permission is used only to detect which streaming site is active
- Source code is available on GitHub

Typical review takes 1-5 days. You may be asked to provide the native host source code for review — point them to the GitHub repository.

### 6. After Approval

Once approved, users can install directly from AMO. They will still need to:
1. Install the native host (via `SyncView.exe` or the Inno Setup installer)
2. Have Discord running

Consider linking to the installer download from the AMO listing description.

## Discord Application Setup

The extension uses Discord Application ID `1482383187882545233`. If you need to create your own:

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and name it (this name appears in Discord as "Playing **name**")
3. Copy the **Application ID**
4. Update `DISCORD_CLIENT_ID` in both `native-host/host.py` and `native-host/app.py`
5. (Optional) Under **Rich Presence > Art Assets**, upload default images

## Troubleshooting

### Extension says "Disconnected"
- Make sure Discord is running
- Make sure `SyncView.exe` has been run at least once to register the native host
- Click "Reconnect" in the SyncView app
- Check that `host.exe` exists in the same directory as `SyncView.exe`

### No Rich Presence appears on Discord
- Open Discord Settings > Activity Privacy > make sure "Display current activity" is enabled
- Rich Presence is not visible to yourself — ask a friend to check, or use a second Discord account
- The Discord Application ID must have a valid application on the Developer Portal

### Native host not found
- Re-run `SyncView.exe` and go to Settings > "Re-register Native Host"
- Or check the registry key: `HKCU\Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc` should point to a valid JSON manifest
- The JSON manifest's `path` field must point to the actual location of `host.exe`

### Extension doesn't detect media
- Make sure you're on a supported site (see table above)
- The content script needs the page to be fully loaded — wait a few seconds after navigating
- Some sites (Netflix, Disney+, etc.) use DRM-protected players that may limit metadata availability

## Landing Page & Cloudflare Pages

The `site/` directory contains a static landing page for the project. To deploy it:

### Deploy to Cloudflare Pages

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) > Workers & Pages > Create
2. Connect your GitHub repository
3. Configure the build:
   - **Build command:** (leave empty — it's static HTML)
   - **Build output directory:** `site`
4. Deploy

Or deploy manually via Wrangler CLI:

```bash
npx wrangler pages deploy site --project-name=sync-view
```

Your site will be available at `https://sync-view.pages.dev` (or your custom domain).

### Update Notifications

The landing page hosts a `version.json` file that SyncView.exe checks on startup:

```json
{
  "version": "2.0.0",
  "release_url": "https://github.com/f00d4tehg0dz/firefox-youtube-discord-richpresence-exentison/releases/latest",
  "changelog": "Initial release with support for 12 streaming services."
}
```

When you release a new version:

1. Update `APP_VERSION` in `native-host/app.py` and `native-host/host.py`
2. Update `version` in `manifest.json`
3. Update `site/version.json` with the new version number, release URL, and changelog
4. Build and publish the new release
5. Deploy the updated `site/` to Cloudflare Pages

SyncView.exe will show an in-app banner when an update is available, with a "Download" button linking to the release page.

The update check URL defaults to `https://sync-view.pages.dev/version.json`. Change `UPDATE_CHECK_URL` in `native-host/app.py` if your domain differs.

## Project Structure

```
sync-view/
  manifest.json          # Firefox extension manifest
  content.js             # Content script — detects media on streaming sites
  background.js          # Background script — bridges content script to native host
  popup/                 # Extension popup UI
    popup.html
    popup.js
    popup.css
  icons/                 # Extension and app icons
  native-host/
    host.py              # Headless native messaging host (-> host.exe)
    app.py               # Desktop GUI app with setup wizard (-> SyncView.exe)
    requirements.txt     # Python dependencies
  site/                  # Landing page (deploy to Cloudflare Pages)
    index.html
    style.css
    app.js
    version.json         # Version manifest for update checking
  build.bat              # Build script (PyInstaller + extension packaging)
  installer.iss          # Inno Setup installer script
```

## License

MIT
