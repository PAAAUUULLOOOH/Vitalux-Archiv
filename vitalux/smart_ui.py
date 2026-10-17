"""SMART health inspector in CrystalDiskInfo-style information hierarchy.
Own Vitalux-themed Qt widgets; no third-party design assets.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QFrame,QGridLayout,QHBoxLayout,QVBoxLayout,
    QLabel,QProgressBar,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QSizePolicy)
from . import theme
from .widgets import Card,label
from .ui_locale import QPushButton, QComboBox
from .i18n import tr
from .sensors import fmt_bytes

FIELDS=(('Firmware','firmware'),('Seriennummer','serial'),('Schnittstelle','interface'),
        ('Übertragungsmodus','transfer_mode'),('Kapazität','capacity'),('Standard','standard'),
        ('Betriebsstunden','hours'),('Einschaltvorgänge','power_cycles'),
        ('Gelesene Daten','read_bytes'),('Geschriebene Daten','written_bytes'),
        ('Drehzahl','rotation_rate'),('Formfaktor','form_factor'))
HEADERS=('ID','Attribut','Aktuell','Schlechtester','Schwelle','Rohwert')


def tint(hex_value,opacity):
    c=QColor(hex_value)
    return f'rgba({c.red()},{c.green()},{c.blue()},{opacity})'

class SmartPane(Card):
    def __init__(self):
        super().__init__('SMART / Laufwerkszustand')
        self._reports=[];self._drives=[];self._filling=False
        row=QHBoxLayout();row.setSpacing(12)
        self.selector=QComboBox();self.selector.setMinimumWidth(250)
        self.selector.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.selector.currentIndexChanged.connect(self.show_selected)
        row.addWidget(self.selector,1)
        self.button=QPushButton('SMART-Daten prüfen');self.button.setObjectName('ghostBtn')
        row.addWidget(self.button);self.body.addLayout(row)
        self.status=label('SMART-Daten werden beim Öffnen der Laufwerke geprüft.','muted',wrap=True)
        self.body.addWidget(self.status)
        self.drive_name=label('–','bigName',wrap=True)
        self.drive_name.setMinimumHeight(34);self.body.addWidget(self.drive_name)
        summaryrow=QHBoxLayout();summaryrow.setSpacing(18)
        group=QFrame();group.setFixedWidth(176)
        gl=QVBoxLayout(group);gl.setContentsMargins(8,6,8,8);gl.setSpacing(6)
        self.health_label=label('Gesundheitszustand','muted',Qt.AlignCenter)
        gl.addWidget(self.health_label)
        self.health_badge=QLabel('–');self.health_badge.setAlignment(Qt.AlignCenter)
        self.health_badge.setMinimumHeight(76);gl.addWidget(self.health_badge)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setFixedHeight(9)
        self.progress.setTextVisible(False);gl.addWidget(self.progress)
        self.temp_label=label('Temperatur','muted',Qt.AlignCenter);gl.addWidget(self.temp_label)
        self.temp_badge=QLabel('–');self.temp_badge.setAlignment(Qt.AlignCenter)
        self.temp_badge.setMinimumHeight(48);gl.addWidget(self.temp_badge);gl.addStretch()
        summaryrow.addWidget(group)
        grid_frame=QWidget();grid=QGridLayout(grid_frame)
        grid.setContentsMargins(0,0,0,0);grid.setHorizontalSpacing(14);grid.setVerticalSpacing(9)
        self.fields={}
        for index,(title,key) in enumerate(FIELDS):
            gridrow,col=divmod(index,2);left=col*2
            lbl=label(title,'muted');lbl.setMinimumWidth(100)
            value=label('–','strong',wrap=True);value.setMinimumWidth(120)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(lbl,gridrow,left);grid.addWidget(value,gridrow,left+1)
            self.fields[key]=(lbl,value,title)
        summaryrow.addWidget(grid_frame,1);self.body.addLayout(summaryrow)
        self.table_title=label('S.M.A.R.T.-Attribute','cardTitle');self.body.addWidget(self.table_title)
        self.table=QTableWidget(0,len(HEADERS));self.table.setHorizontalHeaderLabels([tr(x) for x in HEADERS])
        self.table.verticalHeader().hide();self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection);self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setMinimumHeight(320)
        self.table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        head=self.table.horizontalHeader()
        head.setSectionResizeMode(0,QHeaderView.Fixed);head.setSectionResizeMode(1,QHeaderView.Stretch)
        self.table.setColumnWidth(0,50)
        for col in range(2,6):head.setSectionResizeMode(col,QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(29);self.body.addWidget(self.table)
        self.notes=label('HDDs melden normalerweise keine verbleibende Lebensdauer in Prozent.','muted',wrap=True)
        self.body.addWidget(self.notes)
        self.refresh_theme()

    def set_devices(self, devices):
        """Show disk selectors immediately; SMART values arrive asynchronously."""
        self._drives = list(devices or [])
        self.set_reports([{'name': d.get('name'), 'model': d.get('model'),
                           '_pending': True} for d in self._drives
                          if d.get('name')], self._drives)

    def set_reports(self,reports,drives=None):
        previous=self.selector.currentData()
        self._reports=list(reports);self._drives=list(drives or [])
        models={x['name']:x.get('model') or '' for x in self._drives if x.get('name')}
        self._filling=True;self.selector.clear()
        for d in self._reports:
            name=d.get('name') or '–';model=d.get('model') or models.get(name)
            self.selector.addItem(f'{name} · {model}' if model and model!='–' else name,name)
        match=self.selector.findData(previous)
        self.selector.setCurrentIndex(match if match>=0 else 0)
        self._filling=False;self.show_selected()

    @staticmethod
    def format_field(key,val):
        if val is None or val=='' or val=='–':return '–'
        if key in ('read_bytes','written_bytes','capacity'):return fmt_bytes(val,1000)
        if key=='hours':return f'{val:,} h'.replace(',','.')
        if key=='power_cycles':return f'{val:,}'.replace(',','.')
        if key=='rotation_rate':return f'{val} U/min' if val else '–'
        return str(val)

    def show_selected(self,*_):
        if self._filling:return
        index=self.selector.currentIndex()
        data=self._reports[index] if 0<=index<len(self._reports) else {}
        static=next((x for x in self._drives if x.get('name')==data.get('name')),{})
        model=data.get('model') or static.get('model') or '–'
        self.drive_name.setText(model if model!='–' else data.get('name') or '–')
        status=data.get('health','Unbekannt');pct=data.get('health_percent')
        color=(theme.CRIT if status=='Warnung' else '#1cbc92' if status=='Gut' and theme.mode()!='light'
               else '#128666' if status=='Gut' else theme.MUTED)
        self.health_badge.setText(tr(status)+(f'\n{pct} %' if pct is not None else ''))
        self.health_badge.setStyleSheet(f'border:1px solid {tint(color,100)};border-radius:12px;'
            f'background:{tint(color,30)};color:{color};font-size:22px;font-weight:800;')
        self.progress.setVisible(pct is not None);self.progress.setValue(pct or 0)
        self.progress.setStyleSheet(f'QProgressBar{{background:{theme.TRACK};border:none;border-radius:4px;}}'
                                    f'QProgressBar::chunk{{background:{color};border-radius:4px;}}')
        temp=data.get('temp');self.temp_badge.setText(f'{temp} °C' if temp is not None else '–')
        self.temp_badge.setStyleSheet(f'border:1px solid {theme.BORDER};border-radius:10px;'
                f'background:{tint(theme.accent(),22)};color:{theme.TEXT};font-size:23px;font-weight:800;')
        for key,(_,value,_) in self.fields.items():
            val=data.get(key)
            if val is None and key=='capacity':val=static.get('size')
            value.setText(self.format_field(key,val))
        attrs=data.get('attributes') or []
        self.table.setUpdatesEnabled(False);self.table.setRowCount(len(attrs))
        for r,attr in enumerate(attrs):
            values=(attr.get('id'),attr.get('name'),attr.get('current'),attr.get('worst'),
                    attr.get('threshold'),attr.get('raw'))
            for col,raw in enumerate(values):
                item=QTableWidgetItem(tr(str(raw)) if raw is not None else '–')
                item.setFlags(Qt.ItemIsEnabled)
                if col!=1:item.setTextAlignment(Qt.AlignCenter)
                if col==0:item.setForeground(QColor(theme.accent()))
                if attr.get('failed'):item.setForeground(QColor(theme.CRIT))
                self.table.setItem(r,col,item)
        self.table.setUpdatesEnabled(True)
        self.status.setText(tr('SMART-Daten werden beim Öffnen der Laufwerke geprüft.') if data.get('_pending')
                            else data.get('error') or (tr('Ausgelesen mit')+' '+data.get('source','smartctl')
                            if data else tr('Keine SMART-Daten verfügbar.')))
        message=('SMART-Prüfung wird beim Öffnen automatisch gestartet.' if data.get('_pending')
                 else data.get('error') if data.get('error') else
                 'Keine auslesbaren SMART-Attribute für dieses Laufwerk.'
                 if data and not attrs else 'Die Prozentanzeige beschreibt bei SSDs die gemeldete Restlebensdauer, nicht die Ausfallwahrscheinlichkeit. HDDs liefern meist keine Prozentangabe.')
        self.notes.setText(tr(message))

    def refresh_theme(self):
        self.table.setStyleSheet('QTableWidget{'
           f'background:{tint(theme.CARD,150)};color:{theme.TEXT};'
           f'border:1px solid {theme.BORDER};border-radius:10px;'
           f'alternate-background-color:{tint(theme.BORDER,55)};gridline-color:transparent;}}'
           f'QHeaderView::section{{background:{theme.CARD};color:{theme.MUTED};'
           f'border:none;border-bottom:1px solid {theme.BORDER};padding:7px;font-weight:700;}}')
        self.show_selected()

    def retranslate(self):
        self.table.setHorizontalHeaderLabels([tr(x) for x in HEADERS])
        for key,(lbl,_,title) in self.fields.items():lbl.setText(tr(title))
        self.health_label.setText(tr('Gesundheitszustand'));self.temp_label.setText(tr('Temperatur'))
        self.table_title.setText(tr('S.M.A.R.T.-Attribute'));self.show_selected()
