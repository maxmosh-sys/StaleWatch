import os
import json
import logging
import argparse
from logging.handlers import TimedRotatingFileHandler # הוסף את השורה הזו בתחילת הקובץ עם שאר ה-Imports
import smtplib
from datetime import datetime
from email.message import EmailMessage

# All inputs and outputs are resolved relative to this script's own location,
# so the tool works no matter what the current working directory is.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Config lives alongside StaleWatch.py as StaleWatch.json.
CONFIG_PATH = os.path.join(BASE_DIR, "StaleWatch.json")

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="StaleWatch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "StaleWatch - a staleness monitor for files and folders.\n"
            "\n"
            "PURPOSE:\n"
            "  Some processes are supposed to keep updating a file or folder (a\n"
            "  log that should keep growing, an export that should be refreshed,\n"
            "  a data drop that should keep arriving). When they silently stop,\n"
            "  nobody notices. StaleWatch watches those paths and raises an alert\n"
            "  when one stops changing for too long.\n"
            "\n"
            "HOW IT WORKS:\n"
            "  * Reads its configuration from StaleWatch.json (next to this\n"
            "    script). Each entry under 'monitoring_tasks' describes one path\n"
            "    to watch, how long it may stay unchanged (threshold_minutes),\n"
            "    and how to alert (email and/or Microsoft Teams).\n"
            "  * For every run it checks each path's last-modified time and size.\n"
            "    If either changed since last time, the path is considered active\n"
            "    and its timer resets. If nothing changed for longer than the\n"
            "    threshold, the path is 'stale' and an alert is sent.\n"
            "  * 'alert_cooldown_minutes' prevents repeated alerts for the same\n"
            "    still-stale path.\n"
            "  * Each task keeps its own log file ('log_file', rotated daily with\n"
            "    a 30-day backlog) and its own state file ('state_file', which\n"
            "    remembers activity between runs). Their folders are created if\n"
            "    missing.\n"
            "\n"
            "USAGE:\n"
            "  StaleWatch is meant to run repeatedly (e.g. every 10 minutes via\n"
            "  Windows Task Scheduler / StaleWatch.bat). It runs once and exits;\n"
            "  the schedule provides the repetition."
        ),
        epilog=(
            "Examples:\n"
            "  python StaleWatch.py             Run one monitoring pass.\n"
            "  python StaleWatch.py --selftest  Check email/Teams connectivity, then run.\n"
        ),
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="Verify that the configured email/Teams channels are reachable "
             "before monitoring (posts a test message to Teams).",
    )
    return parser.parse_args(argv)


def _ensure_parent_dir(path):
    """Create the folder that will contain `path` if it does not exist yet."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def build_task_logger(task):
    """Return a logger that writes this task's messages to its own log file.

    The log file is named by the task's 'log_file' field (which must end in
    '.log'); its folder is created if missing. A TimedRotatingFileHandler rolls
    the file over at midnight and keeps a 30-day backlog.
    """
    log_file = task.get('log_file')
    if not log_file:
        raise ValueError(f"Task '{task['name']}' is missing the 'log_file' field.")
    if os.path.splitext(log_file)[1].lower() != '.log':
        raise ValueError(f"Task '{task['name']}' log_file must have a '.log' extension: {log_file}")

    _ensure_parent_dir(log_file)

    logger = logging.getLogger(f"StaleWatch.{task['name']}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # avoid duplicate handlers if this runs more than once
    # יצירת קובץ חדש בכל חצות (midnight), שמירה של 30 ימים אחורה (backupCount)
    handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30, encoding='utf-8')
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    return logger


def task_state_path(task):
    """Validate the task's 'state_file' field, create its folder, return the path.

    The file must end in '.json'; its folder is created if missing.
    """
    state_file = task.get('state_file')
    if not state_file:
        raise ValueError(f"Task '{task['name']}' is missing the 'state_file' field.")
    if os.path.splitext(state_file)[1].lower() != '.json':
        raise ValueError(f"Task '{task['name']}' state_file must have a '.json' extension: {state_file}")

    _ensure_parent_dir(state_file)
    return state_file


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_file_status(path, task_type):
    """Returns a tuple of (mtime, size). For folders, returns (max_mtime, total_size)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path does not exist: {path}")
    
    if task_type == 'file':
        stat = os.stat(path)
        return stat.st_mtime, stat.st_size
    else: 
        latest_mtime = 0
        total_size = 0
        for root, _, files in os.walk(path):
            for file in files:
                p = os.path.join(root, file)
                stat = os.stat(p)
                latest_mtime = max(latest_mtime, stat.st_mtime)
                total_size += stat.st_size
        return latest_mtime, total_size

def test_email_connection(settings):
    try:
        with smtplib.SMTP(settings['server'], settings['port'], timeout=10) as server:
            if settings.get('use_tls', True):
                server.starttls()
            password = os.environ.get('EMAIL_PASSWORD')
            if not password: raise ValueError("EMAIL_PASSWORD not set.")
            server.login(settings['sender_email'], password)
            return True
    except Exception as e:
        logging.error(f"Email test failed: {e}")
        return False

def test_teams_webhook(webhook_url):
    try:
        import requests  # imported lazily so email-only setups don't need it installed
        payload = {"text": "System Connectivity Test: The monitor is active."}
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Teams test failed: {e}")
        return False

def send_email_alert(settings, task, recipients):
    msg = EmailMessage()
    msg['Subject'] = f"Alert: Task '{task['name']}' is Stale"
    msg['From'] = settings['sender_email']
    msg['To'] = ", ".join(recipients)
    msg.set_content(f"Path '{task['path']}' is stale. Description: {task.get('description', 'N/A')}")
    
    password = os.environ.get('EMAIL_PASSWORD')
    if not password:
        raise ValueError(
            "EMAIL_PASSWORD is not set. Set it to a Google App Password "
            "(not your normal Gmail password) so StaleWatch can send email alerts."
        )

    with smtplib.SMTP(settings['server'], settings['port'], timeout=10) as server:
        if settings.get('use_tls', True): server.starttls()
        server.login(settings['sender_email'], password)
        server.send_message(msg)

def send_teams_alert(webhook_url, task):
    import requests  # imported lazily so email-only setups don't need it installed
    payload = {"text": f"**Alert:** Task '{task['name']}' is stale.\n\nPath: `{task['path']}`"}
    requests.post(webhook_url, json=payload, timeout=10).raise_for_status()

def process_task(task, state, logger=logging):
    now = datetime.now()

# 1. Get current status
    try:
        curr_mtime_ts, curr_size = get_file_status(task['path'], task['type'])
        curr_mtime = datetime.fromtimestamp(curr_mtime_ts)
    except Exception as e:
        logger.error(f"Error accessing '{task['name']}': {e}")
        return

# 2. Check if file is actually "Stale"
    # We retrieve the last known state for this task
    task_state = state.get(task['name'], {
        "last_mtime": curr_mtime_ts,
        "last_size": curr_size,
        "last_alert_time": "2000-01-01T00:00:00"
    })
    # Always persist the state for this task, even on the early returns below,
    # so healthy/fresh tasks keep a baseline in state.json.
    state[task['name']] = task_state

    # If size changed OR mtime changed, the file is NOT stale - reset the activity tracker
    if curr_mtime_ts > task_state['last_mtime'] or curr_size != task_state['last_size']:
        logger.info(f"Task '{task['name']}' activity detected (Size: {curr_size} bytes). Resetting timer.")
        task_state['last_mtime'] = curr_mtime_ts
        task_state['last_size'] = curr_size
        return

    # 3. Calculate staleness
    delta = (now - curr_mtime).total_seconds() / 60
    if delta <= task['threshold_minutes']:
        return

    # 4. Handle Cooldown
    last_alert = datetime.fromisoformat(task_state['last_alert_time'])
    if (now - last_alert).total_seconds() / 60 < task['alert_cooldown_minutes']:
        return

    # 5. Trigger Alerts
    logger.warning(f"Task '{task['name']}' is stale! Sending alerts...")
    for notification in task['notifications']:
        try:
            if notification['type'] == 'email':
                send_email_alert(load_config()['smtp_settings'], task, notification['recipients'])
            elif notification['type'] == 'teams':
                send_teams_alert(notification['webhook_url'], task)
        except Exception as e:
            logger.error(f"Failed to alert for '{task['name']}': {e}")

    task_state['last_alert_time'] = now.isoformat()

def run_selftest(config):
    """Verify notification channels are reachable. Posts a test message to Teams,
    so only run this on demand (python monitor.py --selftest), not every cycle."""
    logging.info("Running connectivity self-test...")
    test_email_connection(config['smtp_settings'])
    unique_urls = {n['webhook_url'] for t in config['monitoring_tasks'] for n in t['notifications'] if n['type'] == 'teams'}
    for url in unique_urls:
        test_teams_webhook(url)


def load_state(path):
    """Load persisted state, tolerating a missing or corrupted file."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Could not read '{path}' ({e}); starting from empty state.")
        return {}


def save_state(state, path):
    """Write state atomically so a crash mid-write can't corrupt the file."""
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=4)
    os.replace(tmp, path)


def main(argv=None):
    args = parse_args(argv)
    # Console logging for general/system messages; each task also logs to its own file.
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    try:
        config = load_config()

        if args.selftest:
            run_selftest(config)

        # Each task keeps its own log file and its own state file.
        for task in config.get('monitoring_tasks', []):
            try:
                logger = build_task_logger(task)
                state_path = task_state_path(task)
            except (ValueError, KeyError) as e:
                logging.error(f"Skipping task: {e}")
                continue

            state = load_state(state_path)
            process_task(task, state, logger)
            save_state(state, state_path)

    except Exception as e:
        logging.critical(f"System failure: {e}")

if __name__ == "__main__":
    main()