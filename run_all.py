import os
import threading
import time
import subprocess
import smtplib
import shutil
from email.message import EmailMessage
from datetime import datetime
import sys

# ---------- CONFIG ----------
SENDER_EMAIL = "alankritsrivastava2k4@gmail.com"
APP_PASSWORD = "agfudcooqmnnkcsa"
RECEIVER_EMAIL = "dvpandit2003@gmail.com"

LOG_FILE = "run_log.txt"

ATTACHMENTS = [
    "keystrokes.txt",
    "system_info.xlsx",
    "screenshot.png"
]

# ---------- LOGGER ----------
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---------- GET USER FOLDER ----------
def get_latest_user_folder():
    folders = []
    for f in os.listdir('.'):
        if os.path.isdir(f) and not f.startswith('.'):
            if os.path.exists(os.path.join(f, "keystroke_dataset.csv")):
                folders.append(f)

    if not folders:
        return None

    return max(folders, key=os.path.getmtime)


# ---------- RUN STEP ----------
def run_step(name, command):
    log(f"STARTING: {name}")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        log(f"SUCCESS: {name}")
        return result.stdout

    except subprocess.CalledProcessError as e:
        log(f"ERROR in {name}")
        log(e.stderr)
        exit(1)


# ---------- AUTH STATUS ----------
def get_auth_status():
    log_file = "security_log.txt"

    if not os.path.exists(log_file):
        return "✅ Authenticated"

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return "✅ Authenticated"

    if "Intruder detected" in lines[-1]:
        return "🚨 Intrusion Detected"
    else:
        return "✅ Authenticated"


# ---------- MAIN ----------
def run_all():

    log("===== STARTING PIPELINE =====")

    # ---------------- BEHAVIOR AUTH ----------------
    log("Running behavior_auth (manual mode, 60 sec)...")

    process = subprocess.Popen(
        ["python", "behavior_auth.py"],
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    log("👉 Select user manually and start typing")

    def stop_process_after_timeout(p, timeout):
        time.sleep(timeout)
        if p.poll() is None:  # still running
            log("⏱ Timeout reached (60 sec). Stopping behavior_auth...")
            p.terminate()

    # run timeout thread
    timer_thread = threading.Thread(
        target=stop_process_after_timeout,
        args=(process, 60)
    )
    timer_thread.start()

    process.wait()  # wait until user exits OR timeout

    log("behavior_auth finished")

    # ---------------- COPY KEYSTROKES ----------------
    user_folder = get_latest_user_folder()

    if not user_folder:
        log("User folder not found")
        exit(1)

    src = os.path.join(user_folder, "keystrokes.txt")
    dst = "keystrokes.txt"

    if os.path.exists(src):
        shutil.copy(src, dst)
        log(f"Copied keystrokes.txt from {user_folder}")
    else:
        log("keystrokes.txt not found")
        exit(1)

    # ---------------- PREPROCESS ----------------
    run_step("preprocess_keylog.py", ["python", "preprocess_keylog.py"])

    # ---------------- SYSTEM TRACK ----------------
    log("Running system_track (20 sec)...")

    process = subprocess.Popen(["python", "system_track.pyw"])
    time.sleep(20)   # ✅ 20 seconds
    process.terminate()
    time.sleep(2)

    log("system_track stopped")

    # ---------------- ANALYZER ----------------
    analyzer_output = run_step(
        "activity-analyzer/main.py",
        ["python", "activity-analyzer/main.py"]
    )

    with open("analysis_output.txt", "w", encoding="utf-8") as f:
        f.write(analyzer_output)

    ATTACHMENTS.append("analysis_output.txt")

    # ---------------- EMAIL ----------------
    log("Sending email...")

    auth_status = get_auth_status()
    log(f"Authentication result: {auth_status}")

    msg = EmailMessage()
    msg["Subject"] = "Keystroke Analysis Report"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    report = f"""
================= KEYSTROKE ANALYSIS REPORT =================

📅 Analysis Duration:
Last 2 Minutes User Activity

🔐 Authentication Result:
{auth_status}

🧠 User Activity Classification:
------------------------------------------------------------
{analyzer_output}
------------------------------------------------------------

📊 Interpretation:
Based on the last 2 minutes of captured keystroke behavior:

- The system analyzed typing dynamics including speed, dwell time, and patterns.
- Activity classification is generated using behavioral analysis.
- Low confidence or zero activity indicates insufficient interaction data.

📝 Final Conclusion:
- If activity data is valid → user behavior is considered.
- If activity is missing/zero → result may not be reliable.
- Authentication decision is based on trained model + anomaly detection.

=============================================================
"""

    msg.set_content(report)

    for file in ATTACHMENTS:
        if os.path.exists(file):
            with open(file, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=file
                )
            log(f"Attached: {file}")
        else:
            log(f"Missing: {file}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)

        log("Email sent successfully")

    except Exception as e:
        log(f"Email error: {e}")

    log("===== PIPELINE COMPLETED =====")


# ---------- RUN ----------
if __name__ == "__main__":
    run_all()