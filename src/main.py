"""Entry point for the automated wood-joining jig.

Boots a standalone Wi-Fi access point and starts the local control web
server. No internet connection and no external services are required.
"""

import network
import time
from webapp import app

AP_SSID = "wood-jig"
AP_PASSWORD = "jointech123"


def start_access_point():
    """Bring up the ESP32 access point so operators can connect directly."""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    while not ap.active():
        time.sleep(0.1)
    print("Access point ready:", ap.ifconfig())
    return ap


def main():
    start_access_point()
    print("Serving control interface at http://192.168.4.1")
    app.run(port=80)


if __name__ == "__main__":
    main()
