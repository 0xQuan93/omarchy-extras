# Omarchy Extras

A pick-and-choose collection of desktop tools, shell plugins, and a theme by Quan.
Built on **Omarchy 4.0.2-1 with the Quickshell bar and Lua-based Hyprland configuration**.
This is an independent community project. Older Waybar-based installations are not supported by the installer.

| Component | What you get | Additional requirements |
| --- | --- | --- |
| `dashboard` | Machine stats, weather, news, focus timer, agent launchers, local chat | Python 3, systemd user session; Foot, btop, Codex and Ollama for their respective features |
| `wanderer` | Theme-aware reading room and daily desktop reading card | Dashboard (included automatically), Chromium, Hyprland Lua API |
| `weather` | Compact weather widget using your chosen dashboard city | Dashboard (included automatically) |
| `radio` | SomaFM presets and MPRIS media controls | MPV, mpv-mpris; stock Omarchy media service |
| `toonami` | Toonami Aftermath guide, channel switching, window/tile/mini/fullscreen modes | MPV, Hyprland Lua API, network access |
| `wavewarz` | Public battle feed, coin prices, optional local AI recaps | curl; Ollama for recaps |
| `notifications` | Custom notification service with persistent popup/history handling | Replaces the stock notification service |
| `theme` | Regalia ’89 palette and Signal Field wallpaper | Omarchy theme support |

## Marketplace plugin

The marketplace installs the **Extras bar menu**. It links to setup instructions, the
repository, and your optional local dashboard. It does not install or enable the
collection's components, start services, change your theme, or replace notifications.
Requires Omarchy Quattro/Quickshell and a default browser; no extra packages for the menu.

```bash
omarchy plugin add https://github.com/0xQuan93/omarchy-extras.git --enable
```

Click **Extras** to open the menu. Use Up/Down or Tab to select a link, Enter to
open it, and Escape or an outside click to close. The dashboard link expects you
to install the optional dashboard first. Opening external links uses your default browser.

```bash
omarchy bar move io.github.0xquan93.omarchy-extras --section left
omarchy plugin remove io.github.0xquan93.omarchy-extras
```

Removing this menu leaves separately installed components intact; remove those using
the component instructions below. Component manifests are installer inputs, not
additional plugins automatically enabled by marketplace installation.

## Optional components


Clone this repository, review the source, and preview your chosen components:

```bash
git clone https://github.com/0xQuan93/omarchy-extras.git
cd omarchy-extras
python3 install.py radio toonami theme
```

The default is a **read-only preview**. Install with:

```bash
python3 install.py radio toonami theme --apply
```

Use `all` to select every component, including the replacement notification daemon.
Install only what you want; weather and Wanderer automatically include the dashboard.
The installer checks dependencies but does not install system packages or download models.

Helpers are copied to `$XDG_DATA_HOME/omarchy-extras` (default `~/.local/share/omarchy-extras`).
Plugins go into `$XDG_CONFIG_HOME/omarchy/plugins`. Existing widget entries and unrelated
settings are preserved. Added widgets can coexist with stock widgets; remove the old bar
entry yourself if you prefer just one. Notifications explicitly disables `omarchy.notifications`.
No Hyprland config, gestures, keybindings, or autostart scripts are changed.

Changed files are backed up under `$XDG_STATE_HOME/omarchy-extras/backups/<timestamp>`
(default `~/.local/state/omarchy-extras/backups`). Each backup has a JSON manifest mapping
original paths to saved files; a null backup marks a newly created file. Settings are written
atomically. A service-start failure can leave the files installed: fix the reported problem
and rerun. `--no-start` installs service definitions without starting them.

## Use and customize

- **Dashboard:** open `http://127.0.0.1:8990`. Choose your city in Customize. Weather has no default location. Settings are created in the installed `dashboard/settings.json`; focus notes stay in your browser. Agent buttons use your installed `codex` from PATH and your existing account/config. Local chat needs an existing Ollama service at `127.0.0.1:11434`; the installer does not configure it. The local-agent button expects the `qwen3.5:4b` model. CPU temperature currently recognizes `k10temp`; other machines may show unavailable.
- **Wanderer:** click the desktop card or visit `http://127.0.0.1:8990/wanderer/`. Edit the installed `dashboard/wanderer/readings.json` to choose your own links. Updates preserve that file. The card uses a Hyprland special workspace; no gestures are installed. Its appearance follows your active Omarchy palette.
- **Radio:** click the widget for presets; right-click plays/pauses your active media player. Stop radio affects only its dedicated MPV player. New playback starts at 40% volume, with no login autoplay.
- **Toonami:** click to load the guide, then choose a public station. Window, Tile, Mini and Fullscreen control its dedicated MPV window. Mini has width presets and four corners, with preferences lasting for your login session. Account-only channels open the provider's website. Provider availability and public APIs can change. An included public issuer chain supplements system certificate verification; no private keys are included and TLS verification remains enabled.
- **Wave Desk:** prices refresh every two minutes, battle data every minute. Recaps run on request through local Ollama. Configure optional `WAVE_DESK_HANDLE` and `WAVE_DESK_MODEL` with `systemctl --user edit quan-wavewarz.service`, adding `Environment=WAVE_DESK_HANDLE=yourhandle` under `[Service]`, then restart the service. No wallet connection is used. Desktop cards are positioned for the original layout; adjust margins in the QML for yours.
- **Theme:** run `omarchy theme set regalia-89` after installing `theme`. Installation alone does not change your theme.

The two Python services bind only to loopback (8990 and 8991). They are desktop companions
with local launch actions, not servers to expose to a network. Network feeds and streams
contact their named providers; local AI features contact your local Ollama server.

## Update or remove

Pull changes and rerun the same component command with `--apply`. Your dashboard settings
and reading list are preserved. Helpers are installed copies; moving the clone is fine.

To remove a component, remove its `oxquan.*` entry from `bar.layout` and/or `plugins` in
`~/.config/omarchy/shell.json`. IDs are `oxquan.home`, `oxquan.wanderer`, `oxquan.weather`,
`oxquan.media`, `oxquan.toonami`, `oxquan.wavewarz`, and `oxquan.notifications`.
When removing notifications, also remove `omarchy.notifications` from `disabledPlugins`
so the stock daemon can load again.

Stop backend services when they are no longer needed:

```bash
systemctl --user disable --now quan-dashboard.service
systemctl --user disable --now quan-wavewarz.service
```

Weather and Wanderer need the dashboard service. You may then delete the corresponding
plugin folder, installed helper folder, and user service file, followed by
`systemctl --user daemon-reload`. Stop radio/Toonami playback before deleting their helpers.
Switch to another theme before removing the installed `regalia-89` folder.
Restore individual backed-up files if needed; restoring an entire old shell.json can undo
later unrelated changes. The installer does not delete your notification history.

## Development and validation

```bash
python3 -m unittest discover -s tests -v
(cd dashboard && python3 -m unittest discover -v)
(cd toonami && python3 -m unittest discover -v)
(cd wavewarz && python3 -m unittest discover -v)
node --check dashboard/app.js
node --check dashboard/wanderer/app.js
```

The public package has automated backend and isolated installer checks. Its original
components were used on the author's desktop. The portable package still needs a fresh
Omarchy installation and listening checks; QML uses internal Omarchy APIs that may change.
Please include your Omarchy version, selected components, and relevant errors in bug reports.

## License and credits

MIT for this collection's code and original artwork; see [LICENSE](LICENSE).
Omarchy-derived shell code retains the upstream copyright and MIT license in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Brand names, external publications,
streams, and provider services remain their owners' material. No media content is bundled.
