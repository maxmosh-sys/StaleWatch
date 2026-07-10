# StaleWatch

**StaleWatch** is a robust, lightweight, Python-based utility designed to detect "staleness" in files and directories. It triggers alerts when monitored paths haven't changed in terms of **last modification time** OR **file size**, ensuring that your critical processes, logs, and data exports are running as expected.

## Core Features
*   **Dual-Criterion Monitoring:** Detects staleness by analyzing both `mtime` (last modification time) and file size. If either changes, the timer resets.
*   **Multi-Channel Alerts:** Supports real-time notifications via **Email (SMTP)** and **Microsoft Teams (Incoming Webhooks)**.
*   **Anti-Spam Logic:** Implements an `alert_cooldown_minutes` setting to prevent alert fatigue by limiting notification frequency.
*   **Daily Log Rotation:** Automatically rotates logs at midnight using `TimedRotatingFileHandler`, keeping a 30-day history for easy auditing.
*   **Persistent State:** Maintains monitoring history locally to track alert status across reboots.

## Prerequisites
*   **Python 3.x** installed on the system.
*   **Libraries:** The `requests` library is required **only for Microsoft Teams notifications**. Email-only setups need no extra packages. To enable Teams alerts, install it via pip:
```bash
    pip install requests
    ```

## Folder Layout
StaleWatch resolves all paths relative to `StaleWatch.py`'s own location, so it works regardless of the current working directory:
```
StaleWatch.py
StaleWatch.bat
StaleWatch.json        # read (config, next to StaleWatch.py)
output_files/          # created automatically
    state.json         # read + written each run
    StaleWatch.log     # written (rotated daily)
```

## Setup Instructions
1.  **Project Location:** Place `StaleWatch.py`, `StaleWatch.bat`, and `StaleWatch.json` in your project directory (e.g., `C:\Users\maxmo\Projects\StaleWatch`). The `output_files` folder is created automatically on first run.
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

## Deployment
Automate the execution using **Windows Task Scheduler**:
1.  Set up a new task to run `StaleWatch.bat` every 10 minutes, passing the folder that contains `StaleWatch.py` and the environment as arguments (e.g., `StaleWatch.bat "C:\Users\maxmo\Projects\StaleWatch" PRD`). The environment must be one of `PRD PPR ITG QA1 QA2 QA3`.
2.  For full details, refer to the `DEPLOYMENT.md` file in this directory.

## Logging
The script automatically generates `output_files\StaleWatch.log`. Logs are rotated daily at midnight. The system keeps a history of the last 30 days of logs.

## License
This project is provided as-is for system monitoring and automation purposes.