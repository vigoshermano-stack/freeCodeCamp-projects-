"""Local-first web interface for the wood-joining jig.

Uses Microdot, a MicroPython web framework with Flask-style routing.
Note: Flask itself does not run on MicroPython microcontrollers; Microdot
provides the same developer experience on constrained hardware.
"""

from microdot import Microdot
from motion import home, move_to, layout_positions
import time

app = Microdot()

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wood-Joining Jig</title>
</head>
<body>
  <h1>Wood-Joining Jig</h1>
  <form method="post">
    <label>Number of joints: <input name="count" type="number" value="4" required></label><br>
    <label>Spacing (mm): <input name="spacing" type="number" step="0.1" value="40" required></label><br>
    <label>Edge offset (mm): <input name="offset" type="number" step="0.1" value="60" required></label><br>
    <button type="submit">Run layout</button>
  </form>
</body>
</html>"""


@app.route("/")
async def index(request):
    if request.method == "POST":
        count = int(request.form["count"])
        spacing = float(request.form["spacing"])
        offset = float(request.form["offset"])
        home()
        for position in layout_positions(count, spacing, offset):
            move_to(position)
            time.sleep(1)  # pause for the operator to cut
        return "Layout complete. Return to the form to run another."
    return PAGE, 200, {"Content-Type": "text/html"}
