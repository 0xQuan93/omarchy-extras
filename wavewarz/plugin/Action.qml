import QtQuick
import qs.Commons

Rectangle {
    id: root
    property string text: ""
    signal clicked()
    implicitHeight: 32
    implicitWidth: label.implicitWidth + 24
    radius: 7
    color: area.containsMouse ? Qt.alpha(Color.accent, 0.25) : Qt.alpha(Color.accent, 0.12)
    opacity: enabled ? 1 : 0.5
    Text { id: label; anchors.centerIn: parent; text: root.text; textFormat: Text.PlainText; color: Color.accent; font.family: Style.fontFamily; font.pixelSize: 12 }
    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
