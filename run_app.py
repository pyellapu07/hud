"""
Personal OS — native desktop window (no browser needed).
Uses pywebview to render the dashboard as a real app window.
"""
import webview
import os
import json

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, 'index.html')
POS_FILE  = os.path.join(BASE_DIR, 'win_position.json')


def load_pos():
    if os.path.exists(POS_FILE):
        try:
            with open(POS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_pos(x, y, w, h):
    with open(POS_FILE, 'w') as f:
        json.dump({'x': x, 'y': y, 'w': w, 'h': h}, f)


class App:
    def __init__(self, window):
        self.window = window

    def on_closed(self):
        try:
            save_pos(
                self.window.x, self.window.y,
                self.window.width, self.window.height
            )
        except Exception:
            pass


pos = load_pos()

window = webview.create_window(
    title      = 'Personal OS',
    url        = f'file:///{HTML_FILE.replace(os.sep, "/")}',
    width      = pos.get('w', 1280),
    height     = pos.get('h', 820),
    x          = pos.get('x', None),
    y          = pos.get('y', None),
    resizable  = True,
    min_size   = (900, 600),
    text_select= True,
)

app = App(window)
window.events.closed += app.on_closed

webview.start(debug=False)
