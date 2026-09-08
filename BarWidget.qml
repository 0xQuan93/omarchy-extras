pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Ui

Panel {
    id: root
    moduleName: "io.github.0xquan93.omarchy-extras"
    ipcTarget: "io.github.0xquan93.omarchy-extras"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    property int selected: 0
    readonly property var actions: [
        {label: "Setup guide & components ↗", url: "https://github.com/0xQuan93/omarchy-extras#optional-components"},
        {label: "Open local dashboard ↗", url: "http://127.0.0.1:8990"},
        {label: "Source & issue tracker ↗", url: "https://github.com/0xQuan93/omarchy-extras"}
    ]
    function activate(index) {
        root.close()
        Qt.openUrlExternally(actions[index].url)
    }
    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "Extras"
        horizontalMargin: 8
        tooltipText: "Omarchy Extras · desktop tools & setup"
        onPressed: function(buttonCode) {
            if (buttonCode === Qt.LeftButton) root.toggle()
        }
    }
    KeyboardPanel {
        id: popup
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        focusTarget: keys
        contentWidth: popup.fittedContentWidth(Style.space(340))
        contentHeight: popup.fittedContentHeight(content.implicitHeight)
        PanelKeyCatcher {
            id: keys
            anchors.fill: parent
            onCloseRequested: root.close()
            onTabRequested: function(direction) { root.selected = (root.selected + direction + root.actions.length) % root.actions.length }
            onMoveRequested: function(dx, dy) { if (dy) root.selected = (root.selected + dy + root.actions.length) % root.actions.length }
            onActivateRequested: root.activate(root.selected)
            Column {
                id: content
                width: parent.width
                spacing: Style.space(10)
                Text {
                    text: "OMARCHY EXTRAS"
                    color: root.barForeground
                    font.family: Style.fontFamily
                    font.pixelSize: Style.font.subtitle
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "A desktop collection, installed your way."
                    wrapMode: Text.WordWrap
                    color: root.barForeground
                    font.pixelSize: Style.font.body
                }
                Text {
                    width: parent.width
                    text: "Dashboard · reading room · weather · radio · Toonami · Wave Desk · notifications · Regalia ’89"
                    wrapMode: Text.WordWrap
                    color: root.barForeground
                    opacity: 0.75
                    font.pixelSize: Style.font.bodySmall
                }
                Repeater {
                    model: root.actions
                    Button {
                        required property var modelData
                        required property int index
                        width: content.width
                        text: (root.selected === index ? "› " : "  ") + modelData.label
                        foreground: root.barForeground
                        leftAlign: true
                        onClicked: root.activate(index)
                    }
                }
                Text {
                    width: parent.width
                    text: "The dashboard requires optional setup. Open the guide to choose components; this menu starts no services."
                    wrapMode: Text.WordWrap
                    color: root.barForeground
                    opacity: 0.65
                    font.pixelSize: Style.font.caption
                }
            }
        }
    }
}
