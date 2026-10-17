"""Responsive dashboard editor with live magnetic reordering.

Cards preserve their preferred size except where large gaps would otherwise
remain. The existing 14 px grid spacing and indivisible hero tile are kept.
"""
from copy import deepcopy
from PySide6.QtCore import Qt, QEvent, QRect, QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QWidget, QToolButton, QVBoxLayout, QSizePolicy,
                                QGraphicsOpacityEffect)

from . import settings, theme, motion
from .i18n import tr
from .dashboard_model import (TITLES, ORDER, DEFAULT, PITCH, GAP, normalize_order,
                               grid_pack, move_order)


class Grip(QToolButton):
    """Visible top-right MOVE affordance only while hovering in edit mode."""
    def __init__(self, board, key, parent=None):
        super().__init__(parent)
        self.board, self.key = board, key
        self.setText(tr('Zum Verschieben halten'))
        self.setFixedSize(157, 25)
        self.setCursor(Qt.OpenHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName('tileMoveHint')
        self.setToolTip(tr('Kachel verschieben'))
        # This is a quiet caption rather than the sole clickable drag handle.
        # Global edit-mode mouse handling works from every point of the tile.

    def paintEvent(self, event):
        from PySide6.QtGui import QColor, QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        ink = QColor(theme.MUTED)
        ink.setAlpha(205 if theme.mode() in ('glass','black_glass') else 230)
        p.setPen(ink)
        p.drawText(self.rect().adjusted(0, 0, -2, 0),
                   Qt.AlignRight | Qt.AlignVCenter, self.text())
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.board.begin_drag(self.key, event.globalPosition().toPoint())
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.board.drag_to(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.board.end_drag()
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class Tile(QWidget):
    def __init__(self, board, key, content):
        super().__init__(board)
        self.board, self.key = board, key
        self.setObjectName('dashboardTile')
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMouseTracking(True)
        self._hover = False
        self._editing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        content.setParent(self)
        layout.addWidget(content)
        self.content = content
        self.drag = Grip(board,key,parent=self)
        self.remove = QToolButton(self)
        self.remove.setObjectName('tileRemoveHint')
        self.remove.setText('×')
        self.remove.setFixedSize(23,25)
        self.remove.setCursor(Qt.PointingHandCursor)
        self.remove.setToolTip(tr('Kachel ausblenden'))
        self.remove.clicked.connect(lambda: board.hide_tile(key))
        self.set_editing(False)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        # Close remains top-right; the unframed hint is directly below it,
        # right-aligned, and never overlaps the close hit target.
        self.remove.move(self.width()-39,9)
        self.drag.move(max(6,self.width()-177),36)
        self.drag.raise_()
        self.remove.raise_()

    def enterEvent(self,event):
        self._hover = True
        self._sync_grips()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self._hover = False
        self._sync_grips()
        super().leaveEvent(event)

    def _sync_grips(self):
        dragged = self.board._dragging is not None and self.board._dragging['key'] == self.key
        self.drag.setVisible(self._editing and (self._hover or dragged))
        self.remove.setVisible(self._editing and (self._hover or dragged))
        if self.drag.isVisible():self.drag.raise_()
        if self.remove.isVisible():self.remove.raise_()

    def set_editing(self,value):
        self._editing = bool(value)
        self._sync_grips()


class DashboardBoard(QWidget):
    changed = Signal()
    """Magnetic 12/6/3-column dashboard with conservative gap filling."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('dashboardBoard')
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        old = settings.get('dashboard_layout', {})
        self.order = normalize_order(settings.get('dashboard_order', None),old)
        self.hidden = set(k for k in settings.get('dashboard_hidden', []) if k in ORDER)
        # The distro mark belongs to the hero card but can be hidden independently.
        self.distro_logo_visible = settings.get('dashboard_distro_logo_visible', True) is not False
        self.tiles = {}
        self.editing = False
        self.history = []
        self._snapshot = None
        self._dragging = None
        self._last_targets = {}
        self._anims = {}
        self._anim_targets = {}
        self._fade_anims = {}
        self._suspend_resize_reflow = False
        # One geometry reflow at most per display refresh while the user is
        # actively resizing the window; no new tween per pixel.
        from PySide6.QtCore import QTimer
        self._resize_coalesce = QTimer(self)
        self._resize_coalesce.setSingleShot(True)
        self._resize_coalesce.setInterval(16)
        self._resize_coalesce.timeout.connect(lambda: self.refresh_geometry(animate=False))
        self.undo_shortcut = QShortcut(QKeySequence.Undo,self)
        self.undo_shortcut.activated.connect(self.undo)
        self.undo_shortcut.setEnabled(False)

    def register(self,key,content):
        if key not in ORDER:raise ValueError(key)
        tile=Tile(self,key,content)
        self.tiles[key]=tile
        tile.setVisible(key not in self.hidden)

    def _cols(self):
        return 12 if self.width()>=740 else 6 if self.width()>=475 else 3

    def _render_positions(self,order=None):
        return grid_pack(self.order if order is None else order,self.hidden,self._cols())

    def _frame(self,rect):
        x,y,w,h=rect
        cw=max(1,self.width())/self._cols()
        return QRect(round(x*cw),y*PITCH,max(28,round(w*cw-GAP)),max(45,h*PITCH-GAP))

    def refresh_geometry(self,animate=False,order=None,skip_dragged=False):
        targets=self._render_positions(order)
        bottom=max((p[1]+p[3] for p in targets.values()),default=1)
        height=bottom*PITCH+8
        if skip_dragged and self._dragging:
            # Do not shrink the scrollable canvas while the mouse is held.
            # That would move the cursor's target under an active gesture.
            height=max(height,self.height())
        if self.height()!=height:self.setFixedHeight(height)
        for key,tile in self.tiles.items():
            if key not in targets:
                if animate and self.editing and tile.isVisible():
                    self._fade_out(key,tile)
                elif key not in self._fade_anims:
                    tile.hide()
                continue
            self._stop_fade(key)
            tile.show()
            if skip_dragged and self._dragging and key == self._dragging['key']:
                continue
            self._animate_to(key,tile,self._frame(targets[key]),animate)
        self._last_targets=targets

    def _fade_out(self,key,tile):
        if not motion.enabled():
            self._stop_fade(key)
            tile.hide()
            return
        if key in self._fade_anims:return
        self._stop_anim(key)
        effect=QGraphicsOpacityEffect(tile)
        tile.setGraphicsEffect(effect)
        anim=QPropertyAnimation(effect,b'opacity',self)
        anim.setDuration(motion.duration(155))
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anims[key]=anim
        def complete():
            if self._fade_anims.get(key) is anim:
                self._fade_anims.pop(key,None)
                if key in self.hidden:tile.hide()
                tile.setGraphicsEffect(None)
            anim.deleteLater()
        anim.finished.connect(complete)
        anim.start()

    def _stop_fade(self,key):
        old=self._fade_anims.pop(key,None)
        if old is not None:
            old.stop()
            self.tiles[key].setGraphicsEffect(None)
            old.deleteLater()

    def _stop_anim(self,key):
        anim=self._anims.pop(key,None)
        self._anim_targets.pop(key,None)
        if anim is not None:
            anim.stop()
            anim.deleteLater()

    def _animate_to(self,key,tile,rect,animate):
        # Never restart an animation if its destination hasn't changed; that
        # was the main cause of jerky transitions in the previous editor.
        if self._anim_targets.get(key)==rect:
            return
        self._stop_anim(key)
        if animate and motion.enabled() and tile.isVisible() and tile.geometry().isValid() and tile.geometry()!=rect:
            same_size = tile.size() == rect.size()
            # Animating pos rather than geometry avoids resizing expensive
            # glass widgets and live graphs on every animation frame.
            animation=QPropertyAnimation(tile,b'pos' if same_size else b'geometry',self)
            animation.setStartValue(tile.pos() if same_size else tile.geometry())
            animation.setEndValue(rect.topLeft() if same_size else rect)
            animation.setDuration(motion.duration(170))
            animation.setEasingCurve(QEasingCurve.OutCubic)
            self._anims[key]=animation
            self._anim_targets[key]=rect
            def complete():
                if self._anims.get(key) is animation:
                    self._anims.pop(key,None)
                    self._anim_targets.pop(key,None)
                animation.deleteLater()
            animation.finished.connect(complete)
            animation.start()
        elif tile.geometry()!=rect:
            tile.setGeometry(rect)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if event.size().width()!=event.oldSize().width() and not self._suspend_resize_reflow:
            if not self._resize_coalesce.isActive():
                self._resize_coalesce.start()

    def begin_edit(self):
        self.editing=True
        # Intercept mouse gestures for every nested widget, not only the hint.
        QApplication.instance().installEventFilter(self)
        self.undo_shortcut.setEnabled(True)
        self.history.clear()
        self._snapshot=(list(self.order),set(self.hidden),self.distro_logo_visible)
        for tile in self.tiles.values():tile.set_editing(True)
        self.refresh_geometry()

    def finish_edit(self,save=True):
        if self._dragging:self.end_drag()
        QApplication.instance().removeEventFilter(self)
        if not save and self._snapshot is not None:
            self.order,self.hidden=list(self._snapshot[0]),set(self._snapshot[1])
            self.distro_logo_visible = self._snapshot[2]
        self.editing=False
        self.undo_shortcut.setEnabled(False)
        self.history.clear()
        self._snapshot=None
        for tile in self.tiles.values():tile.set_editing(False)
        self.refresh_geometry(animate=True)
        self.changed.emit()
        if save:
            settings.set('dashboard_order',list(self.order))
            settings.set('dashboard_hidden',sorted(self.hidden))
            settings.set('dashboard_distro_logo_visible',self.distro_logo_visible)
            # Retain normalized positions for compatibility with earlier builds.
            settings.set('dashboard_layout',{k:list(v) for k,v in grid_pack(self.order,(),12).items()})

    def _push_undo(self):
        if self.editing:
            self.history.append((list(self.order),set(self.hidden),self.distro_logo_visible))
            self.history=self.history[-30:]
            self.changed.emit()

    def undo(self):
        if not self.editing or not self.history:return
        self.order,self.hidden,self.distro_logo_visible=self.history.pop()
        self.refresh_geometry(animate=True)
        self.changed.emit()

    def hide_tile(self,key):
        if key == 'distro_logo':
            self.hide_distro_logo()
            return
        if not self.editing or key in self.hidden:return
        self._push_undo()
        self.hidden.add(key)
        self.refresh_geometry(animate=True)
        self.changed.emit()

    def show_tile(self,key):
        if key == 'distro_logo':
            self.show_distro_logo()
            return
        if not self.editing or key not in self.hidden:return
        self._push_undo()
        self.hidden.remove(key)
        self.refresh_geometry(animate=True)
        self.changed.emit()

    def hide_distro_logo(self):
        if not self.editing or not self.distro_logo_visible:return
        self._push_undo()
        self.distro_logo_visible = False
        self.changed.emit()

    def show_distro_logo(self):
        if not self.editing or self.distro_logo_visible:return
        self._push_undo()
        self.distro_logo_visible = True
        self.changed.emit()

    def reset(self):
        if not self.editing:return
        self._push_undo()
        self.order=list(ORDER)
        self.hidden.clear()
        self.distro_logo_visible = True
        self.refresh_geometry(animate=True)
        self.changed.emit()

    def _tile_for_event(self, widget):
        """Return the owning tile even for charts, nested cards and chip labels."""
        while isinstance(widget, QWidget):
            if isinstance(widget, Tile) and widget.board is self:
                return widget
            widget = widget.parentWidget()
        return None

    def eventFilter(self, watched, event):
        """App-level drag handling without unsupported Wayland mouse grabs.

        QWidget.grabMouse() on a non-popup triggers Qt Wayland warnings and may
        destabilize focus/input. The existing application event filter receives
        drag motion/release while the pointer remains in the Vitalux window.
        """
        if not self.editing:
            return super().eventFilter(watched,event)
        typ=event.type()
        if typ not in (QEvent.MouseButtonPress, QEvent.MouseMove,
                       QEvent.MouseButtonRelease):
            return super().eventFilter(watched,event)
        if self._dragging is not None:
            if typ == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                self.drag_to(event.globalPosition().toPoint())
                event.accept()
                return True
            if typ == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                owner=self.tiles[self._dragging['key']]
                self.end_drag()
                event.accept()
                return True
            return super().eventFilter(watched,event)
        if typ != QEvent.MouseButtonPress or event.button() != Qt.LeftButton:
            return super().eventFilter(watched,event)
        owner=self._tile_for_event(watched)
        if owner is None or not owner.isVisible() or owner.key in self.hidden:
            return super().eventFilter(watched,event)
        # The remove button must receive the click without starting a drag.
        if (watched is owner.remove or owner.remove.isAncestorOf(watched)
                or (isinstance(watched, QToolButton) and watched.property('distroLogoRemove'))):
            return super().eventFilter(watched,event)
        self.begin_drag(owner.key,event.globalPosition().toPoint())
        owner.setCursor(Qt.ClosedHandCursor)
        event.accept()
        return True

    def begin_drag(self,key,global_pos):
        if not self.editing or key in self.hidden:return
        # Do not record undo until the order actually changes.
        tile = self.tiles[key]
        self._dragging=dict(key=key,original=list(self.order),preview=list(self.order),
                            initial=global_pos, rect=QRect(tile.geometry()), moved=False)
        self._stop_anim(key)
        self.tiles[key].raise_()
        self.tiles[key]._sync_grips()

    def drag_to(self,global_pos):
        state=self._dragging
        if state is None:
            return
        delta = global_pos - state['initial']
        if not state['moved'] and delta.manhattanLength() < 6:
            return
        state['moved'] = True
        key = state['key']
        tile = self.tiles[key]
        # The picked-up tile follows the pointer 1:1, with NO grid constraint,
        # easing, interpolation or per-frame relayout. Its native size stays.
        tile.move(state['rect'].topLeft() + delta)

        # Calculate a *prospective* snapped insertion for the other tiles.
        # Only a changed insertion starts a neighboring-tile animation.
        where = self.mapFromGlobal(global_pos)
        visible = [k for k in state['preview'] if k not in self.hidden]
        without = [k for k in visible if k != key]
        candidates = []
        for index in range(len(without) + 1):
            sequence = without[:index] + [key] + without[index:]
            layout = grid_pack(sequence, self.hidden, self._cols())
            rect = self._frame(layout[key])
            center = rect.center()
            distance = (center.x()-where.x())**2 + (center.y()-where.y())**2
            candidates.append((distance, index))
        index = min(candidates)[1]
        proposed = without[:index] + [key] + without[index:]
        proposed += [k for k in state['preview'] if k in self.hidden]
        if proposed != state['preview']:
            state['preview'] = proposed
            self.refresh_geometry(animate=True, order=proposed, skip_dragged=True)
            tile.raise_()

    def end_drag(self):
        state=self._dragging
        if state is None:return
        self._dragging=None
        # No explicit grab/release: Qt Wayland only supports popup mouse grabs.
        owner=self.tiles[state['key']]
        owner.unsetCursor()
        if state['moved'] and state['preview']!=state['original']:
            self._push_undo()
            self.order=list(state['preview'])
        # The dragged widget only snaps/animates at release.
        self.refresh_geometry(animate=state['moved'])
        self.tiles[state['key']]._sync_grips()

    def available_hidden(self):
        hidden = [(key,tr(TITLES[key])) for key in ORDER if key in self.hidden]
        if not self.distro_logo_visible:
            hidden.append(('distro_logo', tr('Distributionslogo')))
        return hidden
