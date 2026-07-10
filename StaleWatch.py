import os
import sys
import json
import logging
from logging.handlers import TimedRotatingFileHandler # הוסף את השורה הזו בתחילת הקובץ עם שאר ה-Imports
import smtplib
from datetime import datetime
from email.message import EmailMessage

# All inputs and outputs are resolved relative to this script's own location,
# so the tool works no matter what the current working directory is.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")

# Config lives alongside StaleWatch.py as StaleWatch.json.
CONFIG_PATH = os.path.join(BASE_DIR, "StaleWatch.json")
STATE_PATH = os.path.join(OUTPUT_DIR, "state.json")
LOG_PATH = os.path.join(OUTPUT_DIR, "StaleWatch.log")

# Outputs (log + state) live in output_files/, which must exist before logging starts.
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # יצירת קובץ חדש בכל חצות (midnight), שמירה של 30 ימים אחורה (backupCount)
        TimedRotatingFileHandler(LOG_PATH, when="midnight", interval=1, backupCount=30, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
    
    with smtplib.SMTP(settings['server'], settings['port'], timeout=10) as server:
        if settings.get('use_tls', True): server.starttls()
        server.login(settings['sender_email'], os.environ.get('EMAIL_PASSWORD'))
        server.send_message(msg)

def send_teams_alert(webhook_url, task):
    import requests  # imported lazily so email-only setups don't need it installed
    payload = {"text": f"**Alert:** Task '{task['name']}' is stale.\n\nPath: `{task['path']}`"}
    requests.post(webhook_url, json=payload, timeout=10).raise_for_status()

def process_task(task, state):
    now = datetime.now()

# 1. Get current status
    try:
        curr_mtime_ts, curr_size = get_file_status(task['path'], task['type'])
        curr_mtime = datetime.fromtimestamp(curr_mtime_ts)
    except Exception as e:
        logging.error(f"Error accessing '{task['name']}': {e}")
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
        logging.info(f"Task '{task['name']}' activity detected (Size: {curr_size} bytes). Resetting timer.")
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
    logging.warning(f"Task '{task['name']}' is stale! Sending alerts...")
    for notification in task['notifications']:
        try:
            if notification['type'] == 'email':
                send_email_alert(load_config()['smtp_settings'], task, notification['recipients'])
            elif notification['type'] == 'teams':
                send_teams_alert(notification['webhook_url'], task)
        except Exception as e:
            logging.error(f"Failed to alert for '{task['name']}': {e}")

    task_state['last_alert_time'] = now.isoformat()

def run_selftest(config):
    """Verify notification channels are reachable. Posts a test message to Teams,
    so only run this on demand (python monitor.py --selftest), not every cycle."""
    logging.info("Running connectivity self-test...")
    test_email_connection(config['smtp_settings'])
    unique_urls = {n['webhook_url'] for t in config['monitoring_tasks'] for n in t['notifications'] if n['type'] == 'teams'}
    for url in unique_urls:
        test_teams_webhook(url)


def load_state(path=STATE_PATH):
    """Load persisted state, tolerating a missing or corrupted file."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Could not read '{path}' ({e}); starting from empty state.")
        return {}


def save_state(state, path=STATE_PATH):
    """Write state atomically so a crash mid-write can't corrupt the file."""
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=4)
    os.replace(tmp, path)


def main():
    try:
        config = load_config()

        if '--selftest' in sys.argv:
            run_selftest(config)

        state = load_state()

        for task in config.get('monitoring_tasks', []):
            process_task(task, state)

        save_state(state)

    except Exception as e:
        logging.critical(f"System failure: {e}")

if __name__ == "__main__":
    main()