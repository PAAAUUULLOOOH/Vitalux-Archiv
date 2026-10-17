"""Disable all transient on-hover help popups throughout Vitalux.

Normal hover colors, focus outlines, mouse clicks and explicit help dialogs
remain operational. Application-wide event filtering also covers Qt-created
popup windows and nested widgets, not only the sidebar.
"""
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QToolTip


class NoHoverHints(QObject):
    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.ToolTip, QEvent.Type.WhatsThis):
            QToolTip.hideText()
            return True
        return False


def install(app):
    guard = NoHoverHints(app)
    app.installEventFilter(guard)
    return guard
