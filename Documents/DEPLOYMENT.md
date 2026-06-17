# StaleWatch Deployment Guide

This guide provides step-by-step instructions for automating the **StaleWatch** monitoring tool using the Windows Task Scheduler.

## Prerequisites
1. Ensure `StaleWatch.py` and `StaleWatch.bat` are in your project directory (e.g., `C:\Users\maxmo\Projects\StaleWatch`), with `config.json` inside the `input_files` subfolder. (`output_files\state.json` and `output_files\StaleWatch.log` are created automatically.)
2. Verify that `python` is available on the system PATH (the batch file calls `python` directly).
3. Ensure the `EMAIL_PASSWORD` environment variable is set in your system environment variables.

## Step-by-Step Configuration

### 1. Open Task Scheduler
- Press `Win + R`, type `taskschd.msc`, and hit Enter.
- In the right-hand panel, click **Create Task...**.

### 2. General Tab
- **Name**: `StaleWatch_Monitor`
- **Security Options**:
    - Select **Run whether user is logged on or not**.
    - Check **Run with highest privileges**.

### 3. Triggers Tab
- Click **New...**.
- **Begin the task**: On a schedule.
- Select **Daily**.
- Under **Advanced settings**:
    - Check **Repeat task every:** and set it to **10 minutes**.
    - Set **for a duration of:** to **Indefinitely**.

### 4. Actions Tab
- Click **New...**.
- **Action**: Start a program.
- **Program/script**: Browse and select `C:\Users\maxmo\Projects\StaleWatch\StaleWatch.bat`.
- **Add arguments (optional)**: The folder that contains `StaleWatch.py`, quoted: `"C:\Users\maxmo\Projects\StaleWatch"`
    - *Note: This argument is required — the batch file passes it to Python as the location of `StaleWatch.py`. Inputs/outputs are then resolved relative to that folder, so "Start in" is no longer needed.*

### 5. Settings Tab
- **Stop the task if it runs longer than**: Set to `1 hour` to prevent zombie processes.
- **If the task is already running, then the following rule applies**: Set to `Do not start a new instance`.

### 6. Finalization
- Click **OK**.
- Enter your Windows account credentials when prompted to authorize the task to run in the background.

## Verification
1. Right-click the newly created task (`StaleWatch_Monitor`) in the Task Scheduler library.
2. Click **Run**.
3. Check the `output_files\StaleWatch.log` file in your project folder to confirm the script executed successfully without errors.