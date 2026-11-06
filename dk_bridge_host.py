"""DKAI FunStudio - hot-reloadable probe/patch host plugin.

Loads user_plugins/dk_bridge_ext.py and re-executes it whenever that file
changes, so logic can be iterated without restarting the app.

Controls:
  user_plugins/PATCH_GO.txt        -> enable the patch stage
  user_plugins/dk_bridge_host.log  -> everything this host does
  user_plugins/dk_bridge_ext.log   -> everything the ext script does
"""

import os
import time
import threading
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOG = os.path.join(_HERE, "dk_bridge_host.log")
_EXT = os.path.join(_HERE, "dk_bridge_ext.py")
_EXT_LOG = os.path.join(_HERE, "dk_bridge_ext.log")

_state = {}
_g = {}


def _log(msg):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def _log_ext(msg):
    try:
        with open(_EXT_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def _load_ext():
    with open(_EXT, "r", encoding="utf-8") as f:
        src = f.read()
    g = {"__name__": "dk_bridge_ext", "__file__": _EXT}
    exec(compile(src, _EXT, "exec"), g)
    return g


def _worker():
    _log("host started (pid=%s)" % os.getpid())
    mtime = 0.0
    while True:
        try:
            if os.path.exists(_EXT):
                m = os.path.getmtime(_EXT)
                if m != mtime:
                    mtime = m
                    _log("loading ext (mtime=%s)" % m)
                    try:
                        _g = _load_ext()
                        _log("ext loaded ok")
                    except Exception:
                        _log("ext load FAILED\n" + traceback.format_exc())
            tick = _g.get("tick")
            if tick is not None:
                try:
                    tick(_state, _log_ext)
                except Exception:
                    _log_ext("tick error\n" + traceback.format_exc())
        except Exception:
            _log("host loop error\n" + traceback.format_exc())
        time.sleep(1.5)


def _start():
    try:
        threading.Thread(target=_worker, name="dk-bridge-host", daemon=True).start()
    except Exception:
        _log("could not start host\n" + traceback.format_exc())


_start()


try:
    from application.funscript.plugins.base_plugin import FunscriptTransformationPlugin as _Base
except Exception:
    try:
        from plugins.base_plugin import FunscriptTransformationPlugin as _Base
    except Exception:
        _Base = object


class BridgeProbePlaceholder(_Base):
    """No-op plugin so the loader sees a well-formed plugin."""

    @property
    def name(self):
        return "dk_bridge_probe_placeholder"

    @property
    def description(self):
        return "Diagnostic placeholder - does nothing to the funscript."

    @property
    def version(self):
        return "0.3.0"

    @property
    def parameters_schema(self):
        return {}

    def transform(self, funscript, axis="both", **parameters):
        return None

    def get_preview(self, funscript, axis="both", **parameters):
        return {"filter_type": "BridgeProbePlaceholder"}
