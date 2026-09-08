import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons

Item {
  id: root
  property var reading: ({title: "Wanderer’s Desk", kind: "A DAILY PRACTICE IN CURIOSITY", description: "Consciousness, hidden histories, sound, and possible futures."})
  Process {
    id: content
    command: ["/usr/bin/python3", "@DATA@/dashboard/wanderer/daily.py"]
    running: true
    stdout: StdioCollector { onStreamFinished: { try { root.reading = JSON.parse(text) } catch(e) {} } }
  }
  Timer { interval: 60000; running: true; repeat: true; onTriggered: if (!content.running) content.running = true }
  Process { id: launch; command: ["/usr/bin/python3", "@DATA@/dashboard/wanderer/toggle.py"] }
  Variants {
    model: Quickshell.screens
    PanelWindow {
      required property var modelData
      screen: modelData
      anchors { top: true; right: true }
      margins { top: 90; right: 34 }
      implicitWidth: Math.min(390, modelData.width - 50)
      implicitHeight: 270
      color: "transparent"
      exclusionMode: ExclusionMode.Ignore
      WlrLayershell.namespace: "oxquan-wanderer"
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      Rectangle {
        anchors.fill: parent
        radius: Style.cornerRadius
        color: Color.popups.background
        border.color: Color.popups.border
        Column {
          anchors.fill: parent
          anchors.margins: 24
          spacing: 13
          Text { text: "✦   WANDERER’S DESK"; color: Color.accent; font.family: Style.fontFamily; font.pixelSize: 11; font.letterSpacing: 2 }
          Text { width: parent.width; text: root.reading.title; color: Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 25; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
          Text { width: parent.width; text: root.reading.description; color: Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 13; wrapMode: Text.WordWrap; maximumLineCount: 4; elide: Text.ElideRight }
          Text { text: "CLICK TO OPEN ↗"; color: Color.accent; font.family: Style.fontFamily; font.pixelSize: 10 }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: if (!launch.running) launch.running = true }
      }
    }
  }
}
