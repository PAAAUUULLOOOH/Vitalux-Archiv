from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal, QVariantAnimation, QEasingCurve, QPoint, QRect, QEventLoop
from PySide6.QtGui import QRegion, QAction
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QSystemTrayIcon, QGraphicsDropShadowEffect, QMenu)
from .ui_locale import QPushButton, retranslate_widgets

from . import APP_NAME, __version__, i18n, sensors, settings, theme, motion
from .i18n import tr
from .pages import CpuPage, DiskPage, GpuPage, MemoryPage, NetworkPage, OverviewPage, SystemPage
from .pages_extra import InfoPage, UpdatePage
from .control import SensorsPage, PreferencesPage
from .brand import PulseCore, TrayPulse, app_icon, sync_installed_icon, wordmark_pixmap
from .widgets import NavButton, SidebarToggle, ChartPanel, Gauge, label
from .glass import AmbientScene, GlassSidebar, GlassSurface, create_ambient_scene
from .sidebar_transition import SidebarTransition, SidebarFreeze
from .smooth_scroll import AdaptiveScrollArea
from .alerts import AlertMonitor, readings_from_sample
from .tray_preview import TrayPreview, tray_tooltip
from .wallpaper_accents import resolve_accent
from .monitor_insights import SessionExtrema
from .insight_engine import MonitoringLab
from .diagnostics import log_exception


class Sampler(QThread):
    sample = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.interval = int(settings.get('interval', 1) or 1)
        self._last_error = None

    def run(self):
        while not self.isInterruptionRequested():
            try:
                self.sample.emit(sensors.collect())
                self._last_error = None
            except Exception as exc:
                # Retain one timestamped, versioned traceback per distinct
                # failure instead of flooding logs at one-second intervals.
                error = (type(exc), str(exc))
                if error != self._last_error:
                    log_exception(type(exc), exc, exc.__traceback__)
                    self._last_error = error
            self.msleep(max(1, self.interval) * 1000)


class MainWindow(QMainWindow):
    def __init__(self, distro, logo, manager):
        super().__init__()
        # Never request per-pixel transparency of the native window.
        # Frosted materials are drawn inside Vitalux;
        # the entire application canvas remains fully opaque.
        self.setAutoFillBackground(True)
        self.distro, self.logo, self.manager = distro, logo, manager
        self.setWindowTitle(APP_NAME)
        # Accommodate KDE fractional scaling and smaller logical desktops.
        self.setMinimumSize(800, 560)
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry().size()
            self.resize(max(800, min(1380, available.width() - 32)),
                        max(560, min(900, available.height() - 32)))
        else:
            self.resize(1380, 900)
        self.hist = {k: deque(maxlen=900) for k in (
            "cpu", "ram", "gpu", "vram", "net_down", "net_up", "io_read", "io_write",
            "cpu_temp", "gpu_temp", "gpu_clock", "gpu_power")}
        self._extrema = SessionExtrema()
        self.lab = MonitoringLab(snapshot_path=Path(settings.PATH).with_name("insights-snapshots.json"))
        self._focus_window = None
        self.last_sample = None
        self.pages = []
        self.update_btn = None
        self._sidebar_collapsed = bool(settings.get('sidebar_collapsed', False))
        self._sidebar_progress = 1.0 if self._sidebar_collapsed else 0.0
        self._sidebar_motion = None
        self._sidebar_overlay = None
        self._alerts = AlertMonitor()
        self._force_quit = False
        self.restart_requested = False
        self._update_notice_queued = False
        self._notified_update_version = str(settings.get('last_notified_update_version', ''))
        self._tray_was_maximized = False
        self.last_render_ms = None
        self._last_refresh_error = None
        # Create the tray icon even when Plasma's StatusNotifier host comes up
        # after Vitalux. Qt automatically registers a visible icon when a host
        # becomes available. Checking isSystemTrayAvailable() here loses that.
        self._tray = QSystemTrayIcon(app_icon(), self)
        self._tray.setToolTip(tray_tooltip(None))
        self._tray_glow = TrayPulse(self._tray, self)
        self._tray_menu = QMenu(self)
        self._tray_open_action = QAction(tr('Vitalux öffnen'), self._tray_menu)
        self._tray_preview = TrayPreview()
        self._tray_preview_action = QAction(tr('Live-Vorschau anzeigen'), self._tray_menu)
        self._tray_preview_action.triggered.connect(self.show_tray_preview)
        self._tray_quit_action = QAction(tr('Beenden'), self._tray_menu)
        self._tray_open_action.triggered.connect(self.show_from_tray)
        self._tray_quit_action.triggered.connect(self.quit_from_tray)
        self._tray_menu.addAction(self._tray_open_action)
        self._tray_menu.addAction(self._tray_preview_action)
        self._tray_update_action = QAction('', self._tray_menu)
        self._tray_update_action.setVisible(False)
        self._tray_update_action.triggered.connect(self._open_updates_from_tray)
        self._tray_menu.addAction(self._tray_update_action)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(self._tray_quit_action)
        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        # A single click normally produces Trigger. A double click may first
        # produce Trigger, so debounce it to avoid hiding an opened window.
        self._tray_click_timer = QTimer(self)
        self._tray_click_timer.setSingleShot(True)
        self._tray_click_timer.setInterval(190)
        self._tray_click_timer.timeout.connect(self._toggle_tray_window)
        self._tray.show()
        manager.changed.connect(self._sync_glow)
        manager.restart.connect(self.quit_from_tray)
        self._build(0)

        self.sampler = Sampler(self)
        self.sampler.sample.connect(self.on_sample)
        self.sampler.start()

    def _build(self, index):
        # A disk benchmark must not outlive its QWidget when changing the UI theme/language.
        for _name, old_page in self.pages:
            if isinstance(old_page, DiskPage):
                if not old_page.benchmark.stop_and_wait():
                    return  # Never destroy a running QThread.
        distro, logo = self.distro, self.logo
        root = create_ambient_scene()
        self.render_backend_active = root.render_backend
        outer = QHBoxLayout(root)
        self._outer_layout = outer
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = GlassSidebar()
        self.sidebar = side
        side.setFixedWidth(250)
        sl = QVBoxLayout(side)
        self.sidebar_layout = sl
        sl.setContentsMargins(16, 21, 16, 16)
        sl.setSpacing(4)
        # One brand block: its internal spacings vanish completely in icon mode.
        brand = QWidget(side)
        brand.setObjectName('sidebarBrand')
        brand_lay = QVBoxLayout(brand)
        brand_lay.setContentsMargins(0, 0, 0, 0)
        brand_lay.setSpacing(4)
        self.sidebar_brand = brand
        self.pulse_core = PulseCore(size=132, parent=brand)
        brand_lay.addWidget(self.pulse_core, 0, Qt.AlignHCenter)
        brand_lay.addSpacing(4)
        mark = label(align=Qt.AlignHCenter)
        mark.setObjectName('wordmarkWrap')
        mark.setFixedSize(200, 42)
        mark.setPixmap(wordmark_pixmap(200, 42))
        self.brand_mark = mark
        brand_lay.addWidget(mark, 0, Qt.AlignHCenter)
        brand_lay.addSpacing(7)
        self.sidebar_distro = label(distro['short'], 'sidebarDistro', Qt.AlignHCenter, wrap=True)
        brand_lay.addWidget(self.sidebar_distro)
        brand_lay.addSpacing(15)
        sl.addWidget(brand)

        self.stack = QStackedWidget()
        self.pages = [
            ("Übersicht", OverviewPage(distro, logo)),
            ("Prozessor", CpuPage()),
            ("Grafik", GpuPage(self.lab, self.open_focus_window)),
            ("Arbeitsspeicher", MemoryPage()),
            ("Netzwerk", NetworkPage()),
            ("Laufwerke", DiskPage()),
            ("Sensoren", SensorsPage()),
            ("System", SystemPage(distro)),
            ("Einstellungen", PreferencesPage(self)),
            ("Updates", UpdatePage(self.manager)),
            ("Info", InfoPage(distro)),
        ]
        # Keep the branding and language switch fixed, while the full glass
        # category list can scroll on shorter screens (e.g. 760px).
        nav_host = QWidget()
        self.nav_host = nav_host
        nav_host.setObjectName('glassNavRail')
        nav_host.setAutoFillBackground(False)
        nav_layout = QVBoxLayout(nav_host)
        nav_layout.setContentsMargins(1, 2, 3, 2)
        nav_layout.setSpacing(5)
        nav_scroll = AdaptiveScrollArea()
        self.nav_scroll = nav_scroll
        nav_scroll.setObjectName('glassScroll')
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setAutoFillBackground(False)
        nav_scroll.viewport().setAutoFillBackground(False)
        nav_scroll.setWidget(nav_host)

        group = QButtonGroup(side)
        self.nav_buttons = []
        glyph = {"Übersicht":"◈", "Prozessor":"◉", "Grafik":"▣", "Arbeitsspeicher":"▤",
                 "Netzwerk":"◎", "Laufwerke":"▱", "Sensoren":"♨", "System":"⚙",
                 "Einstellungen":"≡", "Updates":"↻", "Info":"ⓘ"}
        for i, (name, page) in enumerate(self.pages):
            if name == "Updates":
                nav_layout.addSpacing(8)
            btn = NavButton(glyph.get(name, '•') + '    ' + tr(name))
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            group.addButton(btn, i)
            self.nav_buttons.append(btn)
            nav_layout.addWidget(btn)
            if name == "Updates":
                self.update_btn = btn
            scroll = AdaptiveScrollArea()
            scroll.setObjectName('glassScroll')
            scroll.setWidgetResizable(True)
            scroll.setAutoFillBackground(False)
            scroll.viewport().setAutoFillBackground(False)
            page.setAutoFillBackground(False)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)
        group.idClicked.connect(self._switch_page)
        group.button(index).setChecked(True)
        self.stack.setCurrentIndex(index)

        nav_layout.addStretch(1)
        sl.addWidget(nav_scroll, 1)
        # Border-docked arrow replaces the full-width "Einklappen" button.
        self.collapse_button = SidebarToggle(side)
        self.collapse_button.clicked.connect(self.toggle_sidebar)
        side.set_toggle_button(self.collapse_button)
        sl.addSpacing(8)
        lang_host = QWidget(side)
        self.lang_host = lang_host
        langs = QHBoxLayout(lang_host)
        langs.setContentsMargins(0, 0, 0, 0)
        langs.setSpacing(6)
        langs.addStretch(1)
        for code in ("de", "en"):
            b = QPushButton(code.upper())
            b.setObjectName("langBtn")
            b.setCheckable(True)
            b.setChecked(i18n.lang() == code)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=code: self.set_language(c))
            langs.addWidget(b)
        langs.addStretch(1)
        self.lang_buttons = langs
        sl.addWidget(lang_host)
        sl.addSpacing(6)
        self.sidebar_version = label(f"{APP_NAME}  ·  {__version__}", 'sidebarVersion', Qt.AlignHCenter)
        sl.addWidget(self.sidebar_version)

        outer.addWidget(side)
        outer.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self._optimize_scroll_surfaces()
        self._apply_sidebar_state()
        self._setup_sidebar_motion()
        self._sync_glow()
        # Apply the lightweight renderer even when Minimalistisch is saved
        # before the application launches, rather than only on theme switches.
        if theme.mode() == "minimal":
            self.apply_appearance()

    def _switch_page(self, index):
        # Leaving edit mode commits the layout; neither the editor nor its
        # unsaved arrangement is silently destroyed on navigation.
        overview = self.pages[0][1]
        if index != 0 and hasattr(overview, 'board') and overview.board.editing:
            overview.save_editor()
        self.stack.setCurrentIndex(index)
        # Start the read-only SMART scan on first entry, after the device
        # selectors are visible. Subsequent visits keep the last results;
        # users can still rescan using the button.
        page_name, page_widget = self.pages[index]
        if (page_name == 'Laufwerke' and not page_widget._smart_loaded
                and (page_widget._smart_worker is None or
                     not page_widget._smart_worker.isRunning())):
            QTimer.singleShot(0, page_widget.request_smart)
        # Keep sampling while refreshing only the visible page.
        self._refresh_visible_page()

    def set_language(self, code):
        """Translate widgets in place; never rebuild a running benchmark/page."""
        if code == i18n.lang():
            return
        # All source strings are tracked by our Qt widget wrappers.
        scrolls = [(scroll,scroll.verticalScrollBar().value())
                   for scroll in self.findChildren(QScrollArea)]
        i18n.set_lang(code)
        settings.set('lang',code)
        self._tray_open_action.setText(tr('Vitalux öffnen'))
        self._tray_quit_action.setText(tr('Beenden'))
        self._tray_preview_action.setText(tr('Live-Vorschau anzeigen'))
        self._tray_preview.retheme()
        self._tray.setToolTip(tray_tooltip(self.last_sample))
        retranslate_widgets(self.centralWidget())
        if self._focus_window is not None:
            self._focus_window.retranslate()
            retranslate_widgets(self._focus_window)
        glyph = {"Übersicht":"◈", "Prozessor":"◉", "Grafik":"▣", "Arbeitsspeicher":"▤",
                 "Netzwerk":"◎", "Laufwerke":"▱", "Sensoren":"♨", "System":"⚙",
                 "Einstellungen":"≡", "Updates":"↻", "Info":"ⓘ"}
        for btn, (name, _) in zip(self.nav_buttons,self.pages):
            btn.setText(glyph.get(name,'•') + '    ' + tr(name))
            btn.setToolTip('')
            btn.update()
        for btn in self.lang_host.findChildren(QPushButton):
            btn.setChecked(btn.text().lower() == code)
        if hasattr(self.pages[0][1], 'retranslate'):
            self.pages[0][1].retranslate()
        disk = next((p for name, p in self.pages if name == 'Laufwerke'), None)
        if disk is not None and hasattr(disk, 'retranslate'):
            disk.retranslate()
        if len(self.pages)>8 and hasattr(self.pages[8][1],'refresh_appearance'):
            self.pages[8][1].refresh_appearance()
        self._sync_glow()
        # Layout reflow may happen when labels grow in English.
        QTimer.singleShot(0,lambda: [scroll.verticalScrollBar().setValue(value)
                                    for scroll,value in scrolls])

    def _sync_glow(self):
        on = self.manager.available and bool(self.manager.latest)
        version = self.manager.latest if on else ''
        if self.update_btn is not None:
            self.update_btn.set_glow(on)
            self.update_btn.set_update_version('v' + version if on else '')
            # No hover hints: the version is directly visible in the sidebar.
            self.update_btn.setToolTip('')
        if hasattr(self, 'pulse_core'):
            self.pulse_core.set_update_available(on)
        if hasattr(self, '_tray_glow'):
            self._tray_glow.set_active(on)
        if self._tray is not None:
            self._tray_update_action.setVisible(on)
            if on:
                self._tray_update_action.setText(
                    tr('Update verfügbar:') + ' v' + version)
        if (on and version != self._notified_update_version
                and not self._update_notice_queued):
            self._update_notice_queued = True
            QTimer.singleShot(1300, self._announce_update)

    def _announce_update(self):
        self._update_notice_queued = False
        if not self.manager.available or not self.manager.latest:
            return
        version = self.manager.latest
        if version == self._notified_update_version:
            return
        if not (self._tray and self._tray.isVisible()
                and QSystemTrayIcon.isSystemTrayAvailable()
                and QSystemTrayIcon.supportsMessages()):
            return
        self._tray.showMessage(
            APP_NAME + ' · ' + tr('Update verfügbar'),
            tr('Version {} ist verfügbar. Im Reiter Updates ansehen.').format(version),
            QSystemTrayIcon.Information, 7000)
        self._notified_update_version = version
        settings.set('last_notified_update_version', version)

    def _open_updates_from_tray(self):
        self.show_from_tray()
        for index, (name, _page) in enumerate(self.pages):
            if name == 'Updates':
                self.nav_buttons[index].setChecked(True)
                self._switch_page(index)
                return

    def set_interval(self, val):
        val = max(1, min(5, int(val)))
        self.sampler.interval = val
        for _, page in self.pages:
            for attr in ('graph', 'graph_load', 'graph_net', 'io_graph'):
                graph = getattr(page, attr, None)
                if hasattr(graph, 'set_interval'):
                    graph.set_interval(val)

    def _setup_sidebar_motion(self):
        """A lightweight image-composited transition; no layout work per tick."""
        self._sidebar_overlay = None

    def _capture_dashboard_layers(self, root):
        """Grab the visible dashboard tiles separately from their backdrop.

        The underlying DashboardBoard uses absolute child positioning, so
        temporarily hiding its tiles does not modify the grid geometry.
        Qt's QPixmap.grab() is called only at transition endpoints.
        """
        overview = self.pages[0][1]
        if self.stack.currentIndex() != 0 or not hasattr(overview, 'board'):
            return root.grab(), {}, None
        scroll = self.stack.widget(0)
        viewport = scroll.viewport()
        view_rect = QRect(viewport.mapTo(root, QPoint(0, 0)), viewport.size())
        captured = {}
        hidden = []
        for key, tile in overview.board.tiles.items():
            if tile.isVisible() and tile.geometry().isValid():
                r = QRect(tile.mapTo(root, QPoint(0, 0)), tile.size())
                if not r.intersects(view_rect):
                    continue
                captured[key] = (r, tile.grab())
                hidden.append(tile)
        try:
            for tile in hidden:
                tile.hide()
            frame = root.grab()
        finally:
            for tile in hidden:
                tile.show()
        return frame, captured, view_rect

    def _sidebar_visual_layers(self):
        """Capture moving sidebar children individually without affecting Qt layouts.

        Opacity effects prevent their pixels appearing in the *background*
        snapshot, but never hide widgets or remove them from a layout. This is
        performed only at the two endpoint states, never on animation frames.
        """
        side = self.sidebar
        def sprite(widget):
            if not widget.isVisibleTo(side):
                return None
            return (QRect(widget.mapTo(side, QPoint(0, 0)), widget.size()), widget.grab())
        nav = {i: sprite(btn) for i, btn in enumerate(self.nav_buttons)}
        brand = sprite(self.sidebar_brand)
        language = sprite(self.lang_host)
        version = sprite(self.sidebar_version)
        viewport = QRect(self.nav_scroll.viewport().mapTo(side, QPoint(0,0)),
                         self.nav_scroll.viewport().size())
        # Render ONLY the sidebar's own background, not its children. Avoid
        # attaching 14 QGraphicsOpacityEffects twice per click (slow on HiDPI).
        from PySide6.QtGui import QPixmap, QPainter
        dpr = side.devicePixelRatioF()
        background = QPixmap(round(side.width()*dpr), round(side.height()*dpr))
        background.setDevicePixelRatio(dpr)
        background.fill(Qt.transparent)
        painter = QPainter(background)
        side.render(painter, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawWindowBackground)
        painter.end()
        return dict(background=background, nav=nav, brand=brand,
                    language=language, version=version, viewport=viewport)

    def toggle_sidebar(self):
        """Move the sidebar seam smoothly, without animating the live widget tree.

        The former effect blended two *whole windows* on every animation frame,
        making widgets appear twice and the arrow jump. We now capture the
        layout at each endpoint *without* the arrow, then animate the sidebar,
        the content and the seam-docked arrow as separate layers. Actual Qt
        layouts are recalculated once when the state changes, not every frame.
        """
        # A second click during an unfinished transition used to remove the
        # live overlay and reveal a different layout in a single frame.
        # Complete the current glide before accepting another request.
        if self._sidebar_motion is not None:
            return

        if not motion.enabled():
            self._sidebar_collapsed = not self._sidebar_collapsed
            settings.set('sidebar_collapsed', self._sidebar_collapsed)
            self._apply_sidebar_state()
            self.centralWidget().layout().activate()
            overview = self.pages[0][1]
            if hasattr(overview, 'board'):
                overview.board.refresh_geometry(animate=False)
            return

        root = self.centralWidget()
        toggle = self.collapse_button
        old_width = self.sidebar.width()
        visible = root.isVisible()
        # Guard the FIRST rendered frame, before even hiding the arrow. Qt's
        # processEvents() is needed to settle QScrollArea, but must NEVER expose
        # the temporarily rebuilt destination layout to the compositor.
        freeze = SidebarFreeze(root, root.grab()) if visible else None
        old_arrow = toggle.grab()
        before = after = None
        before_side = after_side = None
        old_tiles = new_tiles = {}
        old_viewport = new_viewport = None
        new_arrow = None
        try:
            if visible:
                # QWidget.grab is synchronous. Briefly remove our guard only
                # while rendering offscreen, never while pumping Qt events.
                toggle.hide()
                freeze.hide()
                try:
                    before, old_tiles, old_viewport = self._capture_dashboard_layers(root)
                    before_side = self._sidebar_visual_layers()
                finally:
                    freeze.show()
                    freeze.raise_()
                    toggle.show()

            self._sidebar_collapsed = not self._sidebar_collapsed
            settings.set('sidebar_collapsed', self._sidebar_collapsed)
            self._sidebar_progress = 1.0 if self._sidebar_collapsed else 0.0
            self._apply_sidebar_state()
            root.layout().activate()
            overview = self.pages[0][1]
            if hasattr(overview, 'board'):
                overview.board._resize_coalesce.stop()
                overview.board.refresh_geometry(animate=False)
            # The first-frame guard remains visible throughout *all* queued
            # paint, resize and child-show events raised by the state change.
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
            root.layout().activate()
            if hasattr(overview, 'board'):
                overview.board._resize_coalesce.stop()
                overview.board.refresh_geometry(animate=False)
            new_width = self.sidebar.width()
            toggle.show()
            toggle.raise_()
            new_arrow = toggle.grab()

            if visible:
                toggle.hide()
                freeze.hide()
                try:
                    after, new_tiles, new_viewport = self._capture_dashboard_layers(root)
                    after_side = self._sidebar_visual_layers()
                finally:
                    freeze.show()
                    freeze.raise_()
                    toggle.show()

            if (before is None or after is None or before.isNull() or
                    after.isNull() or new_width == old_width):
                return

            overlay = SidebarTransition(root, before, after, old_width, new_width,
                                        old_arrow, new_arrow, old_tiles, new_tiles,
                                        old_viewport, new_viewport,
                                        before_side=before_side, after_side=after_side)
            self._sidebar_overlay = overlay
            # A single, opaque overlay now owns the whole visible transition;
            # expose the real destination widgets only after the final frame.
            overlay.raise_()
        finally:
            if freeze is not None:
                freeze.hide()
                freeze.deleteLater()
            toggle.show()
            # Only raise the real arrow if there is no animation overlay.
            # During the animation its ONE snapshot moves with the seam.
            if self._sidebar_overlay is None:
                toggle.raise_()

        # Keep endpoint snapshots untouched until the animation finishes.
        self.collapse_button.setEnabled(False)
        overlay.resized.connect(self._sidebar_finish)
        animation = QVariantAnimation(self)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        # Cache-only rendering during the glide, not 9 freshly re-sized glass
        # panels and charts per animation frame. Keep a single easing curve.
        animation.setDuration(motion.duration(300))
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.valueChanged.connect(overlay.set_progress)
        animation.finished.connect(self._sidebar_finish)
        self._sidebar_motion = animation
        animation.start()

    def _sidebar_finish(self):
        overlay = self._sidebar_overlay
        self._sidebar_overlay = None
        if overlay is not None:
            overlay.hide()
            overlay.deleteLater()
        animation = self._sidebar_motion
        self._sidebar_motion = None
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        # Keep the real, accessible button in the topmost paint layer.
        # The latest sample is redrawn now, not while a cached frame is moving.
        if self.last_sample is not None:
            # The compositor already has a settled destination frame. Refresh
            # only the visible page; repainting all hidden pages caused a burst
            # of expensive glass/sensor paints just as the transition ended.
            self.stack.currentWidget().update()
        self.collapse_button.setEnabled(True)
        if self.last_sample is not None:
            self._refresh_visible_page()
        self.collapse_button.show()
        self.collapse_button.raise_()

    def _apply_sidebar_state(self):
        """Only for initial construction: no animation before the window shows."""
        compact = self._sidebar_collapsed
        self.sidebar_layout.setContentsMargins(*( (8,55,8,12) if compact else (16,21,16,16) ))
        self.sidebar_brand.setVisible(not compact)
        self.lang_host.setVisible(not compact)
        self.sidebar_version.setVisible(not compact)
        self.nav_host.layout().setContentsMargins(1,2,1 if compact else 3,2)
        for btn in self.nav_buttons:btn.set_compact(compact)
        self.sidebar.setFixedWidth(74 if compact else 250)
        self.collapse_button.set_collapsed(compact)
        self.sidebar._position_toggle()

    @staticmethod
    def _is_scrolling_card(widget):
        """Qt drop shadows require expensive offscreen redraws on each scroll."""
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                return True
            parent = parent.parentWidget()
        return False

    def _optimize_scroll_surfaces(self):
        """Keep frosted cards but avoid offscreen effects within scrolling pages."""
        for card in self.findChildren(GlassSurface):
            fx = card.graphicsEffect()
            if isinstance(fx, QGraphicsDropShadowEffect):
                fx.setEnabled(not self._is_scrolling_card(card)
                              and theme.mode() != 'minimal')

    def _refresh_visible_page(self):
        if self.last_sample is None or not self.pages:
            return
        page = self.pages[self.stack.currentIndex()][1]
        try:
            page.refresh(self.last_sample, self.hist)
            self._last_refresh_error = None
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            signature = (self.stack.currentIndex(), type(exc), str(exc))
            if signature != self._last_refresh_error:
                log_exception(type(exc), exc, exc.__traceback__)
                self._last_refresh_error = signature

    def apply_appearance(self):
        """Restyle in-place; keep selected page, benchmark worker and scroll intact."""
        theme.set_mode(settings.get('theme', 'glass'))
        user_accent = settings.get('accent', '#4f8cff')
        theme.set_accent(resolve_accent(user_accent, self.distro['color']))
        QApplication.instance().setStyleSheet(theme.stylesheet())
        self.brand_mark.setPixmap(wordmark_pixmap(200, 42))
        self.pulse_core.sync_theme()
        current_icon = app_icon()
        QApplication.instance().setWindowIcon(current_icon)
        self.setWindowIcon(current_icon)
        if not self._tray_glow.active:
            self._tray.setIcon(current_icon)
        self._tray_glow.refresh()
        self._tray_preview.retheme()
        sync_installed_icon()
        minimal = theme.mode() == 'minimal'
        self.centralWidget().set_low_power(minimal)
        # Disabling graphics effects (rather than removing them) retains the
        # original glass shadows when switching back to Glass/Dark/Light.
        for card in self.findChildren(GlassSurface):
            fx = card.graphicsEffect()
            if isinstance(fx, QGraphicsDropShadowEffect):
                fx.setEnabled(not minimal and not self._is_scrolling_card(card))
        for gauge in self.findChildren(Gauge):
            if minimal:
                gauge._animate.stop()
                gauge._render_value = gauge.value
        for nav in self.nav_buttons:
            if minimal:
                nav._timer.stop()
            elif nav.glow and nav.isVisible():
                nav._timer.start()
        for graph in self.findChildren(ChartPanel):
            graph.retheme()
        disk = next((p for name, p in self.pages if name == 'Laufwerke'), None)
        if disk is not None and hasattr(disk, 'refresh_appearance'):
            disk.refresh_appearance()
        # Keep the linked credit in sync with the active theme accent.
        info_page = next((page for title, page in self.pages if title == 'Info'), None)
        if info_page is not None:
            info_page.support_credit.retranslate()
        # QPainter-based glass/rings/navigation read colors directly from theme.
        self.centralWidget().update()
        for widget in self.centralWidget().findChildren(QWidget):
            widget.update()
        if len(self.pages) > 8:
            pref = self.pages[8][1]
            if hasattr(pref, 'refresh_appearance'):
                pref.refresh_appearance()

    def _check_alerts(self, sample):
        preferences = settings.get_many(dict(
            cpu_temp=90, gpu_temp=90, ram_usage=90, disk_usage=95,
            alerts_enabled=False))
        limits = {key: preferences[key] for key in (
            'cpu_temp', 'gpu_temp', 'ram_usage', 'disk_usage')}
        friendly = {'cpu_temp': tr('CPU-Temperatur'), 'gpu_temp': tr('GPU-Temperatur'),
                    'ram_usage': tr('RAM-Auslastung'), 'disk_usage': tr('Systemlaufwerk-Belegung')}
        for warning in self._alerts.update(readings_from_sample(sample), limits,
                                           preferences['alerts_enabled']):
            msg = f'{friendly[warning.metric]}: {warning.value:.0f}{warning.unit}  (≥ {warning.limit:.0f}{warning.unit})'
            self.statusBar().showMessage(tr('Grenzwert überschritten') + ' · ' + msg, 16000)
            if self._tray is not None:
                self._tray.showMessage(APP_NAME + ' · ' + tr('Warnung'), msg,
                                       QSystemTrayIcon.Warning, 8000)

    def apply_dashboard_order(self):
        if self.pages:
            overview = self.pages[0][1]
            if hasattr(overview, 'apply_layout'):
                overview.apply_layout()

    def open_focus_window(self):
        from .insight_ui import FocusWindow
        if self._focus_window is None:
            self._focus_window = FocusWindow(self)
        if self.last_sample is not None:
            self._focus_window.update_sample(self.last_sample)
        self._focus_window.show()
        self._focus_window.raise_()
        self._focus_window.activateWindow()

    def reset_session_extrema(self):
        """Reset displayed minimum/maximum values without touching hardware."""
        self._extrema.reset()
        if self.last_sample is not None:
            self.last_sample["session_extrema"] = self._extrema.snapshot()
            self._refresh_visible_page()

    def on_sample(self, d):
        import time
        started = time.perf_counter()
        d["session_extrema"] = self._extrema.update(d)
        self.lab.ingest(d, settings.get_many({
            "cpu_temp": 90, "gpu_temp": 90, "ram_usage": 90
        }))
        if self._focus_window is not None and self._focus_window.isVisible():
            self._focus_window.update_sample(d)
        self.last_sample = d
        self._check_alerts(d)
        if self._tray is not None:
            self._tray.setToolTip(tray_tooltip(d))
            if self._tray_preview.isVisible():
                self._tray_preview.update_sample(d)
        # Native, lightweight branding animation driven by the real CPU sample.
        cpu_pct = d.get("cpu", {}).get("usage", 0.0)
        self.pulse_core.set_cpu_load(cpu_pct)
        h = self.hist
        g = d["gpus"][0] if d["gpus"] else None
        h["cpu"].append(d["cpu"]["usage"])
        h["ram"].append(d["ram"]["percent"])
        h["gpu"].append(g.get("usage") if g else None)
        h["vram"].append(g["vram_used"] / g["vram_total"] * 100
                         if g and isinstance(g.get("vram_used"), (int, float))
                         and isinstance(g.get("vram_total"), (int, float))
                         and g["vram_total"] > 0 else None)
        h["cpu_temp"].append(d.get("cpu", {}).get("temp"))
        h["gpu_temp"].append(g.get("temp") if g else None)
        h["gpu_clock"].append(g.get("clock") if g else None)
        h["gpu_power"].append(g.get("power") if g else None)
        h["net_down"].append(d["net"]["down"])
        h["net_up"].append(d["net"]["up"])
        h['io_read'].append(d['io']['read'])
        h['io_write'].append(d['io']['write'])
        # History is populated above; repaint only the selected page.
        # Switching pages immediately uses the latest sample and all history.
        if self._sidebar_motion is None:
            self._refresh_visible_page()
        self.last_render_ms = (time.perf_counter() - started) * 1000

    def _on_tray_activated(self, reason):
        """Plasma uses Trigger for a single left click, Context for right click."""
        if reason == QSystemTrayIcon.Trigger:
            self._tray_click_timer.start()
        elif reason == QSystemTrayIcon.DoubleClick:
            self._tray_click_timer.stop()
            self.show_from_tray()
        # Context is handled by QSystemTrayIcon's persistent QMenu itself.

    def show_tray_preview(self):
        popup = self._tray_preview
        popup.update_sample(self.last_sample)
        popup.retheme()
        area = self._tray.geometry()
        screen = QApplication.screenAt(area.center()) if not area.isNull() else QApplication.primaryScreen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is not None:
            bounds = screen.availableGeometry()
            x = area.center().x() - popup.width() // 2 if not area.isNull() else bounds.right() - popup.width() - 14
            y = area.top() - popup.sizeHint().height() - 12 if not area.isNull() else bounds.bottom() - popup.sizeHint().height() - 14
            popup.move(max(bounds.left()+8, min(x, bounds.right()-popup.width()-8)),
                       max(bounds.top()+8, min(y, bounds.bottom()-popup.sizeHint().height()-8)))
        popup.show()
        popup.raise_()

    def _toggle_tray_window(self):
        if self.isVisible() and not self.isMinimized():
            self._hide_to_tray()
        else:
            self.show_from_tray()

    def _hide_to_tray(self):
        """Only hide when a real system tray is available to reopen the app."""
        if not (self._tray and self._tray.isVisible() and
                QSystemTrayIcon.isSystemTrayAvailable()):
            return False
        self._tray_was_maximized = self.isMaximized()
        self.hide()
        return True

    def show_from_tray(self):
        self._tray_click_timer.stop()
        if self._tray_was_maximized or self.isMaximized():
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def restart_for_renderer(self):
        """Close gracefully; the portable launcher restarts after exit status 42."""
        if self.restart_requested:
            return True
        self._tray_click_timer.stop()
        self._force_quit = True
        if self.close():
            self.restart_requested = True
            return True
        # An active benchmark may refuse shutdown.
        self._force_quit = False
        return False

    def quit_from_tray(self):
        self._tray_click_timer.stop()
        self._force_quit = True
        if not self.close():
            # An active benchmark may refuse to close until its worker stops.
            self._force_quit = False

    def _inform_missing_tray(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, APP_NAME, tr('Die KDE-Systemleiste ist momentan nicht verfügbar. Vitalux bleibt geöffnet. Um es vollständig zu beenden, deaktiviere die Tray-Funktion unter Einstellungen.'))

    def closeEvent(self, event):
        if not self._force_quit and settings.get('close_to_tray', True):
            if self._hide_to_tray():
                event.ignore()
                return
            # On systems without an available system tray, do not silently
            # terminate the process when the user expects X to hide the app.
            # Remain accessible until the user changes the setting or a host
            # is available. Never hide a window that cannot be reopened.
            event.ignore()
            if not getattr(self, '_tray_missing_notice', False):
                self._tray_missing_notice = True
                QTimer.singleShot(0, self._inform_missing_tray)
            return
        # Commit an in-progress dashboard edit before the application closes.
        if self.pages and hasattr(self.pages[0][1], 'board') and self.pages[0][1].board.editing:
            self.pages[0][1].save_editor()
        for _name, page in self.pages:
            if isinstance(page, DiskPage):
                page.stop_smart()
                if not page.benchmark.stop_and_wait():
                    event.ignore()
                    return
        self.sampler.requestInterruption()
        self.sampler.wait(7000)
        self._tray_click_timer.stop()
        self._tray_glow.stop()
        self._tray_preview.close()
        if self._tray is not None:
            self._tray.hide()
        self.manager.shutdown()
        super().closeEvent(event)
        # quitOnLastWindowClosed(False) keeps the event loop alive when hidden
        # in the tray. An intentional close must end the process explicitly.
        if event.isAccepted():
            QTimer.singleShot(0, QApplication.instance().quit)
