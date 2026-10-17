# Vitalux: native Qt Quick GPU interface (experimental)

This is a **work in progress**, not the stable Vitalux interface.

## Architecture

- A standalone **QQuickView** is the top-level native window.
- Cards, navigation, animated meter fills, scrolling and chart bars are Qt
  Quick scene-graph nodes, not CPU-painted \`QWidget\` children.
- An independent Qt \`QThread\` polls the **existing** Vitalux sensor collectors
  every second; it never drives the frame rate.
- The prototype currently has Overview, Processor, Graphics, Memory, Network,
  System and Info views. Disk benchmarks, SMART, settings, updates, custom
  wallpapers, advanced sensor pages, language switching and the existing
  full dashboard layout are **not yet ported**.
- Qt chooses rendering through its RHI. OpenGL is the preview's default;
  alternatively \`QSG_RHI_BACKEND=vulkan\` may be tested on supported drivers.
  Neither mode is guaranteed to use a hardware GPU (e.g. Mesa software drivers).

## Running without replacing the stable app

From a developer checkout with \`PySide6\` and \`psutil\` installed:

\`\`\`sh
python3 -m vitalux.gpu_ui
\`\`\`

For an **assembled portable build that includes these experimental files**,
run \`./run.sh --gpu-preview\`. Normal \`./run.sh\` is unchanged.

Do not overlay experimental files onto a stable installation without a
backup. This branch does not publish a ready-made AppImage or release ZIP.

## Technical validation

\`\`\`sh
QT_QPA_PLATFORM=offscreen QSG_RHI_BACKEND=software python3 tests/test_gpu_ui_preview.py
\`\`\`

This smoke test validates the source loading and live-data binding, not
end-user responsiveness, visual parity, real GPU use or specific FPS.
Benchmark realistic systems under KDE Wayland with 60/144/240 Hz monitors
before considering the prototype a replacement.

## Production migration checklist

1. Reproduce existing wallpaper materials, blur and accent variants with no
   visual regressions and without rebuilding textures on every sensor sample.
2. Migrate cards, gauges and all historical charts to Quick scene graph nodes.
3. Port sensors, alerts, disk/SMART benchmarks, settings and update UI.
4. Preserve KDE tray, localization, install/update/rollback and reliability.
5. Compare full GPU pipelines (OpenGL/Vulkan) on actual KDE Wayland machines
   against today's CPU-based interface. Add explicit backend failure fallback.
6. Keep the stable Qt Widgets launcher available until full regression coverage
   and hands-on visual comparison approve an opt-in beta.
