import QtQuick

Item {
    id: backdrop
    property int generation: 0

    Image {
        anchors.fill: parent
        source: "image://vitaluxwallpaper/backdrop/" + backdrop.generation
        cache: false
        asynchronous: false
        fillMode: Image.Stretch
        smooth: false
    }
}
