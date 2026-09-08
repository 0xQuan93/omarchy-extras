import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Ui as Ui
import qs.Commons

Ui.BarWidget {
  id: root
  moduleName: "oxquan.toonami"
  implicitWidth: vertical ? barSize : Style.space(104)
  implicitHeight: barSize
  property bool popupOpen: false
  property var stations: []
  property var player: ({selected: "east", playing: false, paused: false, fullscreen: false})
  property string message: ""
  property string guideMessage: "Loading station guide…"
  readonly property string helper: "@DATA@/toonami/toonami.py"
  function close() { popupOpen = false }
  function action(name, station) {
    if (control.running) return
    message = ""
    control.command = ["/usr/bin/python3", helper, name].concat(station ? [station] : [])
    control.running = true
  }
  onPopupOpenChanged: if (popupOpen && !guide.running) guide.running = true
  IpcHandler {
    target: "quan-toonami"
    function toggle(): void { root.popupOpen = !root.popupOpen }
    function status(): string { return JSON.stringify({stations: root.stations.length, player: root.player, error: root.message, guide: root.guideMessage, popup: root.popupOpen}) }
  }
  Process {
    id: guide
    command: ["/usr/bin/python3", root.helper, "guide"]
    running: true
    stdout: StdioCollector { onStreamFinished: {
      try { var data = JSON.parse(text); root.stations = data.stations || []; root.guideMessage = data.error || "" }
      catch (e) { root.guideMessage = "Guide unavailable · retry by reopening" }
    } }
  }
  Process {
    id: poll
    command: ["/usr/bin/python3", root.helper, "status"]
    running: true
    stdout: StdioCollector { onStreamFinished: { try { root.player = JSON.parse(text) } catch(e) {} } }
  }
  Process {
    id: control
    stdout: StdioCollector { onStreamFinished: {
      try { var data = JSON.parse(text); if (data.error) root.message = data.error; else root.player = data }
      catch(e) { root.message = "Player unavailable · try the official site" }
    } }
  }
  Timer { interval: 3000; running: true; repeat: true; onTriggered: if (!poll.running && !control.running) poll.running = true }
  Timer { interval: 60000; running: root.popupOpen; repeat: true; onTriggered: if (!guide.running) guide.running = true }
  Row {
    anchors.centerIn: parent
    spacing: Style.space(7)
    Image { source: "tom.svg"; width: Style.space(25); height: width; anchors.verticalCenter: parent.verticalCenter }
    Text { visible: !root.vertical; text: "TOONAMI"; color: root.bar.barForeground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; font.bold: true; anchors.verticalCenter: parent.verticalCenter }
    Rectangle { visible: root.player.playing; width: 4; height: 4; radius: 2; color: root.player.paused ? root.bar.barForeground : Color.accent; anchors.verticalCenter: parent.verticalCenter }
  }
  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: function(mouse) { if (mouse.button === Qt.RightButton) root.action("toggle"); else root.popupOpen = !root.popupOpen }
    onEntered: root.bar.showTooltip(root, "Toonami Aftermath · stations & viewing mode\nRight-click: pause / resume")
    onExited: root.bar.hideTooltip(root)
  }
  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(410))
    contentHeight: popup.fittedContentHeight(column.implicitHeight)
    Flickable {
      anchors.fill: parent
      contentHeight: column.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      Column {
        id: column
        width: parent.width
        spacing: Style.space(8)
        Row {
          spacing: Style.space(12)
          Image { source: "tom.svg"; width: Style.space(48); height: width }
          Column {
            spacing: 3
            Text { text: "TOONAMI AFTERMATH"; color: root.bar.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.subtitle; font.bold: true }
            Text { text: "ANIME / CLASSIC CARTOONS / ALL NIGHT"; color: Color.accent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption }
          }
        }
        PanelSeparator { foreground: root.bar.foreground }
        Text { width: parent.width; visible: text !== ""; text: root.message || root.guideMessage; color: root.bar.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.WordWrap; textFormat: Text.PlainText }
        Repeater {
          model: root.stations
          Rectangle {
            id: stationRow
            required property var modelData
            width: column.width
            height: texts.implicitHeight + Style.space(14)
            radius: Style.space(5)
            color: root.player.selected === modelData.key ? Qt.alpha(Color.accent, 0.16) : Qt.alpha(root.bar.foreground, 0.04)
            border.width: root.player.selected === modelData.key ? 1 : 0
            border.color: Color.accent
            Column {
              id: texts
              anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Style.space(10) }
              spacing: Style.space(3)
              Text { width: parent.width; text: stationRow.modelData.number + "  " + stationRow.modelData.name + (stationRow.modelData.gated ? " ↗" : ""); color: root.bar.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.bodySmall; font.bold: true; elide: Text.ElideRight; textFormat: Text.PlainText }
              Text { width: parent.width; text: stationRow.modelData.now; color: root.bar.foreground; opacity: 0.8; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; elide: Text.ElideRight; textFormat: Text.PlainText }
              Text { width: parent.width; visible: text !== ""; text: "NEXT  " + stationRow.modelData.next; color: Color.accent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; elide: Text.ElideRight; textFormat: Text.PlainText; height: stationRow.modelData.next ? implicitHeight : 0 }
            }
            MouseArea { anchors.fill: parent; enabled: !control.running; cursorShape: Qt.PointingHandCursor; onClicked: root.action("play", stationRow.modelData.key) }
          }
        }
        Row {
          spacing: Style.space(6)
          Button { text: "◀"; foreground: root.bar.foreground; enabled: !control.running; onClicked: root.action("previous") }
          Button { text: root.player.paused ? "Resume" : "Pause"; foreground: root.bar.foreground; enabled: root.player.playing && !control.running; onClicked: root.action("toggle") }
          Button { text: "▶"; foreground: root.bar.foreground; enabled: !control.running; onClicked: root.action("next") }
          Button { text: "Stop"; foreground: root.bar.foreground; enabled: root.player.playing && !control.running; onClicked: root.action("stop") }
        }
        PanelSeparator { foreground: root.bar.foreground }
        Text { text: "VIEW / " + (root.player.mode || "window").toUpperCase(); color: Color.accent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption }
        Row {
          spacing: Style.space(6)
          Repeater {
            model: [{name: "Window", mode: "window"}, {name: "Tile", mode: "tiled"}, {name: "Mini ↘", mode: "mini"}, {name: "Fullscreen", mode: "fullscreen"}]
            Button {
              required property var modelData
              text: modelData.name
              foreground: root.bar.foreground
              enabled: !control.running
              onClicked: { root.action(modelData.mode); root.close() }
            }
          }
        }
        Row {
          spacing: Style.space(6)
          Button { text: "Smaller"; foreground: root.bar.foreground; enabled: !control.running; onClicked: root.action("smaller") }
          Button { text: "Larger"; foreground: root.bar.foreground; enabled: !control.running; onClicked: root.action("larger") }
          Button { text: "Corner ↻"; foreground: root.bar.foreground; enabled: !control.running; onClicked: root.action("corner") }
        }
        Text { width: parent.width; text: "Mini: " + (root.player.miniWidth || 320) + "px · " + (root.player.corner || "bottom-right") + " · all workspaces"; color: root.bar.foreground; opacity: 0.7; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption }

        Button { width: column.width; text: "Official site / chat ↗"; foreground: root.bar.foreground; enabled: !control.running; onClicked: root.action("site") }
        Text { width: parent.width; text: "Super + drag: move · Super + right-drag: resize\nSuper + O: float / pin · Super + F: fullscreen\nSpace: pause · PgUp / PgDn: channels · Q: close"; color: root.bar.foreground; opacity: 0.7; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.WordWrap }
      }
    }
  }
}
