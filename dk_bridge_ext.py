"""Probe/patch body for the DKAI FunStudio live-tracker bridge bug (round 4).

Findings:
  * TrackerManager -> app.device_manager (DeviceManager) works.
  * LiveTrackerBridge.start() is an **async** coroutine, so it must be scheduled
    on a running asyncio loop (the device-control bridge loop), not just called.

This round: attach the bridge and drive start()/stop() on the app's own loop.
Enabled only while user_plugins/PATCH_GO.txt exists.
"""

import os
import gc
import time
import asyncio
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
GO = os.path.join(HERE, "PATCH_GO.txt")


def _short(v):
    try:
        return type(v).__name__
    except Exception:
        return "?"


def _find_trackers():
    out = []
    for o in gc.get_objects():
        try:
            if isinstance(o, type):
                continue
            if getattr(o, "_send_to_device_control", None) is None:
                continue
            out.append(o)
        except Exception:
            continue
    return out


def _running_loops():
    out = []
    for o in gc.get_objects():
        try:
            if isinstance(o, asyncio.AbstractEventLoop) and o.is_running():
                out.append(o)
        except Exception:
            continue
    return out


def _manager_of(o):
    app = getattr(o, "app", None)
    return getattr(app, "device_manager", None) if app is not None else None


def _start_bridge(bridge, log):
    loops = _running_loops()
    log("PATCH: running loops=%d %s" % (len(loops), [type(l).__name__ for l in loops]))
    for loop in loops[:4]:
        try:
            fut = asyncio.run_coroutine_threadsafe(bridge.start(), loop)
            try:
                r = fut.result(timeout=4)
                log("PATCH: start() on %s -> %r" % (type(loop).__name__, r))
            except Exception as e:
                log("PATCH: start() future on %s -> %s: %s" % (type(loop).__name__, type(e).__name__, e))
        except Exception:
            log("PATCH: run_coroutine_threadsafe failed on %s\n%s" % (type(loop).__name__, traceback.format_exc()))
    log("PATCH: is_active=%s" % getattr(bridge, "is_active", "?"))


def _build(o, log):
    if getattr(o, "device_bridge", None) is not None:
        br = getattr(o, "device_bridge")
        if not getattr(br, "is_active", False):
            _start_bridge(br, log)
        return False
    dm = _manager_of(o)
    if dm is None:
        log("PATCH: no device manager")
        return False
    try:
        mod = __import__("device_control.bridges.live_tracker_bridge", fromlist=["*"])
        bridge = mod.create_live_tracker_bridge(dm)
        log("PATCH: created %s" % type(bridge).__name__)
        _start_bridge(bridge, log)
        setattr(o, "device_bridge", bridge)
        log("PATCH: attached on id=%s active=%s" % (id(o) % 100000, getattr(bridge, "is_active", "?")))
        return True
    except Exception:
        log("PATCH: failed\n" + traceback.format_exc())
        return False


def tick(state, log):
    now = time.time()
    if now - state.get("last", 0.0) < 2.0:
        return
    state["last"] = now
    if not isinstance(state.get("reported"), dict):
        state["reported"] = {}

    trackers = _find_trackers()
    log("scan: trackers=%d go=%s loops=%d (v5)" % (len(trackers), os.path.exists(GO), len(_running_loops())))
    for o in trackers[:8]:
        br = getattr(o, "device_bridge", None)
        line = "tracker id=%s bridge=%s active=%s tracking=%s" % (
            id(o) % 100000, _short(br), getattr(br, "is_active", "-"), getattr(o, "tracking_active", "?"))
        if state["reported"].get(id(o)) != line:
            state["reported"][id(o)] = line
            log(line)

    if os.path.exists(GO):
        for o in trackers[:8]:
            try:
                _build(o, log)
            except Exception:
                log("patch error\n" + traceback.format_exc())
