import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "oxquan.home"
  property string readout: "⌂  Quan"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Process {
    id: stats
    command: ["/usr/bin/python", "-c", "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8990/api/machine',timeout=2)); print('⌂  Quan  ·  '+str(round(d['ramUsed']/1073741824,1))+'G')"]
    running: true
    stdout: StdioCollector {
      onStreamFinished: if (text.trim()) root.readout = text.trim()
    }
  }
  Timer { interval: 15000; running: true; repeat: true; onTriggered: if (!stats.running) stats.running = true }
  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    horizontalMargin: 12
    text: root.vertical ? "⌂" : root.readout
    tooltipText: "Quan Home · agents, local AI, weather & news"
    onPressed: if (root.bar) root.bar.run("omarchy launch webapp http://127.0.0.1:8990")
  }
}
