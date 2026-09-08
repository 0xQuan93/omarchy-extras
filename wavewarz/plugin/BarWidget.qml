import QtQuick
import QtQuick.Controls as Controls
import qs.Commons
import qs.Ui

Panel {
    id: root
    moduleName: "oxquan.wavewarz"
    ipcTarget: "oxquan.wavewarz"
    property var quotes: ({data:{}})
    property var coins: []
    property var selected: null
    property string detail: "Search by coin name or symbol"
    property string activeQuery: ""
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function dollars(value) {
        return typeof value === "number" ? "$" + value.toLocaleString(Qt.locale("en_US"), 'f', value < 1 ? 6 : 2) : "—"
    }
    function price(id) { return dollars((root.quotes.data[id] || {}).usd) }
    function compactPrice(id) {
        var value = (root.quotes.data[id] || {}).usd
        if (typeof value !== "number") return "—"
        return value >= 1000 ? (value / 1000).toFixed(2) + "k" : value.toFixed(1)
    }
    function stale() {
        return root.quotes.stale || ["solana", "ethereum"].some(function(id) {
            var q = root.quotes.data[id]; return !q || !q.last_updated_at || Date.now()/1000 - q.last_updated_at > 600
        })
    }
    function lookup() {
        if (search.busy) return
        root.activeQuery = field.text.trim()
        search.path = "/search?q=" + encodeURIComponent(root.activeQuery)
        search.run()
    }
    Request { id: prices; path: "/prices"; onReceived: function(data) { if (data.data) root.quotes = data; else root.quotes = {data:root.quotes.data, stale:true} } }
    Request {
        id: search
        onReceived: function(data) {
            if (root.activeQuery === field.text.trim()) { root.coins = data.coins || []; root.detail = data.error || (root.coins.length ? "Select a coin for its USD price" : "No matches") }
            else retry.restart()
        }
    }
    Request {
        id: selectedPrice
        onReceived: function(data) {
            var quote = data.data ? data.data[root.selected.id] : null
            root.detail = quote ? root.selected.name + " · " + root.dollars(quote.usd) + (typeof quote.usd_24h_change === "number" ? " · " + quote.usd_24h_change.toFixed(2) + "% / 24h" : "") + (data.stale ? " · STALE" : "") : (data.error || "Price unavailable")
        }
    }
    Timer { interval: 120000; running: true; repeat: true; triggeredOnStart: true; onTriggered: prices.run() }
    Timer { id: retry; interval: 450; onTriggered: root.lookup() }
    WidgetButton {
        id: button; anchors.fill: parent; bar: root.bar
        text: "SOL " + root.compactPrice("solana") + " · ETH " + root.compactPrice("ethereum") + (root.stale() ? " ~" : "")
        horizontalMargin: 6
        tooltipText: "SOL " + root.price("solana") + " · ETH " + root.price("ethereum") + "\nCoinGecko · USD · every 2 min" + (root.stale() ? " · stale/unavailable" : "") + "\nClick to search coins"
        onPressed: root.toggle()
    }
    KeyboardPanel {
        id: popup; anchorItem: button; owner: root; bar: root.bar; open: root.opened
        focusTarget: field
        contentWidth: popup.fittedContentWidth(390)
        contentHeight: popup.fittedContentHeight(content.implicitHeight)
        Column {
            id: content; width: parent.width; spacing: 12
            Row {
                width: parent.width
                Text { text: "CRYPTO / USD"; color: Color.accent; font.family: Style.fontFamily; font.bold: true; width: parent.width - 70; anchors.verticalCenter: parent.verticalCenter }
                Action { text: "Close"; onClicked: root.close() }
            }
            Text { text: "SOL " + root.price("solana") + "    ETH " + root.price("ethereum"); color: Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 19 }
            Text { width: parent.width; wrapMode: Text.Wrap; text: (root.stale() ? "Stale / unavailable · " : "") + "CoinGecko · refreshes every 2 minutes"; color: Color.popups.text; opacity: 0.6; font.pixelSize: 11 }
            Controls.TextField {
                id: field; width: parent.width; placeholderText: "Search coins… e.g. JUP, BONK, Bitcoin"
                color: Color.popups.text; placeholderTextColor: Qt.alpha(Color.popups.text, 0.5)
                background: Rectangle { radius: 7; color: Qt.alpha(Color.accent, 0.08); border.color: Color.popups.border }
                onTextChanged: { root.coins = []; if (text.trim().length >= 2) retry.restart(); else { retry.stop(); root.detail = "Search by coin name or symbol" } }
                onAccepted: root.lookup()
                Keys.onEscapePressed: root.close()
            }
            Text { width: parent.width; text: search.busy ? "Searching…" : root.detail; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.accent; font.pixelSize: 12; font.family: Style.fontFamily }
            Repeater {
                model: root.coins
                Action {
                    required property var modelData
                    width: content.width
                    text: String(modelData.symbol).toUpperCase() + " · " + modelData.name.slice(0, 28) + " · #" + (modelData.market_cap_rank || "—")
                    enabled: !selectedPrice.busy
                    onClicked: { root.selected = modelData; root.detail = "Loading price…"; selectedPrice.path = "/prices?ids=" + encodeURIComponent(modelData.id); selectedPrice.run() }
                }
            }
            Text { text: "Prices by CoinGecko ↗"; color: Color.popups.text; opacity: 0.6; font.pixelSize: 10; MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Qt.openUrlExternally("https://www.coingecko.com") } }
        }
    }
}
