from collections import deque
import platform

import PySide6
from PySide6.QtCore import Qt, QPoint, QTimer, qVersion, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QThread, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget, QMenu, QSizePolicy, QToolButton, QGraphicsOpacityEffect

from . import theme, motion
from .ui_locale import QPushButton
from .dashboard import DashboardBoard, ORDER, TITLES
from .benchmark_ui import BenchmarkPanel
from .i18n import tr
from .sensors import drives, fmt_bytes, fmt_duration, fmt_rate, system_static
from .monitor_extra import graphics_runtime, system_gpu_device
from . import smart_monitor
from .smart_ui import SmartPane
from .widgets import (Bar, Card, ChipsGrid, GaugeBox, GaugeCard, HistoryGraph, ChartPanel, KeyValue,
                      Meter, label, legend, SidebarToggle)


class Page(QWidget):
    def refresh(self, d, h):
        pass

    def __init__(self, title, sub=""):
        super().__init__()
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(30, 24, 30, 30)
        self.root.setSpacing(16)
        # Die linke Navigation zeigt bereits klar den aktuellen Bereich an.
        # Zusätzliche Seitenüberschriften oben würden nur Fläche verbrauchen
        # und die Oberfläche unnötig wiederholen.
        self.content = QVBoxLayout()
        self.content.setSpacing(16)
        self.root.addLayout(self.content)
        self.root.addStretch(1)


def _row(*widgets):
    lay = QHBoxLayout()
    lay.setSpacing(16)
    for w in widgets:
        lay.addWidget(w, 1)
    return lay


def _temp_freq(c):
    parts = []
    if c["temp"] is not None:
        parts.append(f"{c['temp']:.0f} °C")
    if c["freq"]:
        parts.append(f"{c['freq'] / 1000:.2f} GHz")
    return " · ".join(parts) or f"{c['cores']} {tr('Kerne')} / {c['threads']} {tr('Threads')}"


def _vram_text(g):
    if g["vram_total"]:
        return f"{fmt_bytes(g['vram_used'])} / {fmt_bytes(g['vram_total'])}"
    return None


# ------------------------------------------------------------------ Übersicht
class OverviewPage(Page):
    def __init__(self, distro, logo):
        super().__init__("Übersicht", "Live-Status deines Systems")
        self.static = system_static()
        self.distro_version = distro.get("version") or "–"

        # Auf der Übersicht steht nur die erkannte Distribution. Der App-Name
        # bleibt in der Seitenleiste; Systemversionen stehen ausschließlich in
        # den Kacheln direkt unter dem Distro-Kopf.
        head = Card(hero=True)
        # Compact only the *outer whitespace*: the distro icon (96×96),
        # name typography and the eight system-info chips retain their
        # original dimensions. The saved 35px exactly match the reduced
        # single grid row; no child tile needs to be scaled to fit.
        head.layout().setContentsMargins(20, 7, 20, 7)
        head.body.setSpacing(5)
        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 4, 2)
        row.setSpacing(20)
        # The distribution logo is an independent visibility option *inside*
        # the hero tile: its name and system-information chips stay intact.
        self.distro_logo_host = QWidget(head)
        self.distro_logo_host.setFixedSize(96, 96)
        pic = label()
        pic.setParent(self.distro_logo_host)
        pic.setGeometry(0, 0, 96, 96)
        pic.setAlignment(Qt.AlignCenter)
        pic.setPixmap(logo)
        self.distro_logo_remove = QToolButton(self.distro_logo_host)
        self.distro_logo_remove.setObjectName('tileRemoveHint')
        self.distro_logo_remove.setProperty('distroLogoRemove', True)
        self.distro_logo_remove.setText('×')
        self.distro_logo_remove.setToolTip(tr('Distributionslogo ausblenden'))
        self.distro_logo_remove.setCursor(Qt.PointingHandCursor)
        self.distro_logo_remove.setFixedSize(25, 25)
        self.distro_logo_remove.move(70, 1)
        self.distro_logo_remove.raise_()
        row.addWidget(self.distro_logo_host, 0, Qt.AlignVCenter)
        distro_name = label(distro["name"], "heroTitle", wrap=True)
        distro_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(distro_name, 1, Qt.AlignVCenter)
        # Keep the original 96px distro icon and title. The space on the
        # right remains empty instead of duplicating the chip content.
        head.body.addLayout(row)

        # Restored 0.9.3.30 chip sizing: natural text/layout height and
        # standard Qt grid column sizing, without any fixed 80px tiles.
        # Uptime stays in the last small tile; the OS updater is gone.
        self.chips = ChipsGrid(["Kernel", "KDE", "Mesa", "Distributionsversion", "Sitzung", "Architektur", "Treiber", "Laufzeit"], columns=4)
        self.chips.grid.setVerticalSpacing(6)
        head.body.addWidget(self.chips)
        self.hero_card = head
        # Restore the ORIGINAL centered telemetry cards (v0.9.3.29).
        # Only the GPU description gets a constrained/elided label so that
        # its unusually long name cannot squeeze the GPU ring.
        self.g_cpu, self.g_gpu = GaugeCard("Prozessor"), GaugeCard("Grafik", compact_caption=True)
        self.g_ram, self.g_disk = GaugeCard("Arbeitsspeicher"), GaugeCard("System-Laufwerk")
        c1, c2 = Card("Auslastung"), Card("Netzwerk-Verlauf")
        self.graph_load = ChartPanel(['CPU', 'GPU', 'RAM'], [theme.accent(), theme.secondary_accent(), theme.TEAL])
        self.graph_net = ChartPanel(['Download', 'Upload'], [theme.accent(), theme.secondary_accent()], mode='rate')
        c1.body.addWidget(self.graph_load)
        c2.body.addWidget(self.graph_net)

        net = Card("Netzwerk")
        self.net_name = KeyValue("Aktive Schnittstelle")
        self.net_down, self.net_up = KeyValue("Download"), KeyValue("Upload")
        self.net_total = KeyValue("Daten gesamt")
        net.body.addWidget(self.net_name)
        net.body.addWidget(self.net_down)
        net.body.addWidget(self.net_up)
        net.body.addWidget(self.net_total)
        self.disks_card = Card("Laufwerke")
        self.disk_meters = {}

        # The editor is an OVERLAY aligned with the left sidebar arrow (y=13).
        # It takes no layout row, so the original dashboard moves back up.
        # The overlay arrow ends at y=43; place the first glass card just
        # below it, without wasting space on an extra header/toolbar row.
        self.root.setContentsMargins(30,45,30,30)
        self._sidebar_on_right = False
        self.layout_toggle = SidebarToggle(self, orientation='horizontal')
        self.layout_toggle.setToolTip(tr('Dashboard-Layout'))
        self.layout_toggle.setAccessibleName(tr('Dashboard-Layout'))

        self.layout_actions = QWidget(self)
        self.layout_actions.setObjectName('layoutActions')
        self.layout_actions.setAttribute(Qt.WA_TranslucentBackground, True)
        strip = QHBoxLayout(self.layout_actions)
        strip.setContentsMargins(0,0,0,0)
        strip.setSpacing(5)
        self._editor_buttons = []
        for key, icon, text, handler, width in (
            ('add', '+', 'Kacheln hinzufügen', self._show_hidden_tiles, 136),
            ('undo', '↶', 'Rückgängig', self._undo_layout, 109),
            ('reset', '↺', 'Standardlayout', self.reset_editor, 123),
            ('discard', '×', 'Verwerfen', self.discard_edit, 108),
            ('save', '✓', 'Speichern', self.save_editor, 105),
        ):
            action = QToolButton(self.layout_actions)
            action.setObjectName('layoutAction')
            action.setFixedSize(width,30)
            action.setCursor(Qt.PointingHandCursor)
            action.setFocusPolicy(Qt.StrongFocus)
            action.setProperty('layoutName',key)
            action.setText(f'{icon}  {tr(text)}')
            action.clicked.connect(handler)
            strip.addWidget(action)
            self._editor_buttons.append((key,icon,text,action))
        self._strip_width = sum(item[3].width() for item in self._editor_buttons) + strip.spacing()*4
        self.layout_actions.setFixedSize(self._strip_width,30)
        self._strip_open = False
        self._strip_anim = None
        self._strip_fraction = 0.0
        self._strip_effect = QGraphicsOpacityEffect(self.layout_actions)
        self._strip_effect.setOpacity(0.0)
        self.layout_actions.setGraphicsEffect(self._strip_effect)
        self.layout_actions.hide()
        self.board = DashboardBoard(self)
        for key, widget in (
            ('hero',head), ('cpu',self.g_cpu), ('gpu',self.g_gpu),
            ('ram',self.g_ram), ('disk',self.g_disk),
            ('graph_load',c1), ('graph_net',c2),
            ('network',net), ('drives',self.disks_card),
        ):
            self.board.register(key,widget)
        self.content.addWidget(self.board)
        self.layout_toggle.clicked.connect(self.toggle_editor)
        self.board.changed.connect(self._refresh_editor_actions)
        self.board.changed.connect(self._sync_distro_logo)
        self.distro_logo_remove.clicked.connect(self.board.hide_distro_logo)
        self._sync_distro_logo()
        self._position_editor_controls()
        QTimer.singleShot(0,self.board.refresh_geometry)

    def set_sidebar_side(self, right):
        self._sidebar_on_right = bool(right)
        self.layout_toggle.set_right_side(self._sidebar_on_right)
        self._position_editor_controls()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self,'layout_actions'):
            self._position_editor_controls()

    def _position_editor_controls(self):
        # Put the editor arrow and toolbar on the *outer* edge of content.
        x = 5 if self._sidebar_on_right else self.width()-self.layout_toggle.width()-5
        self.layout_toggle.move(x,13)
        # Shift just the small action strip, not its children or an animated
        # clipping mask. Widgets retain their full width throughout movement.
        target_x = (x+self.layout_toggle.width()+7 if self._sidebar_on_right
                    else x-self._strip_width-7)
        if self._strip_anim is None:
            direction = -1 if self._sidebar_on_right else 1
            self.layout_actions.move(target_x+round(direction*22*(1-self._strip_fraction)),13)
        self.layout_toggle.raise_()
        if self._strip_open:
            self.layout_actions.raise_()
            self.layout_toggle.raise_()

    def _reveal_strip(self, opening):
        """Slide one lightweight action row; never clip/repaint its text.

        The old QRegion mask was rebuilt on every frame and visibly sheared
        button labels, especially at fractional scaling on KDE/Wayland.
        Here button geometries never change. We animate only the containing
        QWidget's position and opacity with one synchronized animation group.
        """
        previous = self._strip_anim
        if previous is not None:
            previous.stop()
            previous.deleteLater()
            self._strip_anim = None
        start = self._strip_fraction
        finish = 1.0 if opening else 0.0
        if opening:
            self.layout_actions.show()
            self.layout_actions.raise_()
            self.layout_toggle.raise_()
        if not motion.enabled() or abs(finish-start) < .001:
            self._strip_fraction = finish
            self._strip_effect.setOpacity(finish)
            self._position_editor_controls()
            if not opening:
                self.layout_actions.hide()
            return
        # Keep the strip in one row with stable letter spacing. A property
        # animation on the opacity effect avoids a per-frame pixel mask.
        fade = QPropertyAnimation(self._strip_effect, b'opacity', self)
        fade.setStartValue(self._strip_effect.opacity())
        fade.setEndValue(finish)
        travel = QPropertyAnimation(self.layout_actions, b'pos', self)
        travel.setStartValue(self.layout_actions.pos())
        x=5 if self._sidebar_on_right else self.width()-self.layout_toggle.width()-5
        target=(x+self.layout_toggle.width()+7 if self._sidebar_on_right
                else x-self._strip_width-7)
        direction = -1 if self._sidebar_on_right else 1
        travel.setEndValue(QPoint(target+round(direction*22*(1-finish)),13))
        group=QParallelAnimationGroup(self)
        for animation in (fade,travel):
            animation.setDuration(motion.duration(round(235*abs(finish-start))))
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            group.addAnimation(animation)
        self._strip_anim=group
        fade.valueChanged.connect(lambda opacity: setattr(self, '_strip_fraction', float(opacity)))
        def completed():
            if self._strip_anim is not group:return
            self._strip_anim=None
            self._strip_fraction=finish
            if not opening:
                self.layout_actions.hide()
            self._position_editor_controls()
            group.deleteLater()
        group.finished.connect(completed)
        group.start()

    def _sync_distro_logo(self):
        visible = self.board.distro_logo_visible
        self.distro_logo_host.setVisible(visible)
        self.distro_logo_remove.setVisible(visible and self.board.editing)

    def _refresh_editor_actions(self):
        for key, _icon, _txt, action in self._editor_buttons:
            if key=='undo':action.setEnabled(bool(self.board.history))
            if key=='add':action.setEnabled(bool(self.board.available_hidden()))

    def _show_hidden_tiles(self):
        menu = QMenu(self)
        hidden=self.board.available_hidden()
        for key,title in hidden:
            item=menu.addAction(title)
            item.triggered.connect(lambda _=False,k=key:self.board.show_tile(k))
        if not hidden:
            item=menu.addAction(tr('Alle Kacheln sind bereits sichtbar'))
            item.setEnabled(False)
        add = next(a for k,_,_,a in self._editor_buttons if k=='add')
        menu.exec(add.mapToGlobal(QPoint(0,add.height())))
        self._refresh_editor_actions()

    def _undo_layout(self):
        self.board.undo()
        self._refresh_editor_actions()

    def toggle_editor(self):
        # A second arrow click commits the edited arrangement, closes the
        # actions AND exits edit mode (same semantics as the Save control).
        if self.board.editing:
            self.save_editor()
            return
        self.board.begin_edit()
        self._sync_distro_logo()
        self._refresh_editor_actions()
        self._strip_open = True
        self.layout_toggle.set_collapsed(True)
        self.layout_toggle.setToolTip(tr('Dashboard-Layout'))
        self._reveal_strip(True)

    def _finish_editor(self, save):
        if not self.board.editing:return
        self.board.finish_edit(save=save)
        self._sync_distro_logo()
        self._strip_open=False
        self.layout_toggle.set_collapsed(False)
        self.layout_toggle.reset_highlight()
        self.layout_toggle.setToolTip(tr('Dashboard-Layout'))
        self._reveal_strip(False)

    def save_editor(self):
        self._finish_editor(True)

    def discard_edit(self):
        self._finish_editor(False)

    def reset_editor(self):
        if not self.board.editing:return
        self.board.reset()
        self._finish_editor(True)

    def retranslate(self):
        self.layout_toggle.setToolTip(tr('Dashboard-Layout'))
        self.layout_toggle.setAccessibleName(tr('Dashboard-Layout'))
        for _,icon,source,action in self._editor_buttons:
            action.setText(f'{icon}  {tr(source)}')
        for tile in self.board.tiles.values():
            tile.drag.setText(tr('Zum Verschieben halten'))
            tile.drag.setToolTip(tr('Kachel verschieben'))
            tile.remove.setToolTip(tr('Kachel ausblenden'))
        self.distro_logo_remove.setToolTip(tr('Distributionslogo ausblenden'))

    def apply_layout(self):
        if not self.board.editing:
            self.board.refresh_geometry()

    def refresh(self, d, h):
        c, r, gpus, disks = d["cpu"], d["ram"], d["gpus"], d["disks"]
        net = d["net"]
        primary = net.get("primary") or {}
        driver = next((g.get("driver") for g in gpus if g.get("driver")), "amdgpu / drm" if gpus and gpus[0]["vendor"] == "AMD" else "–")
        self.chips.set("Kernel", self.static["kernel"])
        self.chips.set("KDE", f"Plasma {self.static['plasma']}")
        self.chips.set("Mesa", self.static["mesa"])
        self.chips.set("Distributionsversion", self.distro_version)
        self.chips.set("Sitzung", self.static["session"])
        self.chips.set("Architektur", self.static["arch"])
        self.chips.set("Treiber", driver)
        self.chips.set("Laufzeit", fmt_duration(d['uptime']))

        self.g_cpu.set(c["usage"], _temp_freq(c))
        if gpus:
            g = gpus[0]
            vt = _vram_text(g)
            # The full name remains available in a tooltip, while the compact
            # two-line caption is elided within its reserved height.
            self.g_gpu.set(g["usage"], g["name"] + (f"\nVRAM {vt}" if vt else ""))
            self.g_gpu.box.sub.setToolTip(g["name"] + (f"\nVRAM {vt}" if vt else ""))
        else:
            self.g_gpu.set(None, "Keine GPU-Daten verfügbar")
        self.g_ram.set(r["percent"], f"{fmt_bytes(r['used'])} / {fmt_bytes(r['total'])}")
        root = next((x for x in disks if x["mount"] == "/"), disks[0] if disks else None)
        if root:
            self.g_disk.set(root["percent"], f"{fmt_bytes(root['used'])} / {fmt_bytes(root['total'])}")

        self.graph_load.set_series([(h["cpu"], theme.accent()), (h["gpu"], theme.secondary_accent()), (h["ram"], theme.TEAL)])
        self.graph_net.set_series([(h["net_down"], theme.accent()), (h["net_up"], theme.secondary_accent())])
        self.net_name.set(primary.get("name", "–") + (f"  ·  {primary.get('speed', 0)} Mbit/s" if primary.get("speed") else ""))
        self.net_down.set(fmt_rate(net["down"]))
        self.net_up.set(fmt_rate(net["up"]))
        self.net_total.set(f"↓ {fmt_bytes(net['total_down'])}   ·   ↑ {fmt_bytes(net['total_up'])}")
        for x in disks[:6]:
            m = self.disk_meters.get(x["mount"])
            if m is None:
                m = self.disk_meters[x["mount"]] = Meter(x["mount"])
                self.disks_card.body.addWidget(m)
            m.set(x["percent"], f"{fmt_bytes(x['used'])} / {fmt_bytes(x['total'])}")


# ------------------------------------------------------------------ Prozessor
class CpuPage(Page):
    def __init__(self):
        super().__init__("Prozessor", "Auslastung, Takt und Temperatur")
        top = Card()
        self.name = label("–", "bigName", wrap=True)
        top.body.addWidget(self.name)
        grid = QGridLayout()
        grid.setHorizontalSpacing(40)
        self.kv = {k: KeyValue(k) for k in ("Kerne / Threads", "Takt", "Temperatur", "Last (1 / 5 / 15 Min)", "CPU-Package-Leistung")}
        for i, w in enumerate(self.kv.values()):
            grid.addWidget(w, i // 2, i % 2)
        top.body.addLayout(grid)
        self.content.addWidget(top)

        self.gauge = GaugeCard("Gesamtauslastung")
        graph = Card("Verlauf")
        self.graph = ChartPanel(['CPU'], [theme.accent()])
        graph.body.addWidget(self.graph)
        lay = QHBoxLayout()
        lay.setSpacing(16)
        lay.addWidget(self.gauge, 1)
        lay.addWidget(graph, 3)
        self.content.addLayout(lay)

        self.cores_card = Card("Threads")
        self.cores_grid = QGridLayout()
        self.cores_grid.setHorizontalSpacing(24)
        self.cores_grid.setVerticalSpacing(12)
        self.cores_card.body.addLayout(self.cores_grid)
        self.content.addWidget(self.cores_card)
        self.core_meters = []

    def refresh(self, d, h):
        c = d["cpu"]
        self.name.setText(c["model"])
        self.kv["Kerne / Threads"].set(f"{c['cores']} / {c['threads']}")
        fm = f" (max {c['freq_max'] / 1000:.2f})" if c["freq_max"] else ""
        self.kv["Takt"].set(f"{c['freq'] / 1000:.2f} GHz{fm}" if c["freq"] else "–")
        self.kv["Temperatur"].set(f"{c['temp']:.0f} °C" if c["temp"] is not None else tr("nicht verfügbar"))
        self.kv["CPU-Package-Leistung"].set(f"{c['power']:.1f} W" if c.get("power") is not None else tr("nicht verfügbar"))
        self.kv["Last (1 / 5 / 15 Min)"].set(" / ".join(f"{x:.2f}" for x in c["load"]))
        self.gauge.set(c["usage"], f"{c['threads']} {tr('Threads')}")
        self.graph.set_series([(h["cpu"], theme.accent())])
        while len(self.core_meters) < len(c["per_core"]):
            i = len(self.core_meters)
            m = Meter(f"Thread {i}")
            self.cores_grid.addWidget(m, i // 4, i % 4)
            self.core_meters.append(m)
        for m, v in zip(self.core_meters, c["per_core"]):
            m.set(v)


# ------------------------------------------------------------------ Grafik
class GpuCard(Card):
    def __init__(self):
        super().__init__()
        self.name = label("–", "bigName", wrap=True)
        self.meta = label("", "muted")
        self.body.addWidget(self.name)
        self.body.addWidget(self.meta)
        gauges = QHBoxLayout()
        self.g_use, self.g_vram = GaugeBox("Auslastung"), GaugeBox("Videospeicher")
        gauges.addWidget(self.g_use, 1)
        gauges.addWidget(self.g_vram, 1)
        self.body.addLayout(gauges)
        self.body.addWidget(label('LIVE-SENSOREN', 'cardTitle'))
        self.kv = {k: KeyValue(k) for k in ("Temperatur", "Hotspot", "Leistung", "Lüfter", "Lüfterdrehzahl", "GPU-Takt", "Speicher-Takt")}
        live_metrics = QGridLayout()
        live_metrics.setHorizontalSpacing(22)
        for i, key in enumerate(('Temperatur', 'Hotspot', 'Leistung', 'Lüfter')):
            live_metrics.addWidget(self.kv[key], i // 2, i % 2)
        self.body.addLayout(live_metrics)
        self.graph = ChartPanel(['Auslastung', 'VRAM'], [theme.accent(), theme.secondary_accent()])
        self.body.addWidget(self.graph)
        self.body.addWidget(label('TECHNISCHE DETAILS', 'cardTitle'))
        technical = QGridLayout()
        for i, key in enumerate(('Lüfterdrehzahl', 'GPU-Takt', 'Speicher-Takt')):
            technical.addWidget(self.kv[key], i // 2, i % 2)
        self.body.addLayout(technical)
        self.h_use, self.h_vram = deque(maxlen=900), deque(maxlen=900)

    def refresh(self, g):
        self.name.setText(g["name"])
        self.meta.setText(" · ".join(x for x in (g["vendor"], g.get("driver") and f"{tr('Treiber')} {g['driver']}") if x))
        self.g_use.set(g["usage"], "")
        pct = g["vram_used"] / g["vram_total"] * 100 if g["vram_total"] else None
        self.g_vram.set(pct, _vram_text(g) or "nicht verfügbar")
        fmt = lambda v, u: f"{v:.0f} {u}" if v is not None else tr("nicht verfügbar")
        self.kv["Temperatur"].set(fmt(g["temp"], "°C"))
        self.kv["Hotspot"].set(fmt(g.get("hotspot"), "°C"))
        self.kv["Leistung"].set(fmt(g["power"], "W"))
        self.kv["Lüfter"].set(fmt(g["fan"], "%"))
        self.kv["Lüfterdrehzahl"].set(fmt(g.get("fan_rpm"), "RPM"))
        self.kv["GPU-Takt"].set(fmt(g["clock"], "MHz"))
        self.kv["Speicher-Takt"].set(fmt(g["clock_mem"], "MHz"))
        self.h_use.append(g["usage"] or 0)
        self.h_vram.append(pct or 0)
        self.graph.set_series([(self.h_use, theme.accent()), (self.h_vram, theme.secondary_accent())])


class GpuPage(Page):
    def __init__(self):
        super().__init__("Grafik", "GPU-Auslastung, Videospeicher und Sensoren")
        self.cards = []
        self.none = Card()
        self.none.body.addWidget(label("Keine GPU-Daten gefunden. Unterstützt werden NVIDIA (nvidia-smi), AMD (amdgpu) und Intel (Name, ohne Auslastung).", wrap=True))
        self.content.addWidget(self.none)

    def refresh(self, d, h):
        gpus = d["gpus"]
        self.none.setVisible(not gpus)
        while len(self.cards) < len(gpus):
            card = GpuCard()
            self.content.addWidget(card)
            self.cards.append(card)
        for i, card in enumerate(self.cards):
            card.setVisible(i < len(gpus))
            if i < len(gpus):
                card.refresh(gpus[i])


# ------------------------------------------------------------------ Speicher
class MemoryPage(Page):
    def __init__(self):
        super().__init__("Arbeitsspeicher", "RAM und Swap")
        self.g_ram, self.g_swap = GaugeCard("RAM"), GaugeCard("Swap")
        stats = Card("Details")
        self.kv = {k: KeyValue(k) for k in ("Gesamt", "In Benutzung", "Verfügbar", "Cache", "Puffer")}
        for w in self.kv.values():
            stats.body.addWidget(w)
        self.content.addLayout(_row(self.g_ram, self.g_swap, stats))
        graph = Card("Verlauf")
        self.graph = ChartPanel(['RAM'], [theme.TEAL])
        graph.body.addWidget(self.graph)
        self.content.addWidget(graph)

    def refresh(self, d, h):
        r = d["ram"]
        self.g_ram.set(r["percent"], f"{fmt_bytes(r['used'])} / {fmt_bytes(r['total'])}")
        if r["swap_total"]:
            self.g_swap.set(r["swap_percent"], f"{fmt_bytes(r['swap_used'])} / {fmt_bytes(r['swap_total'])}")
        else:
            self.g_swap.set(None, "nicht aktiv")
        self.kv["Gesamt"].set(fmt_bytes(r["total"]))
        self.kv["In Benutzung"].set(fmt_bytes(r["used"]))
        self.kv["Verfügbar"].set(fmt_bytes(r["available"]))
        self.kv["Cache"].set(fmt_bytes(r["cached"]))
        self.kv["Puffer"].set(fmt_bytes(r["buffers"]))
        self.graph.set_series([(h["ram"], theme.TEAL)])


# ------------------------------------------------------------------ Laufwerke
class SmartWorker(QThread):
    completed = Signal(object)

    def run(self):
        try:
            self.completed.emit(smart_monitor.scan(drives()))
        except Exception as exc:
            self.completed.emit([{'name': 'SMART', 'error': str(exc)}])


class DiskPage(Page):
    def __init__(self):
        super().__init__("Laufwerke", "Datenträger, Belegung und Durchsatz")
        self.hw = Card("Physische Datenträger")
        self.hw_rows = {}
        self.parts = Card("Partitionen")
        self.part_meters = {}
        io = Card("Durchsatz")
        self.read, self.write = KeyValue("Lesen"), KeyValue("Schreiben")
        io.body.addWidget(self.read)
        io.body.addWidget(self.write)
        self.content.addLayout(_row(self.hw, io))
        io_graph = Card('Laufwerksaktivität')
        self.io_graph = ChartPanel(['Lesen', 'Schreiben'], [theme.accent(), theme.secondary_accent()], mode='rate')
        io_graph.body.addWidget(self.io_graph)
        self.content.addWidget(io_graph)
        self.content.addWidget(self.parts)
        self.smart_card = SmartPane()
        self.smart_button = self.smart_card.button
        self.smart_status = self.smart_card.status
        self.smart_button.clicked.connect(self.request_smart)
        self.content.addWidget(self.smart_card)
        self._smart_worker = None
        self._smart_loaded = False
        # Disk selectors are already visible while SMART runs in a worker.
        # Do not delay the user's first access to drive details.
        self.smart_card.set_devices(drives())
        # Integrierter Laufwerks-Benchmark unter den Laufwerksdaten.
        self.benchmark = BenchmarkPanel()
        self.content.addWidget(self.benchmark)
        self._tick = 0

    def stop_smart(self):
        if self._smart_worker and self._smart_worker.isRunning():
            # The read-only scan uses finite per-drive timeouts; wait for it to
            # finish so Qt never destroys a running QThread on app shutdown.
            self._smart_worker.wait()

    def request_smart(self):
        if self._smart_worker and self._smart_worker.isRunning():
            return
        self.smart_button.setEnabled(False)
        self.smart_status.setText('Lese SMART-Daten im Hintergrund …')
        self._smart_worker = SmartWorker(self)
        self._smart_worker.completed.connect(self.show_smart)
        self._smart_worker.finished.connect(lambda: self.smart_button.setEnabled(True))
        self._smart_worker.start()

    def show_smart(self, reports):
        self._smart_loaded = True
        self.smart_card.set_reports(reports, drives())

    def refresh_appearance(self):
        self.smart_card.refresh_theme()

    def retranslate(self):
        self.smart_card.retranslate()

    def refresh(self, d, h):
        if self._tick % 30 == 0:
            for dr in drives():
                if dr["name"] not in self.hw_rows:
                    kv = KeyValue(f"{dr['name']}  ·  {dr['kind']}")
                    self.hw.body.addWidget(kv)
                    self.hw_rows[dr["name"]] = kv
                text = (dr["model"] + "  ·  " if dr["model"] else "") + fmt_bytes(dr["size"], 1000)
                self.hw_rows[dr["name"]].set(text)
        self._tick += 1
        self.benchmark.update_volumes(d["disks"])
        self.read.set(fmt_rate(d["io"]["read"]))
        self.write.set(fmt_rate(d["io"]["write"]))
        self.io_graph.set_series([(h['io_read'], theme.accent()), (h['io_write'], theme.secondary_accent())])
        current = {x["mount"] for x in d["disks"]}
        for x in d["disks"]:
            m = self.part_meters.get(x["mount"])
            if m is None:
                m = self.part_meters[x["mount"]] = Meter(f"{x['mount']}   ({x['device']}, {x['fstype']})")
                self.parts.body.addWidget(m)
            m.setVisible(True)
            m.set(x["percent"], f"{fmt_bytes(x['used'])} / {fmt_bytes(x['total'])}   ({x['percent']:.0f}%)")
        for mount, m in self.part_meters.items():
            if mount not in current:
                m.setVisible(False)


# ------------------------------------------------------------------ Netzwerk
class NetworkPage(Page):
    def __init__(self):
        super().__init__("Netzwerk", "Live-Datenverkehr, Schnittstellen und Verbindungsdetails")
        top = Card(hero=True)
        self.primary = KeyValue("Aktive Schnittstelle")
        self.addr = KeyValue("IPv4")
        self.total = KeyValue("Daten gesamt")
        self.speed = KeyValue("Link-Geschwindigkeit")
        self.gateway = KeyValue('Gateway')
        self.dns = KeyValue('DNS-Server')
        self.mac = KeyValue('MAC-Adresse')
        top.body.addWidget(self.primary)
        top.body.addWidget(self.addr)
        top.body.addWidget(self.total)
        top.body.addWidget(self.speed)
        top.body.addWidget(self.gateway)
        top.body.addWidget(self.dns)
        top.body.addWidget(self.mac)
        self.content.addWidget(top)

        graph = Card("Netzwerk-Verlauf")
        self.graph = ChartPanel(['Download', 'Upload'], [theme.accent(), theme.secondary_accent()], mode='rate')
        graph.body.addWidget(self.graph)
        self.content.addWidget(graph)

        rates = Card("Aktuelle Übertragungsraten")
        self.down = KeyValue("Download")
        self.up = KeyValue("Upload")
        rates.body.addWidget(self.down)
        rates.body.addWidget(self.up)

        self.ifaces_card = Card("Netzwerkschnittstellen")
        self.iface_rows = {}
        self.content.addLayout(_row(rates, self.ifaces_card))

    def refresh(self, d, h):
        net = d["net"]
        p = net.get("primary") or {}
        self.primary.set(p.get("name", "–"))
        self.addr.set(p.get("ipv4") or "–")
        self.total.set(f"↓ {fmt_bytes(net['total_down'])}   ·   ↑ {fmt_bytes(net['total_up'])}")
        self.speed.set(f"{p.get('speed', 0)} Mbit/s" if p.get("speed") else "–")
        self.gateway.set(net.get('gateway') or '–')
        self.dns.set(', '.join(net.get('dns', [])) or '–')
        self.mac.set(p.get('mac') or '–')
        self.down.set(fmt_rate(net["down"]))
        self.up.set(fmt_rate(net["up"]))
        self.graph.set_series([(h["net_down"], theme.accent()), (h["net_up"], theme.secondary_accent())])
        for iface in net.get("interfaces", []):
            row = self.iface_rows.get(iface["name"])
            if row is None:
                row = self.iface_rows[iface["name"]] = KeyValue(iface["name"])
                self.ifaces_card.body.addWidget(row)
            state = "UP" if iface["isup"] else "DOWN"
            speed = f"{iface['speed']} Mbit/s" if iface["speed"] else "–"
            ip = iface.get("ipv4") or iface.get("ipv6") or tr('keine IP')
            row.set(f"{state} · {speed} · {ip}")


# ------------------------------------------------------------------ System
class SystemPage(Page):
    def __init__(self, distro):
        super().__init__("System", "Betriebssystem, Hardware und Software")
        s = system_static()
        os_card = Card("Betriebssystem")
        self.uptime = KeyValue("Laufzeit")
        for k, v in (("Distribution", distro["name"]), ("Kernel", s["kernel"]), ("Architektur", s["arch"]),
                     ("Rechnername", s["host"]), ("Benutzer", s["user"]), ("Desktop", s["desktop"]),
                     ("Sitzung", s["session"])):
            kv = KeyValue(k)
            kv.set(v)
            os_card.body.addWidget(kv)
        os_card.body.addWidget(self.uptime)

        hw_card = Card("Hardware")
        self.cpu_kv, self.gpu_kv = KeyValue("Prozessor"), KeyValue("Grafik")
        for k, v in (("Hersteller", s["vendor"]), ("Modell", s["product"]),
                     ("Mainboard", s["board"] or "–"), ("BIOS", s["bios"])):
            kv = KeyValue(k)
            kv.set(v)
            hw_card.body.addWidget(kv)
        hw_card.body.addWidget(self.cpu_kv)
        hw_card.body.addWidget(self.gpu_kv)

        sw_card = Card("Software")
        for k, v in (("Python", platform.python_version()), ("Qt", qVersion()), ("PySide6", PySide6.__version__),
                     ("KDE Plasma", s["plasma"]), ("KWin", s["kwin"]), ("KDE Frameworks", s["frameworks"]),
                     ("Mesa", s["mesa"])):
            kv = KeyValue(k)
            kv.set(v)
            sw_card.body.addWidget(kv)
        self.content.addLayout(_row(os_card, hw_card))
        self.content.addWidget(sw_card)
        graphics_card = Card('Grafiksystem & Anzeigen')
        from PySide6.QtGui import QGuiApplication
        runtime = graphics_runtime(QGuiApplication.platformName(), QGuiApplication.screens())
        for title, value in (('Qt-Grafikbackend', runtime['qt_platform']),
                             ('Display-Server', runtime['runtime']),
                             ('Sitzungstyp', runtime['session'])):
            kv = KeyValue(title)
            kv.set(value)
            graphics_card.body.addWidget(kv)
        for idx, screen in enumerate(runtime['screens'], 1):
            rate = f" · {screen['hz']:g} Hz" if screen['hz'] is not None else ''
            kv = KeyValue(f'Bildschirm {idx} · {screen["name"]}')
            scale = f" · {screen['scale_percent']} % {tr('Skalierung')}" if screen.get('scale_percent', 100) != 100 else ''
            kv.set(f"{screen['width']} × {screen['height']}{rate}{scale}")
            graphics_card.body.addWidget(kv)
        self.render_gpu = KeyValue('Erkannte Grafik / mögliche Render-GPU')
        graphics_card.body.addWidget(self.render_gpu)
        self.render_driver = KeyValue('Grafiktreiber')
        graphics_card.body.addWidget(self.render_driver)
        graphics_card.body.addWidget(label('Bei mehreren GPUs lässt sich das aktive Rendergerät ohne zusätzliche Abfrage nicht immer eindeutig bestimmen.', 'muted', wrap=True))
        self.content.addWidget(graphics_card)
        perf_card = Card('Vitalux · Ressourcenverbrauch')
        self.app_cpu = KeyValue('Vitalux CPU')
        self.app_ram = KeyValue('Vitalux RAM')
        self.app_paint = KeyValue('Messwert-Aktualisierung')
        perf_card.body.addWidget(self.app_cpu)
        perf_card.body.addWidget(self.app_ram)
        perf_card.body.addWidget(self.app_paint)
        self.content.addWidget(perf_card)

    def refresh(self, d, h):
        self.render_gpu.set(system_gpu_device(d['gpus']))
        self.render_driver.set(', '.join(dict.fromkeys(str(g.get('driver')) for g in d['gpus'] if g.get('driver'))) or '–')
        app = d.get('app_resources') or {}
        self.app_cpu.set(f"{app['cpu_percent']:.1f} %" if app.get('cpu_percent') is not None else '–')
        self.app_ram.set(fmt_bytes(app.get('rss_bytes')))
        # The render duration is measured by the main window after paint data dispatch.
        from PySide6.QtWidgets import QApplication
        window = QApplication.activeWindow()
        duration = getattr(window, 'last_render_ms', None)
        self.app_paint.set(f'{duration:.1f} ms' if duration is not None else '–')
        self.uptime.set(fmt_duration(d["uptime"]))
        self.cpu_kv.set(d["cpu"]["model"])
        self.gpu_kv.set(", ".join(g["name"] for g in d["gpus"]) or "–")
