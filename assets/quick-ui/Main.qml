import QtQuick 2.15

// Standalone QQuickView: the entire visible interface uses Qt Quick's scene
// graph. No QWidget surfaces, QQuickWidget or Canvas textures are embedded.
Rectangle {
    id: root
    width: 1250
    height: 850
    color: pal.bg
    property var pal: telemetry.palette
    property var m: telemetry.metrics
    property int currentPage: 0
    property var sections: ["Übersicht", "Prozessor", "Grafik",
                            "Arbeitsspeicher", "Netzwerk", "System", "Info"]
    property var subtitles: [
        "Dein Linux-System auf einen Blick",
        "Prozessorauslastung und Sensordaten",
        "Grafikkarte und Live-Auslastung",
        "Arbeitsspeicher und Auslastung",
        "Aktuelle Netzwerkübertragung",
        "Betriebssystem und Laufzeit",
        "Experimentelle GPU-Oberfläche"
    ]
    readonly property color dimAccent: Qt.rgba(0.35, 0.56, 1.0, 0.10)

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.pal.bg }
            GradientStop { position: 1.0; color: root.pal.sidebar }
        }
    }

    Row {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: side
            width: 246
            height: parent.height
            color: root.pal.sidebar
            border.color: root.pal.border
            border.width: 1

            Column {
                width: parent.width - 32
                x: 16
                y: 22
                spacing: 14

                Item {
                    width: parent.width
                    height: 160
                    Image {
                        id: mark
                        width: 106
                        height: 106
                        anchors.horizontalCenter: parent.horizontalCenter
                        source: "../vitalux.svg"
                        fillMode: Image.PreserveAspectFit
                        sourceSize.width: 212
                        sourceSize.height: 212
                        asynchronous: true
                    }
                    Text {
                        anchors.top: mark.bottom
                        anchors.topMargin: 8
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "VITALUX"
                        color: root.pal.accent
                        font.pixelSize: 23
                        font.bold: true
                        font.letterSpacing: 3
                    }
                }
                Text {
                    text: "GPU-OBERFLÄCHE · TEST"
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    color: root.pal.muted
                    font.pixelSize: 10
                    font.letterSpacing: 1.4
                }

                Repeater {
                    model: root.sections
                    delegate: Rectangle {
                        id: navigation
                        width: side.width - 32
                        height: 45
                        radius: 10
                        color: root.currentPage === index ? root.dimAccent : "transparent"
                        border.color: root.currentPage === index ? root.pal.accent : "transparent"
                        border.width: 1

                        Text {
                            text: modelData
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            color: root.currentPage === index ? root.pal.accent : root.pal.text
                            font.pixelSize: 13
                            font.bold: root.currentPage === index
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.currentPage = index
                                details.contentY = 0
                            }
                        }
                    }
                }
            }

            Text {
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 20
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Vorschau · keine stabile Version"
                color: root.pal.muted
                font.pixelSize: 10
            }
        }

        Item {
            id: workspace
            width: parent.width - side.width
            height: parent.height

            Rectangle {
                id: topbar
                height: 87
                width: parent.width
                color: "transparent"
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: root.pal.border
                    opacity: 0.65
                }
                Column {
                    x: 28
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5
                    Text {
                        text: root.sections[root.currentPage]
                        color: root.pal.text
                        font.pixelSize: 25
                        font.bold: true
                    }
                    Text {
                        text: root.subtitles[root.currentPage]
                        color: root.pal.muted
                        font.pixelSize: 12
                    }
                }
                Rectangle {
                    width: 176
                    height: 29
                    radius: 14
                    color: root.dimAccent
                    border.color: root.pal.border
                    anchors.right: parent.right
                    anchors.rightMargin: 26
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        anchors.centerIn: parent
                        text: "●  GPU · Qt Quick"
                        color: root.pal.accent
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
            }

            Flickable {
                id: details
                anchors.top: topbar.bottom
                anchors.bottom: parent.bottom
                width: parent.width
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: width
                contentHeight: contents.implicitHeight + 66

                Column {
                    id: contents
                    width: details.width - 56
                    x: 28
                    y: 24
                    spacing: 17

                    Rectangle {
                        width: contents.width
                        height: 80
                        radius: 14
                        color: root.dimAccent
                        border.color: root.pal.border
                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 18
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 36
                            text: root.m.status
                            color: root.pal.text
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                    }

                    // These metric cards consist solely of GPU scene-graph
                    // rectangles, gradients and text nodes.
                    Grid {
                        id: metricRow
                        visible: root.currentPage === 0
                        width: contents.width
                        columns: width < 770 ? 2 : 4
                        height: visible ? (columns === 2 ? 322 : 155) : 0
                        spacing: 12
                        Repeater {
                            model: 4
                            delegate: Rectangle {
                                width: (metricRow.width - (metricRow.columns - 1) * metricRow.spacing) / metricRow.columns
                                height: 155
                                radius: 14
                                color: root.pal.card
                                border.color: root.pal.border
                                property var itemValue: index === 0 ? root.m.cpuUsage
                                        : index === 1 ? root.m.gpuUsage
                                        : index === 2 ? root.m.ramUsage : 0
                                property string itemTitle: ["CPU", "GPU", "RAM", "SYSTEM"][index]
                                property string itemText: index === 3 ? root.m.uptime :
                                                           Number(itemValue).toFixed(0) + " %"
                                Text {
                                    x: 18; y: 18
                                    color: root.pal.muted
                                    text: itemTitle
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Text {
                                    x: 18; y: 46
                                    color: root.pal.text
                                    text: itemText
                                    font.pixelSize: index === 3 ? 22 : 32
                                    font.bold: true
                                }
                                Rectangle {
                                    visible: index < 3
                                    x: 18; y: 116
                                    width: parent.width - 36
                                    height: 9
                                    radius: 5
                                    color: root.pal.border
                                    Rectangle {
                                        width: parent.width * Math.max(0, Math.min(100, Number(itemValue))) / 100
                                        height: parent.height
                                        radius: parent.radius
                                        color: root.pal.accent
                                        Behavior on width {
                                            NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: mainCard
                        visible: root.currentPage !== 6
                        width: contents.width
                        height: visible ? (root.currentPage === 0 ? 237 : 280) : 0
                        radius: 16
                        color: root.pal.card
                        border.color: root.pal.border
                        Column {
                            x: 22; y: 20
                            width: parent.width - 44
                            spacing: 18
                            Text {
                                color: root.pal.accent
                                font.pixelSize: 13
                                font.bold: true
                                text: root.currentPage <= 1 ? "PROZESSOR"
                                      : root.currentPage === 2 ? "GRAFIK"
                                      : root.currentPage === 3 ? "ARBEITSSPEICHER"
                                      : root.currentPage === 4 ? "NETZWERK" : "SYSTEM"
                            }
                            Text {
                                width: parent.width
                                elide: Text.ElideRight
                                color: root.pal.text
                                font.pixelSize: 19
                                font.bold: true
                                text: root.currentPage <= 1 ? root.m.cpuModel
                                      : root.currentPage === 2 ? root.m.gpuModel
                                      : root.currentPage === 3 ? "Physischer Arbeitsspeicher"
                                      : root.currentPage === 4 ? "Netzwerkschnittstellen"
                                      : root.m.system
                            }
                            Text {
                                color: root.pal.muted
                                font.pixelSize: 14
                                text: root.currentPage <= 1 ? "Auslastung  " + root.m.cpuUsage.toFixed(1) + " %    ·    Temperatur  " + root.m.cpuTemp
                                      : root.currentPage === 2 ? "Auslastung  " + root.m.gpuUsage.toFixed(1) + " %    ·    Temperatur  " + root.m.gpuTemp + "    ·    Takt  " + root.m.gpuClock
                                      : root.currentPage === 3 ? root.m.ramUsed + " von " + root.m.ramTotal
                                      : root.currentPage === 4 ? "Download  " + root.m.netDown + "    ·    Upload  " + root.m.netUp
                                      : "Kernel " + root.m.kernel
                            }
                            Rectangle {
                                width: parent.width
                                height: 78
                                radius: 11
                                color: root.pal.sidebar
                                border.color: root.pal.border
                                Row {
                                    id: chartBars
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    anchors.topMargin: 10
                                    anchors.bottomMargin: 10
                                    spacing: 3
                                    Repeater {
                                        model: root.m.cpuHistory
                                        delegate: Rectangle {
                                            width: Math.max(2, (chartBars.width - (root.m.cpuHistory.length - 1) * chartBars.spacing) / Math.max(1, root.m.cpuHistory.length))
                                            height: Math.max(3, chartBars.height * Number(modelData) / 100)
                                            y: chartBars.height - height
                                            radius: 2
                                            color: root.pal.accent
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: contents.width
                        height: 145
                        radius: 14
                        color: root.pal.card
                        border.color: root.pal.border
                        visible: root.currentPage !== 6
                        Column {
                            x: 22; y: 22
                            width: parent.width - 44
                            spacing: 13
                            Text {
                                text: "LIVE-HARDWAREDATEN"
                                font.pixelSize: 12
                                color: root.pal.accent
                                font.bold: true
                            }
                            Text {
                                width: parent.width
                                color: root.pal.text
                                elide: Text.ElideRight
                                text: "CPU: " + root.m.cpuModel + "   ·   GPU: " + root.m.gpuModel
                                font.pixelSize: 13
                            }
                            Text {
                                color: root.pal.muted
                                text: "RAM " + root.m.ramUsed + " / " + root.m.ramTotal + "   ·   Laufzeit " + root.m.uptime
                                font.pixelSize: 13
                            }
                        }
                    }

                    Rectangle {
                        visible: root.currentPage === 6
                        height: visible ? 248 : 0
                        width: contents.width
                        color: root.pal.card
                        border.color: root.pal.border
                        radius: 16
                        Column {
                            width: parent.width - 48
                            x: 24; y: 24; spacing: 15
                            Text {
                                text: "Made by PAAAUUULLOOOH"
                                color: root.pal.accent
                                font.pixelSize: 27
                                font.bold: true
                            }
                            Text {
                                width: parent.width
                                text: "Danke an TimBooH für die Unterstützung bei Hintergrundbildern und Grafikdarstellung."
                                color: root.pal.accent
                                font.pixelSize: 14
                                font.bold: true
                                wrapMode: Text.Wrap
                            }
                            Text {
                                width: parent.width
                                text: "Diese native GPU-Oberfläche ist ein Entwicklungstest. Nicht alle Funktionen der stabilen Anwendung wurden bereits übertragen."
                                color: root.pal.muted
                                font.pixelSize: 13
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    Text {
                        width: contents.width
                        wrapMode: Text.Wrap
                        color: root.pal.muted
                        font.pixelSize: 11
                        text: "Experimentelle Qt-Quick-Oberfläche · Diese Vorschau enthält noch keinen Benchmark, keine Laufwerksverwaltung und keine Einstellungsseite."
                    }
                }
            }
        }
    }
}
