# Vitalux – Changelog

Every Vitalux release is documented here. The Updates page displays
what has changed before you install a new version and keeps the changelog
of installed and earlier releases available offline.

## [v0.9.3.80] - 2026-10-18
- **Fixed AppImage GPU setup:** Vitalux stages the bundled service installer and engine in a private temporary directory before administrator authorization, avoiding permission errors when root cannot access the AppImage FUSE mount. Temporary files are removed afterward.
- **Protected built-in accent colors:** Red and all other eight fixed colors remain available and cannot be edited or deleted, including after updates. Incorrect legacy custom entries overlapping presets are automatically cleaned up; only user-created colors can be changed.
- Removed the one-time “Vitalux continues in the system tray” popup on window close. Tray functionality, live readings and warning notifications are unchanged.
- Removed obsolete notification state, translations and unused Qt imports. Updated the compact README, bilingual in-app guide, and AppImage/color/tray regression tests.

## [v0.9.3.79] - 2026-10-18
- **GPU tuning now included in Vitalux:** The original LACT 0.10.1 open-source GPU control backend is bundled with the full ZIP and AppImage and SHA-256 verified. No separate LACT desktop application or package installation is needed.
- Automatic GPU detection works even before the privileged tuning service is enabled. Click **Set up GPU tuning** and authorize the one-time setup of **vitalux-gpu.service**.
- Native Vitalux branding throughout Graphics, status messages and setup. Original engine attribution and MIT license remain available in the legal documentation.
- Improved Qt widget signal management, offline detection, and regression tests for setup, hardware discovery and original upstream binary. Administrator approval and supported hardware drivers remain necessary.

## [v0.9.3.78] - 2026-10-18
- **Native GPU tuning in the Graphics tab:** Vitalux-themed frontend communicating with the original local **LACT daemon (lactd)**, while preserving existing live GPU stats.
- Configure supported clock, voltage, power and fan parameters. Unknown LACT configuration fields are preserved and exposed in an advanced JSON editor. Explicit confirmation is required; unconfirmed changes are reverted by LACT.
- Create, activate and delete profiles; auto-switch and process/GameMode rules use LACT's API. Vitalux monitoring remains available when lactd is not installed or accessible.
- Expanded README, bilingual built-in guide, translations, MIT credit and automated LACT/Qt regression checks. Hardware support varies by GPU, drivers and LACT; live hardware verification remains necessary.

## [v0.9.3.77] - 2026-10-18
- Restored the full About-page acknowledgement, with a bold “Thanks to:” heading and clickable TimBooH GitHub profile; it follows the active language and accent color.
- Conservative automatic dashboard tiling fills only large holes after tile moves or hiding, retaining the same 14 px spacing, saved order, undo and drag-and-drop.
- Tidied the affected code, kept the README concise and updated the bilingual in-app guide and regression tests.

## [v0.9.3.76] - 2026-10-18
- Smoother mouse-wheel scrolling with time-based interpolation, automatically following the active monitor's configured refresh rate, including screen and refresh-rate changes. Precision touchpad input remains native and immediate.
- Frame updates run only while actively scrolling; reduced-motion and motion-off settings are respected. This does not change the display mode or guarantee a particular FPS.
- Shortened and enlarged the TimBooH acknowledgement in Info, using the same accent color as “Made by PAAAUUULLOOOH”.
- Updated README and scrolling regression tests.

## [v0.9.3.75] - 2026-10-18
- Added **Qt Quick · GPU test (experimental)** as a third option next to CPU and OpenGL under Settings → Graphics rendering. Restart now applies changes.
- Qt Quick uses the Qt RHI/OpenGL scene graph for the wallpaper texture while CPU-painted widgets, charts and glass cards remain unchanged. This is not a full QML migration or a performance guarantee.
- Bundled required Qt Quick/QML libraries into the portable ZIP and AppImage with automatic CPU fallback. The prior CPU and OpenGL options remain available.
- Added a smaller Info-page credit beneath “Made by PAAAUUULLOOOH”: “Thanks to TimBooH for supporting the integration of custom wallpapers and graphics output (OpenGL/CPU rendering).”
- Updated German/English documentation and renderer regression tests.

## [v0.9.3.74] - 2026-10-18
- Disabled expensive offscreen Qt drop shadows inside scrolling cards while retaining frosted glass surfaces and borders, reducing repaint overhead in both CPU and OpenGL modes.
- Decode imported wallpapers at a bounded target size and reuse cached images; all five placement modes remain available.
- Restored the original single **Accent color** chooser with presets and custom colors, plus one **Automatically match background** entry. Removed extra tabs and numbered swatches; prior numbered settings migrate to automatic matching.
- Improved layout of accent and wallpaper controls for narrow windows and KDE fractional scaling.
- Added **Restart now** when switching CPU/OpenGL; the existing launcher performs a graceful full-process restart after threads shut down. Active benchmarks can prevent restart.
- Updated German/English documentation and regression tests; previous releases stay available for rollback.

## [v0.9.3.73] - 2026-10-17
- Added an experimental, opt-in OpenGL/GPU background renderer and GPU-based composition for the main Qt window. Standard Qt widgets and charts still render on the CPU; improvements are not guaranteed.
- Settings → Graphics rendering lets you choose CPU (stable default) or OpenGL (experimental), taking effect after restart without touching other preferences.
- Context availability is checked before startup and automatically falls back to CPU when unavailable. A crash during GPU startup is detected on the next launch and switches back to CPU; `VITALUX_RENDERER=software` also provides an immediate override.
- The previous release remains untouched for rollback. README, bilingual help and regression coverage updated.

## [v0.9.3.72] - 2026-10-17
- Added two accent-color tabs in Settings: Manual Accent Colors (existing colors, edit and delete preserved) and Match Background (five suggested accent colors sampled from the active wallpaper).
- The Match Automatically mode updates accent colors when the user changes a built-in background or personal image. Explicitly selected wallpaper swatches also track the active wallpaper.
- Local, low-resolution color sampling avoids feedback loops with the Adaptive Accent Color background and adds no external dependency.
- Styled tabs for all five Vitalux themes and updated README, bilingual guidance and regression tests. The existing 630 fixed-preset combinations remain unchanged.

## [v0.9.3.71] - 2026-10-17
- Restored KDE tray hover CPU, GPU, RAM and available temperature metrics using real live readings.
- Added an optional compact live popup through the tray context menu; the native KDE tooltip serves the Wayland hover.
- Added import, selection, and removal of PNG/JPEG/WebP/BMP pictures without deleting the originals.
- Added fill, fit, stretch, center and tile placement with preview.
- Updated translations and help while preserving 630 built-in combinations.

## [v0.9.3.70] - 2026-10-17
- Unified four log files: `vitalux.log`, `errors.log`, `installation.log` and `restart.log` now include local ISO timestamps with timezone and the relevant Vitalux version. Native crash frames have timestamped start and crash-end markers.
- Removed the Northern Lights, Night Waves and Violet Mist animations, palettes and rendering branches. Sparkle is the only remaining animated wallpaper.
- Removed Pearl and Ice Blue static wallpapers and palettes. Previously saved removed backgrounds fall back to the active theme's default.
- Updated GitHub README and bilingual in-app help with 5 themes × 14 wallpaper choices × 9 accent options = **630 selection combinations** (560 with fixed color presets); custom accents are additional.
- Updated regression tests for selections, logging, versions and rollback.

## [v0.9.3.69] - 2026-10-17
- Improved crash diagnostics: each application, Python and Qt console line in `vitalux.log` now carries local ISO-8601 time and timezone. Startup includes the version and launch process ID; exit includes the actual process status, preserved across the logging pipe.
- `errors.log` writes a timestamped version and start marker before enabling native fatal stack traces, making it easier to distinguish historical errors from new crashes.
- Added crash logger regressions covering simulated native malloc errors, exit status 134, recovery notifications and startup markers.
- The user's historical `json` NameError came from Vitalux 0.9.3.23; current sources already include that import. The separate native heap corruption still requires contemporary crash evidence for root-cause identification.

## [v0.9.3.68] - 2026-10-17
- Removed Rainbow Pastel and the animated Rainbow, Color Fade and Light backgrounds, along with their obsolete palettes and render effects.
- Preserved the existing animated Sparkle design.
- Added three subtle, automatically animated wallpapers around the original Glass brightness: Northern Lights (deep teal/blue/violet), Night Waves (muted ocean blue) and Violet Mist (dark blue-violet).
- Removed outdated selections from the dropdown and translations; saved references to deleted styles fall back to the active theme's default background.
- Updated regressions for available styles, animation, low-luminance palette checks, README and the bilingual built-in guide.

## [v0.9.3.67] - 2026-10-17
- Removed the global “Gently animate background” option and its rendering/settings implementation; static backgrounds stay static.
- Added four intrinsically animated wallpapers: Rainbow, Color Fade, Sparkle and Light. Light palettes retain their intended brightness regardless of UI scheme, and Adaptive Accent Color returns.
- Completely removed color-intensity and background-softness sliders, related stored preferences, rendering controls and the dedicated slider module; wallpaper colors and softness are now tuned per preset.
- Restored the permanently left-aligned sidebar; right-side docking, drag handle and mirrored controls have been removed with their unused source modules.
- Added yellow and red accent presets with matching Vitalux SVG icons and wordmarks; improved icon updates in the app, tray and user-installed KDE launcher.
- Increased update icon glow visibility in the tray. Pop-up buttons now respect Vitalux’s selected language rather than depending on Qt system catalog availability.
- Updated compact README, bilingual built-in guide, changelogs and regression tests.

## [v0.9.3.66] - 2026-10-17
- The sidebar can now be docked left or right using a draggable dotted grip; clicking the grip toggles sides. Dock position persists, and the collapse arrow, seam and dashboard layout arrow mirror their positions.
- Fixed the dashboard layout editor arrow remaining highlighted after closing; the action strip now opens toward the available screen area.
- Balanced the frosted sidebar contrast and brightness with surrounding cards while preserving the familiar glass design.
- Improved all optional background animations with more noticeable, palette-matched lighting; Minimal also supports an inexpensive monochrome shimmer when explicitly enabled. Animation remains off by default.
- New installation defaults: Glass theme, Vitalux Blue accent and matching Glass wallpaper. Existing preferences are preserved.
- All six predefined accent colors now recolor Vitalux's window, app and tray icons. User-installed desktop menu icons update too, subject to KDE icon caching. Update glow matches the selected color.
- Updated the README, bilingual in-app guide and visual regressions.

## [v0.9.3.65] - 2026-10-17
- The Vitalux system tray icon now glows and breathes when an update is available, returning to the normal icon afterwards. The in-app logo has a brighter accent-coordinated halo; Updates navigation and the one-time tray notification remain intact.
- Restored the original frosted sidebar with its illuminated seam. For non-default background palettes, frost intensity adjusts modestly while original color schemes retain their familiar look.
- Replaced all former additional backgrounds with nine coordinated options: Light (Pearl, Daybreak, Ice Blue), Rainbow (Pastel, Prism), Dark (Deep Ocean, Midnight, Velvet, Graphite). The five original color-scheme backgrounds remain.
- The new gradients subtly echo the accent color and support intensity, softness and optional animation. Removed saved presets automatically fall back to the current theme's original background.
- Updated the compact GitHub README and bilingual built-in guide, and extended regression coverage for wallpapers and animated tray icons.

## [v0.9.3.64] - 2026-10-17
- Composed one shared background for the canvas, sidebar and frosted cards, removing the separate dark sidebar tint and harmonizing Light.
- Refined color palettes and optional, smoothly moving ambient gradients for Aurora Glass, Nebula Purple, Obsidian Black, Arctic Frost and Adaptive.
- The intensity setting now changes every stock background, including Dark, Light, Glass, Black Glass and the monochrome Minimal.
- Both background sliders now use fully custom Qt rendering with visible accent gradients and tactile handles.
- SMART scans start automatically when opening Drives, with drive selection visible immediately and a manual rescan button available.
- Extended regressions and updated README and built-in instructions.

## [v0.9.3.63] - 2026-10-17
- Restored the original background designs with the same names as their schemes: Dark, Light, Glass, Black Glass and Minimal. Automatic (color scheme) follows the active scheme.
- Harmonized the sidebar with additional backgrounds without altering the familiar original glass appearance. Refined Aurora Glass, Obsidian Black, Nebula Purple and Arctic Frost using softer color washes and understated satin ribbons.
- Refined background sliders with accent gradients, subtle handles, consistently aligned percentage values and more legible hover states.
- Available updates now trigger a gentle pulse in the Updates navigation row and Vitalux logo. The available version is visible in the sidebar. A single tray notification per version and a tray-menu shortcut open Updates.
- The app still checks automatically at startup and roughly every six hours. Installing updates always requires confirmation.
- Updated README, bilingual translations, built-in guide and regression tests.

## [v0.9.3.62] - 2026-10-17
- Removed transient mouse-hover text popups across Vitalux while preserving normal hover highlights, including the sidebar.
- Added native Aurora Glass, Obsidian Black, Nebula Purple, Arctic Frost, Adaptive and Classic background styles independently of the selected color scheme; Minimal stays flat.
- Added background color intensity, softness, and optional subtle animation. Adaptive follows the chosen accent color; animation is disabled by default.
- Rendered atmospheric graphics locally using cached Qt painting; no browser or downloadable assets required.
- Updated settings, English translations, the built-in guide, and a shorter, more professional GitHub README.
- Extended visual regression tests for backdrops, theme switching, Minimal and disabled tooltip popups.

## [v0.9.3.61] - 2026-10-17
- Left-aligned hardware warning numbers, preserved readable units, and made wheel changes require input focus.
- Preserved the dark right-hand drop-down area without an arrow; list width now adapts to full labels and entries have tooltips.
- Improved sizing for fractionally scaled KDE desktops and stopped repainting hidden pages unnecessarily.
- SMART health scans now run only on explicit button requests.
- Multi-GPU temperature warnings use the hottest readable GPU; invalid sensor numbers are ignored.
- Cached preferences are written atomically and write failures are reported.
- CI runs its tests even for existing releases and delta archives now target the preceding published version.
- Extended regression tests for threshold controls, preferences, alerts, and drop-downs.

## [v0.9.3.60] - 2026-10-17
- Fixed invisible hardware warning thresholds: the clipped native QSpinBox editor is replaced by a separately laid out number input and visible unit for reliable rendering on KDE/Wayland.
- Thresholds stay editable with arrow keys, mouse wheel, range validation, and persisted settings.
- Preserved compact widths and column alignment and expanded visual and editing regression tests.

## [v0.9.3.59] - 2026-10-17
- Reverted the problematic recent drop-down styling and restored the previous controls with a darker selection area on the right.
- Restored readable selection text, including full version numbers in the changelog drop-down.
- Hardware-warning fields display their values and units again, with consistent alignment.
- Updated graphical tests for the restored controls.

## [v0.9.3.58] - 2026-10-17
- All warning-value controls now line up in one common column regardless of label length.
- Narrower warning values without up/down buttons; keyboard, arrow-key and mouse-wheel input remain available.
- More compact drop-downs with no arrows or separate arrow compartments.
- Closed drop-down fields are painted in the active Vitalux theme, independent of the host KDE/Qt style.
- Popup lists, borders and scroll areas explicitly use their current theme's background and text colors.
- Updated tests and README.

## [v0.9.3.57] - 2026-10-17
- Slightly narrower drop-downs with matching custom chevrons for each color scheme.
- Theme-matched popup lists without native black menu strips above and below the items.
- CPU, GPU, RAM and system drive thresholds now sit uniformly right next to their labels.
- Reordered custom accent actions: Edit, Delete, Custom color.
- Updated settings tests and README.

## [v0.9.3.56] - 2026-10-17
- Saved custom accent colors now support editing both the name and color value through a new Edit button, without creating duplicate entries.
- A separate Delete button appears alongside Edit only when a saved custom color is selected.
- All drop-down selectors now match Dark, Light, Glass, Black Glass and Minimalist themes, including the SMART drive selector, with a very small width reduction.
- Temperature and usage alert input fields now follow their labels on the right, retaining compact centered values.
- The update changelog displays only the selected UI language, either German or English.
- Updated the integrated tutorial and GitHub README to cover the improved controls.

## [v0.9.3.55] - 2026-10-17
- Redesigned the drop-down menus with consistent themed popup backgrounds, removing unwanted dark bands at their top and bottom.
- Moved the compact, center-aligned temperature and usage alert fields to the left of their labels, without changing the card size.
- Added fully translated English changelogs for installed versions and upcoming updates; switching between German and English refreshes both.
- Updated the in-app guide and README with relevant display, alert, accent-color, and changelog improvements.

## [v0.9.3.54] - 2026-10-17
- Unified the checkbox appearance with visible check marks across charts, settings, and benchmarks.
- Made alert threshold input fields narrower, with centered values and unchanged card dimensions.
- Custom accent colors can be named, saved, and removed using the X next to the color selector.
- Added a changelog to Vitalux: view upcoming changes before updating and browse version history afterwards.
- GitHub releases now automatically use the changes listed in the changelog.

## [v0.9.3.53] - 2026-10-17
- Improved the automatic restoration of the previous AppImage on the first restart after an update.
- Verified recovery for restarts originating from older Vitalux versions.

## [v0.9.3.52] - 2026-10-17
- Removed problematic explicit mouse grabs in the Wayland layout editor and improved crash diagnostics.
- Added individually designed SVG artwork in the six preset accent colors; the original logo remains for distribution and custom colors.
- Added recovery of the immediately preceding version, with AppImage and ZIP tests.

## [v0.9.3.51] - 2026-10-17
- The distribution logo can now be hidden independently using an X in the layout editor and restored with "Add tiles".
- Added Save, Discard, and Undo for distribution-logo visibility.
- Added initial theme-based recoloring of the Vitalux symbol and wordmark, later replaced with individually designed SVG color variants.
