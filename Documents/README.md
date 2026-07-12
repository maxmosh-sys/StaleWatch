# StaleWatch

**StaleWatch** is a robust, lightweight, Python-based utility designed to detect "staleness" in files and directories. It triggers alerts when monitored paths haven't changed in terms of **last modification time** OR **file size**, ensuring that your critical processes, logs, and data exports are running as expected.

## Core Features
*   **Dual-Criterion Monitoring:** Detects staleness by analyzing both `mtime` (last modification time) and file size. If either changes, the timer resets.
*   **Multi-Channel Alerts:** Supports real-time notifications via **Email (SMTP)** and **Microsoft Teams (Incoming Webhooks)**.
*   **Anti-Spam Logic:** Implements an `alert_cooldown_minutes` setting to prevent alert fatigue by limiting notification frequency.
*   **Per-Task Log & State Files:** Each monitored task writes to its own log file and its own state file, whose names and locations are configured per task.
*   **Daily Log Rotation:** Automatically rotates each task's log at midnight using `TimedRotatingFileHandler`, keeping a 30-day history for easy auditing.
*   **Persistent State:** Maintains monitoring history locally (per task) to track alert status across reboots.

## Prerequisites
*   **Python 3.x** installed on the system.
*   **Libraries:** The `requests` library is required **only for Microsoft Teams notifications**. Email-only setups need no extra packages. To enable Teams alerts, install it via pip:
```bash
    pip install requests
    ```

## Folder Layout
`StaleWatch.py`, `StaleWatch.bat`, and `StaleWatch.json` sit together; the batch file runs `StaleWatch.py` from its own folder. Each task's log and state files live wherever its `log_file` / `state_file` fields point (their folders are created automatically):
```
StaleWatch.py
StaleWatch.bat
StaleWatch.json        # read (config, next to StaleWatch.py)
<per-task log_file>    # e.g. output_files\production_database_log.log (rotated daily)
<per-task state_file>  # e.g. output_files\production_database_log_state.json
```

## Setup Instructions
1.  **Project Location:** Place `StaleWatch.py`, `StaleWatch.bat`, and `StaleWatch.json` in your project directory (e.g., `C:\Users\maxmo\Projects\StaleWatch`). The folders referenced by each task's `log_file` / `state_file` are created automatically on first run.
2.  **Configuration:** Edit `StaleWatch.json` to define your monitoring tasks, thresholds, and notification endpoints.
3.  **Security:** For SMTP authentication, set the `EMAIL_PASSWORD` environment variable in your Windows system settings:
```cmd
    setx EMAIL_PASSWORD "your_password_here"
    ```

## Configuration (`StaleWatch.json`)
The configuration allows granular control over each monitored task:
*   `threshold_minutes`: Time limit for inactivity before triggering an alert.
*   `alert_cooldown_minutes`: Minimum delay before re-sending an alert for the same task.
*   `notifications`: A list of channels (Email/Teams) for each specific task.
*   `log_file`: Path to this task's log file. Must end in `.log`; its folder is created if missing and it is rotated daily (30-day backlog).
*   `state_file`: Path to this task's state file. Must end in `.json`; its folder is created if missing.

## Deployment
Automate the execution using **Windows Task Scheduler**:
1.  Set up a new task to run `StaleWatch.bat` every 10 minutes. The batch file runs `StaleWatch.py` from its own folder and takes no required arguments (pass `--selftest` to run a connectivity check first).
2.  For full details, refer to the `DEPLOYMENT.md` file in this directory.

## Logging
Each monitoring task writes to its own log file (the `log_file` field in `StaleWatch.json`). Logs are rotated daily at midnight, keeping the last 30 days.

## License
This project is provided as-is for system monitoring and automation purposes.