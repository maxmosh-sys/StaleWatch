"""One-off: send a real StaleWatch test alert email using StaleWatch.json + EMAIL_PASSWORD.

Usage (PowerShell, in this session so the password isn't stored anywhere):
    ! $env:EMAIL_PASSWORD="your-google-app-password"; python send_test_email.py
"""
import os
import sys
import StaleWatch as monitor

cfg = monitor.load_config()
settings = cfg["smtp_settings"]

if not os.environ.get("EMAIL_PASSWORD"):
    sys.exit("EMAIL_PASSWORD is not set. Set it to a Google App Password and re-run.")

task = {
    "name": "StaleWatch Test",
    "path": "(connectivity test — no real path)",
    "description": "If you received this, email alerting works.",
}

print(f"Sending test email from {settings['sender_email']} to maxmosh@gmail.com ...")
monitor.send_email_alert(settings, task, ["maxmosh@gmail.com"])
print("Sent. Check the maxmosh@gmail.com inbox (and Spam).")
