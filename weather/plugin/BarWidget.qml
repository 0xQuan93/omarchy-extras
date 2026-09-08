import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "omarchy.weather"
  property string temperature: "—°"
  property string details: "Weather unavailable"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Process {
    id: weather
    command: ["/usr/bin/python", "-c", "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8990/api/weather',timeout=35).read().decode())"]
    running: true
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var data = JSON.parse(text)
          if (!data.current || typeof data.current.temperature_2m !== "number") throw new Error("No weather")
          root.temperature = Math.round(data.current.temperature_2m) + "°"
          root.details = data.place + " · " + data.units.temperature_2m
        } catch (error) {
          root.temperature = "—°"
          root.details = "Weather unavailable · choose your city in Quan Home"
        }
      }
    }
    onExited: function(exitCode, exitStatus) {
      if (exitCode !== 0) {
        root.temperature = "—°"
        root.details = "Weather unavailable · click to open Quan Home"
      }
    }
  }
  Timer {
    interval: 60000
    running: true
    repeat: true
    onTriggered: if (!weather.running) weather.running = true
  }
  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.temperature
    horizontalMargin: 10
    tooltipText: root.details
    onPressed: if (root.bar) root.bar.run("omarchy launch webapp http://127.0.0.1:8990")
  }
}
