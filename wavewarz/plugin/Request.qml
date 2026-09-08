import QtQuick
import Quickshell.Io

Item {
    id: root
    property string path: "/health"
    property string method: "GET"
    property bool busy: proc.running
    signal received(var data)
    function run() { if (!proc.running) proc.running = true }
    Process {
        id: proc
        command: ["curl", "-fsS", "--max-time", "100", "-X", root.method, "http://127.0.0.1:8991" + root.path]
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.received(JSON.parse(text)) }
                catch(e) { root.received({error: "Wave Desk unavailable · reconnecting", stale: true}) }
            }
        }
    }
}
