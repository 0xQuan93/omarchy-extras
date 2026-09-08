import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons

Item {
    id: root
    property var report: ({battles: [], events: []})
    property var recap: ({status: "idle", text: ""})
    property string connectionError: ""
    property bool showRecap: false
    function refresh() { feed.run(); summary.run() }
    Request {
        id: feed; path: "/wave"
        onReceived: function(data) {
            if (data.battles) { root.report = data; root.connectionError = "" }
            else root.connectionError = data.error || "Feed unavailable"
        }
    }
    Request { id: summary; path: "/summary"; onReceived: function(data) { if (data.status) root.recap = data } }
    Request { id: generate; path: "/summary"; method: "POST"; onReceived: function(data) { root.recap = data.status ? data : {status:"error", error:data.error, text:""} } }
    Timer { interval: 60000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }
    Timer { interval: 2000; running: root.recap.status === "running"; repeat: true; onTriggered: summary.run() }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            required property var modelData
            screen: modelData
            anchors { top: true; right: true }
            margins { top: 380; right: 34 }
            implicitWidth: Math.min(390, modelData.width - 50)
            implicitHeight: Math.max(200, Math.min(430, modelData.height - 420))
            color: "transparent"
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: "oxquan-wavewarz"
            WlrLayershell.layer: WlrLayer.Bottom
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            Rectangle {
                anchors.fill: parent; radius: Style.cornerRadius
                color: Color.popups.background; border.color: Color.popups.border
                Column {
                    anchors.fill: parent; anchors.margins: 20; spacing: 10
                    Row {
                        width: parent.width
                        Text { text: "≋  WAVE DESK"; color: Color.accent; font.family: Style.fontFamily; font.pixelSize: 14; font.bold: true; width: parent.width - 65 }
                        Text { text: "Wave Desk"; color: Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 12 }
                    }
                    Text {
                        width: parent.width; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                        text: root.connectionError || (root.report.stale ? "STALE · retrying feed" : "Refreshes every minute") + (root.report.fetchedAt ? " · " + Qt.formatDateTime(new Date(root.report.fetchedAt), "HH:mm") : " · connecting…")
                        color: root.connectionError || root.report.stale ? "#e9b76d" : Color.popups.text
                        opacity: 0.75; font.pixelSize: 10; font.family: Style.fontFamily
                    }
                    Row {
                        spacing: 8
                        Action { text: root.showRecap ? "Battles" : "Local AI recap"; onClicked: { root.showRecap = !root.showRecap; if (root.showRecap && root.recap.status === "idle") { root.recap = {status:"running",text:""}; generate.run() } } }
                        Action { text: root.showRecap ? "New recap" : "WaveWarZ ↗"; enabled: !root.showRecap || (root.recap.status !== "running" && !generate.busy); onClicked: { if (root.showRecap) { root.recap = {status:"running",text:""}; generate.run() } else Qt.openUrlExternally("https://wavewarz.info/battles") } }
                    }
                    Flickable {
                        width: parent.width; height: parent.height - y; clip: true
                        contentHeight: body.implicitHeight; boundsBehavior: Flickable.StopAtBounds
                        Column {
                            id: body; width: parent.width; spacing: 12
                            Text {
                                visible: root.showRecap; width: parent.width; wrapMode: Text.Wrap; textFormat: Text.PlainText
                                text: root.recap.status === "running" ? "Your local AI is reading the latest battles…" : (root.recap.error || root.recap.text || "Choose New recap to get started.")
                                color: Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 13; lineHeight: 1.25
                            }
                            Text {
                                visible: root.showRecap && root.recap.status === "ready"; width: parent.width; wrapMode: Text.Wrap
                                text: "AI-generated · " + (root.recap.generatedAt ? Qt.formatDateTime(new Date(root.recap.generatedAt), "MMM d HH:mm") : "") + (root.recap.truncated ? " · output limit reached" : "") + "\nLatest 6 battles + 3 events. Check results in the battle list."
                                color: Color.accent; font.pixelSize: 10; font.family: Style.fontFamily
                            }
                            Text { visible: !root.showRecap && !root.report.battles.length; text: "Waiting for battle data…"; color: Color.popups.text; font.pixelSize: 12 }
                            Repeater {
                                model: root.showRecap ? [] : root.report.battles.slice(0, 8)
                                Column {
                                    required property var modelData
                                    width: body.width; spacing: 4
                                    Text { width: parent.width; text: (modelData.live ? "● LIVE · " : "") + modelData.title; textFormat: Text.PlainText; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight; color: modelData.live ? Color.accent : Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 13; font.bold: true }
                                    Text { width: parent.width; text: modelData.label + " · " + modelData.result; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.accent; font.pixelSize: 11; font.family: Style.fontFamily }
                                    Text { text: (modelData.at ? Qt.formatDateTime(new Date(modelData.at), "MMM d HH:mm") : "Date unavailable") + "  ·  View ↗"; color: Color.popups.text; opacity: 0.6; font.pixelSize: 10; MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Qt.openUrlExternally(modelData.url) } }
                                    Rectangle { width: parent.width; height: 1; color: Color.popups.border }
                                }
                            }
                            Text { visible: !root.showRecap; width: parent.width; text: root.report.profileNote || ""; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.popups.text; opacity: 0.6; font.pixelSize: 10 }
                        }
                    }
                }
            }
        }
    }
}
