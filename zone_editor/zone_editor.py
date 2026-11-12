#!/usr/bin/env python3
"""Buggy Zone Editor - a tiny browser UI for editing ZONE2DIST and ZONE_MAP.

Run on the PC (NOT on the Pico):

    python3 zone_editor/zone_editor.py            # edits ../config.py
    python3 zone_editor/zone_editor.py path/to/config.py

A browser tab opens. When you click "Save", only the ZONE2DIST and ZONE_MAP
assignments inside config.py are rewritten; every other line is left exactly
as it was. A backup (config.py.bak) is written first.

config.py imports Pico-only modules, so it is never imported here. Instead
it is parsed with the `ast` module and the two assignments are read
symbolically (names like ZONE_1, MTR_FWD, KPRB.RED).
"""

import ast
import json
import os
import shutil
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "..", "config.py")
HOST, PORT = "127.0.0.1", 8765

ZONES = ["ZONE_1", "ZONE_2", "ZONE_3", "ZONE_4"]
COLORS = ["BLACK", "RED", "YELLOW", "GREEN", "CYAN", "BLUE", "PURPLE", "WHITE"]
DIRS = ["MTR_FWD", "MTR_REV"]
MAX_INCHES = 150  # the ultrasonic sensor can't see much further than ~4 m


class ConfigError(Exception):
    pass


# --------------------------------------------------------------------------
# Reading config.py
# --------------------------------------------------------------------------
def _sym(node):
    """Evaluate a literal-ish AST node, keeping names symbolic."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_sym(node.operand)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.attr  # KPRB.RED -> "RED"
    if isinstance(node, ast.Subscript):  # ZONE2DIST[ZONE_1]
        return ("SUB", _sym(node.value), _sym(node.slice))
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_sym(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_sym(k): _sym(v) for k, v in zip(node.keys, node.values)}
    raise ConfigError(f"line {node.lineno}: don't understand {ast.unparse(node)!r}")


def _find_assignments(source):
    tree = ast.parse(source)
    found = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in ("ZONE2DIST", "ZONE_MAP")):
            found[node.targets[0].id] = node
    for name in ("ZONE2DIST", "ZONE_MAP"):
        if name not in found:
            raise ConfigError(f"could not find {name} in config.py")
    return found


def _direction(v):
    # Accept the symbolic names, or the raw letters "f"/"r" if typed by hand.
    v = {"f": "MTR_FWD", "r": "MTR_REV"}.get(v, v)
    if v not in DIRS:
        raise ConfigError(f"unknown motor direction {v!r}")
    return v


def _color(v):
    if v not in COLORS:
        raise ConfigError(f"unknown LED color {v!r}")
    return v


def _speed(v):
    if not isinstance(v, int) or not 0 <= v <= 100:
        raise ConfigError(f"motor speed {v!r} must be a whole number 0-100")
    return v


def read_config(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    nodes = _find_assignments(source)

    z2d = _sym(nodes["ZONE2DIST"].value)
    zones = []
    for z in ZONES:
        if z not in z2d:
            raise ConfigError(f"ZONE2DIST is missing {z}")
        lo, hi = z2d[z]
        zones.append([lo, hi])

    zmap = _sym(nodes["ZONE_MAP"].value)
    if len(zmap) != len(ZONES):
        raise ConfigError(f"ZONE_MAP must have {len(ZONES)} front-zone entries")
    front_colors, back_colors, motors = [], [None] * len(ZONES), []
    for f, front in enumerate(zmap):
        front_colors.append(_color(front["LED_COLOR"]))
        backs = front["CAR_BACK"]
        if len(backs) != len(ZONES):
            raise ConfigError(f"ZONE_MAP[{f}] must have {len(ZONES)} back-zone entries")
        row = []
        for b, back in enumerate(backs):
            if back_colors[b] is None:  # back color is per back-zone
                back_colors[b] = _color(back["LED_COLOR"])
            row.append({
                "left": [_direction(back["MTR_LEFT"][0]), _speed(back["MTR_LEFT"][1])],
                "right": [_direction(back["MTR_RIGHT"][0]), _speed(back["MTR_RIGHT"][1])],
            })
        motors.append(row)

    return {"zones": zones, "frontColors": front_colors,
            "backColors": back_colors, "motors": motors,
            "path": os.path.abspath(path)}


# --------------------------------------------------------------------------
# Validating (the browser checks too, but the file is what matters)
# --------------------------------------------------------------------------
def validate(data):
    """Check the zone rules; return normalised zones (unused ones filled in)."""
    zones = data["zones"]
    if len(zones) != len(ZONES):
        raise ConfigError("need exactly 4 zones")
    out = []
    lo = 0
    last = None
    for i, (_, hi) in enumerate(zones):
        if last is not None:  # zone after the "no limit" zone: unused
            out.append([last, -1])
            continue
        if not isinstance(hi, int):
            raise ConfigError(f"{ZONES[i]} max must be a whole number")
        if i == len(ZONES) - 1:
            hi = -1  # the final zone always reaches to infinity
        if hi != -1 and not (lo < hi <= MAX_INCHES):
            raise ConfigError(f"{ZONES[i]} max must be between {lo + 1} and {MAX_INCHES}")
        out.append([lo, hi])
        if hi == -1:
            last = lo
        else:
            lo = hi

    for name in ("frontColors", "backColors"):
        if len(data[name]) != len(ZONES):
            raise ConfigError(f"{name} needs 4 colors")
        for c in data[name]:
            _color(c)
    if len(data["motors"]) != len(ZONES):
        raise ConfigError("motors needs 4 rows")
    for row in data["motors"]:
        if len(row) != len(ZONES):
            raise ConfigError("each motors row needs 4 cells")
        for cell in row:
            for side in ("left", "right"):
                _direction(cell[side][0])
                _speed(cell[side][1])
    return out


# --------------------------------------------------------------------------
# Writing config.py
# --------------------------------------------------------------------------
def gen_zone2dist(zones):
    lines = []
    for i, (lo, hi) in enumerate(zones):
        prefix = "ZONE2DIST = {" if i == 0 else " " * 13
        end = "}" if i == len(zones) - 1 else ","
        unused = any(z[1] == -1 for z in zones[:i])
        note = "  # not used (an earlier zone has no limit)" if unused else ""
        lines.append(f"{prefix}{ZONES[i]}: ({lo:2d}, {hi:2d}){end}{note}")
    return "\n".join(lines)


def gen_zone_map(data):
    out = ["ZONE_MAP = ("]
    for f, fz in enumerate(ZONES):
        fc = data["frontColors"][f]
        out.append(f"    {{DIST: ZONE2DIST[{fz}], LED_COLOR: KPRB.{fc}, CAR_BACK: ( # Front {fz}")
        for b, bz in enumerate(ZONES):
            bc = "KPRB." + data["backColors"][b] + ","
            cell = data["motors"][f][b]
            ld, ls = cell["left"]
            rd, rs = cell["right"]
            close = ")" if b == len(ZONES) - 1 else ","
            out.append(
                f"        {{DIST: ZONE2DIST[{bz}],  LED_COLOR: {bc:<14}"
                f"MTR_LEFT: ({ld + ',':<8} {ls:3d}),  "
                f"MTR_RIGHT: ({rd + ',':<8} {rs:3d})}}{close} # Back {bz}")
        out.append("    }" + ("," if f < len(ZONES) - 1 else ""))
    out.append(")")
    return "\n".join(out)


def write_config(path, data):
    zones = validate(data)
    data = dict(data, zones=zones)
    with open(path, encoding="utf-8") as f:
        source = f.read()
    nodes = _find_assignments(source)
    lines = source.splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"

    # Replace bottom-most block first so earlier line numbers stay valid.
    blocks = sorted(
        [(nodes["ZONE2DIST"], gen_zone2dist(zones)),
         (nodes["ZONE_MAP"], gen_zone_map(data))],
        key=lambda nb: nb[0].lineno, reverse=True)
    for node, text in blocks:
        new = [ln + newline for ln in text.split("\n")]
        lines[node.lineno - 1:node.end_lineno] = new
    new_source = "".join(lines)

    # Safety net: the new file must parse and read back to the same values.
    ast.parse(new_source)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(new_source)
    check = read_config(tmp)
    if (check["zones"] != zones or check["motors"] != data["motors"]
            or check["frontColors"] != data["frontColors"]
            or check["backColors"] != data["backColors"]):
        os.remove(tmp)
        raise ConfigError("internal check failed - config.py was NOT changed")

    shutil.copy2(path, path + ".bak")
    os.replace(tmp, path)
    return read_config(path)


# --------------------------------------------------------------------------
# Tiny web server
# --------------------------------------------------------------------------
def make_handler(config_path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body)
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "index.html"), encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html")
            elif self.path == "/api/config":
                try:
                    self._send(200, read_config(config_path))
                except (ConfigError, SyntaxError, KeyError, ValueError, TypeError) as e:
                    self._send(400, {"error": str(e)})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/config":
                return self._send(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n))
                self._send(200, write_config(config_path, data))
            except (ConfigError, KeyError, ValueError, TypeError) as e:
                self._send(400, {"error": str(e)})

        def log_message(self, fmt, *args):
            pass  # keep the terminal quiet

    return Handler


def main():
    config_path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG)
    read_config(config_path)  # fail early with a clear message
    server = ThreadingHTTPServer((HOST, PORT), make_handler(config_path))
    url = f"http://{HOST}:{PORT}/"
    print(f"Zone Editor is editing: {config_path}")
    print(f"Open {url} in Chrome or Firefox.  Press Ctrl+C here to stop.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")


if __name__ == "__main__":
    main()
