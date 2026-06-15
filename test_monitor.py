"""Functional test harness for StaleWatch monitor.py.

Exercises get_file_status and process_task without sending real alerts.
Run:  python test_monitor.py
"""
import os
import time
import tempfile
import shutil
from datetime import datetime, timedelta

import monitor

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


# --- Capture alerts instead of sending them ----------------------------------
sent = []
monitor.send_email_alert = lambda settings, task, recipients: sent.append(("email", task["name"]))
monitor.send_teams_alert = lambda url, task: sent.append(("teams", task["name"]))


def make_task(path, ttype="file", threshold=30, cooldown=60):
    return {
        "name": "T",
        "description": "d",
        "path": path,
        "type": ttype,
        "threshold_minutes": threshold,
        "alert_cooldown_minutes": cooldown,
        "notifications": [{"type": "teams", "webhook_url": "x"}],
    }


def set_mtime_minutes_ago(path, minutes):
    t = time.time() - minutes * 60
    os.utime(path, (t, t))


print("== get_file_status ==")
tmp = tempfile.mkdtemp()
try:
    f = os.path.join(tmp, "a.txt")
    with open(f, "w") as fh:
        fh.write("hello")
    mt, sz = monitor.get_file_status(f, "file")
    check("file size reported", sz == 5, f"got {sz}")

    # folder with two files
    f2 = os.path.join(tmp, "b.txt")
    with open(f2, "w") as fh:
        fh.write("world!!")
    mt, sz = monitor.get_file_status(tmp, "folder")
    check("folder total size = sum of files", sz == 12, f"got {sz}")

    # missing path raises
    try:
        monitor.get_file_status(os.path.join(tmp, "nope"), "file")
        check("missing path raises", False)
    except FileNotFoundError:
        check("missing path raises", True)

    # empty folder
    empty = os.path.join(tmp, "empty")
    os.mkdir(empty)
    mt, sz = monitor.get_file_status(empty, "folder")
    check("empty folder mtime is 0 (epoch)", mt == 0, f"got {mt}")
finally:
    shutil.rmtree(tmp)

print("\n== process_task: fresh file (within threshold) ==")
tmp = tempfile.mkdtemp()
try:
    f = os.path.join(tmp, "log.txt")
    with open(f, "w") as fh:
        fh.write("x")
    sent.clear()
    state = {}
    monitor.process_task(make_task(f), state)
    check("no alert for fresh file", sent == [], f"sent={sent}")
    check("state persisted for fresh file", "T" in state, f"state={state}")
finally:
    shutil.rmtree(tmp)

print("\n== process_task: stale file fires alert ==")
tmp = tempfile.mkdtemp()
try:
    f = os.path.join(tmp, "log.txt")
    with open(f, "w") as fh:
        fh.write("x")
    set_mtime_minutes_ago(f, 120)  # 2h old, threshold 30m
    sent.clear()
    state = {}
    monitor.process_task(make_task(f), state)
    check("alert fired for stale file", len(sent) == 1, f"sent={sent}")
finally:
    shutil.rmtree(tmp)

print("\n== process_task: cooldown suppresses second alert ==")
tmp = tempfile.mkdtemp()
try:
    f = os.path.join(tmp, "log.txt")
    with open(f, "w") as fh:
        fh.write("x")
    set_mtime_minutes_ago(f, 120)
    sent.clear()
    # state says we alerted 5 minutes ago, cooldown 60m
    state = {"T": {"last_mtime": os.stat(f).st_mtime, "last_size": 1,
                   "last_alert_time": (datetime.now() - timedelta(minutes=5)).isoformat()}}
    monitor.process_task(make_task(f), state)
    check("alert suppressed during cooldown", sent == [], f"sent={sent}")
finally:
    shutil.rmtree(tmp)

print("\n== process_task: activity resets timer (size change) ==")
tmp = tempfile.mkdtemp()
try:
    f = os.path.join(tmp, "log.txt")
    with open(f, "w") as fh:
        fh.write("x")
    set_mtime_minutes_ago(f, 120)
    sent.clear()
    state = {"T": {"last_mtime": 0, "last_size": 999,  # size differs -> activity
                   "last_alert_time": "2000-01-01T00:00:00"}}
    monitor.process_task(make_task(f), state)
    check("no alert when size changed (activity)", sent == [], f"sent={sent}")
    check("timer reset recorded new size", state["T"]["last_size"] == 1, state["T"])
finally:
    shutil.rmtree(tmp)

print("\n== process_task: missing path does not crash ==")
sent.clear()
state = {}
monitor.process_task(make_task("Z:\\does\\not\\exist.txt"), state)
check("missing path handled gracefully", sent == [], f"sent={sent}")

print("\n== load_state / save_state ==")
tmp = tempfile.mkdtemp()
try:
    p = os.path.join(tmp, "state.json")
    check("missing state file -> empty dict", monitor.load_state(p) == {})

    monitor.save_state({"T": {"last_size": 1}}, p)
    check("save then load round-trips", monitor.load_state(p) == {"T": {"last_size": 1}})
    check("no leftover .tmp file after atomic write", not os.path.exists(p + ".tmp"))

    with open(p, "w") as fh:
        fh.write("{ this is not valid json")
    check("corrupted state file -> empty dict (not a crash)", monitor.load_state(p) == {})
finally:
    shutil.rmtree(tmp)

print(f"\n==== {PASS} passed, {FAIL} failed ====")
