"""Regression test: atmospheric wallpaper must recover after Minimal mode.

Run with the bundled Python/PySide6 from the staged application on Linux:
    cd build/staged/Vitalux-vX.Y.Z
    QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH="$PWD/lib" \
        runtime/bin/python3.12 "$GITHUB_WORKSPACE/tests/test_glass_theme_switch.py"
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from vitalux import theme
from vitalux.glass import AmbientScene


def run():
    app = QApplication.instance() or QApplication([])
    scene = AmbientScene()
    scene.resize(960, 720)
    scene.show()
    app.processEvents()

    def select(mode):
        theme.set_mode(mode)
        scene.set_low_power(mode == "minimal")
        app.processEvents()
        if mode == "minimal":
            assert scene._wallpaper.isNull(), "Minimal mode must release sharp image"
            assert scene._soft_wallpaper.isNull(), "Minimal mode must release blur image"
            assert scene._asset_mode is None, "Released images still marked as loaded"
        else:
            assert not scene.sharp_backdrop().isNull(), f"{mode}: background image missing"
            assert not scene.soft_backdrop().isNull(), f"{mode}: blur image missing"
            assert not scene.grab().isNull(), f"{mode}: failed to paint"
            assert scene._asset_mode == mode, f"Wrong cache: {scene._asset_mode} vs {mode}"

    for sequence in (
        ("glass", "minimal", "glass"),
        ("black_glass", "minimal", "black_glass"),
        ("glass", "minimal", "black_glass", "minimal", "glass"),
        ("glass", "minimal", "glass", "minimal", "glass"),
    ):
        for mode in sequence:
            select(mode)
        scene.resize(scene.width() + 2, scene.height() + 2)
        app.processEvents()
        assert not scene.sharp_backdrop().isNull(), "Wallpaper missing after resizing"
    scene.close()
    print("Theme cache and wallpaper restoration: OK")


if __name__ == "__main__":
    run()
