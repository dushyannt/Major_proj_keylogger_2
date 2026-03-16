import time
import os
import datetime
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, scrolledtext

from pynput import keyboard
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler


class TypingDisplay:
    """GUI window to display typed text in real-time"""

    def __init__(self, user_id=None):
        self.user_id = user_id or "Unknown User"
        self.root = None
        self.text_area = None
        self.status_label = None
        self.typed_text = ""
        self.create_window()

    def create_window(self):
        """Create the GUI window"""
        self.root = tk.Tk()
        self.root.title(f"Keystroke Authentication - {self.user_id}")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Real-time Typing Display",
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10))

        # Text display area
        self.text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD,
                                                 font=("Consolas", 12),
                                                 height=15)
        self.text_area.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.text_area.config(state=tk.DISABLED)  # Read-only

        # Status bar
        self.status_label = ttk.Label(main_frame,
                                     text="Ready to type...",
                                     font=("Arial", 10))
        self.status_label.grid(row=2, column=0, pady=(10, 0), sticky=tk.W)

        # Initial message - cleaner
        self.update_display("")

    def update_display(self, text):
        """Update the text display"""
        if self.text_area:
            # Schedule GUI update in main thread
            def _update():
                self.text_area.config(state=tk.NORMAL)
                self.text_area.insert(tk.END, text)
                self.text_area.see(tk.END)  # Auto-scroll to bottom
                self.text_area.config(state=tk.DISABLED)
            if self.root:
                self.root.after(0, _update)

    def update_status(self, message):
        """Update the status message"""
        if self.status_label:
            # Schedule GUI update in main thread
            def _update():
                self.status_label.config(text=message)
            if self.root:
                self.root.after(0, _update)

    def append_char(self, char):
        """Append a character to the display"""
        self.typed_text += char
        self.update_display(char)

    def backspace(self):
        """Handle backspace"""
        if self.typed_text:
            self.typed_text = self.typed_text[:-1]
            # Clear and redraw text
            def _update():
                self.text_area.config(state=tk.NORMAL)
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, self.typed_text)
                self.text_area.config(state=tk.DISABLED)
            if self.root:
                self.root.after(0, _update)

    def clear_display(self):
        """Clear the text display"""
        self.typed_text = ""
        def _update():
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete(1.0, tk.END)
            self.text_area.config(state=tk.DISABLED)
        if self.root:
            self.root.after(0, _update)

    def show_authentication_result(self, authenticated, dwell, flight, speed):
        """Show authentication result - now minimal display"""
        # Only update status bar, don't add text to main display
        status = "✅ AUTHENTICATED" if authenticated else "🚨 INTRUDER DETECTED"
        self.update_status(status)

    def show_early_alert(self):
        """Show early intruder detection alert - minimal display"""
        # Only update status bar, don't add text to main display
        self.update_status("🚨 Early intruder detected!")

    def close(self):
        """Close the GUI window"""
        if self.root:
            self.root.quit()
            self.root.destroy()


class SystemMonitor:

    def __init__(self, user_id=None, show_display=True):

        self.user_id = user_id

        if user_id:
            # Create user folder
            self.user_folder = f"./{user_id}"
            os.makedirs(self.user_folder, exist_ok=True)

            # files - now inside user folder
            self.keylog_file = f"{self.user_folder}/keystrokes.txt"
            self.dataset_file = f"{self.user_folder}/keystroke_dataset.csv"
            self.model_file = f"{self.user_folder}/keystroke_model.pkl"
            self.anomaly_model_file = f"{self.user_folder}/anomaly_model.pkl"
            self.scaler_file = f"{self.user_folder}/scaler.pkl"
        else:
            # fallback for backward compatibility
            self.user_folder = "."
            self.keylog_file = "keystrokes.txt"
            self.dataset_file = "keystroke_dataset.csv"
            self.model_file = "keystroke_model.pkl"
            self.anomaly_model_file = "anomaly_model.pkl"
            self.scaler_file = "scaler.pkl"

        # typing tracking
        self.key_press_times = {}
        self.last_release_time = None
        self.char_count = 0
        self.start_time = time.time()
        self.backspace_counter = 0

        # feature buffer
        self.feature_buffer = []

        # time window authentication
        self.window_duration = 10
        self.window_start_time = time.time()

        # minute-based authentication
        self.auth_count = 0
        self.total_checks = 0
        self.minute_start = time.time()

        # early detection
        self.min_samples_for_check = 15

        # baseline user profile
        self.user_mean = None

        # GUI display
        self.display = None
        if show_display:
            self.display = TypingDisplay(user_id)

        # create dataset if not exists
        if not os.path.exists(self.dataset_file):
            df = pd.DataFrame(columns=[
                "dwell_time",
                "flight_time",
                "typing_speed",
                "backspace_rate",
                "label"
            ])
            df.to_csv(self.dataset_file, index=False)
        else:
            # Check if backspace_rate column exists, if not, add it
            df = pd.read_csv(self.dataset_file)
            if "backspace_rate" not in df.columns:
                df["backspace_rate"] = 0.0  # Default value for existing data
                df.to_csv(self.dataset_file, index=False)

    # --------------------------------
    # User Management Methods
    # --------------------------------

    @staticmethod
    def list_users():
        """List all registered users by checking for user folders"""
        users = []
        try:
            for item in os.listdir('.'):
                if os.path.isdir(item) and not item.startswith('.') and item != '__pycache__':
                    # Check if it's a user folder (has keystroke_dataset.csv)
                    dataset_file = f"{item}/keystroke_dataset.csv"
                    if os.path.exists(dataset_file):
                        users.append(item)
        except:
            pass
        return users

    @staticmethod
    def register_user(user_id):
        """Register a new user by creating their folder and initial dataset"""
        user_folder = f"./{user_id}"
        dataset_file = f"{user_folder}/keystroke_dataset.csv"

        if os.path.exists(user_folder):
            print(f"User {user_id} already exists!")
            return False

        # Create user folder
        os.makedirs(user_folder, exist_ok=True)

        df = pd.DataFrame(columns=[
            "dwell_time",
            "flight_time",
            "typing_speed",
            "backspace_rate",
            "label"
        ])
        df.to_csv(dataset_file, index=False)
        print(f"User {user_id} registered successfully!")
        return True

    @staticmethod
    def user_exists(user_id):
        """Check if a user exists by checking for their folder"""
        user_folder = f"./{user_id}"
        dataset_file = f"{user_folder}/keystroke_dataset.csv"
        return os.path.exists(user_folder) and os.path.exists(dataset_file)

    @staticmethod
    def migrate_existing_data(user_id):
        """Migrate existing single-user data to a new user profile"""
        user_folder = f"./{user_id}"
        if not os.path.exists(user_folder):
            os.makedirs(user_folder, exist_ok=True)

        # Source files (old naming pattern)
        old_files = {
            'dataset': f'keystroke_dataset_{user_id}.csv',
            'model': f'keystroke_model_{user_id}.pkl',
            'anomaly': f'anomaly_model_{user_id}.pkl',
            'scaler': f'scaler_{user_id}.pkl',
            'keylog': f'keystrokes_{user_id}.txt'
        }

        # Destination files (new folder structure)
        new_files = {
            'dataset': f"{user_folder}/keystroke_dataset.csv",
            'model': f"{user_folder}/keystroke_model.pkl",
            'anomaly': f"{user_folder}/anomaly_model.pkl",
            'scaler': f"{user_folder}/scaler.pkl",
            'keylog': f"{user_folder}/keystrokes.txt"
        }

        migrated = False
        for file_type, old_file in old_files.items():
            if os.path.exists(old_file):
                import shutil
                shutil.copy2(old_file, new_files[file_type])
                print(f"Migrated {file_type}: {old_file} -> {new_files[file_type]}")
                migrated = True
            else:
                print(f"Source file {old_file} not found, skipping {file_type}")

        # After migration, ensure the dataset has the correct columns
        dataset_file = new_files['dataset']
        if os.path.exists(dataset_file) and migrated:
            df = pd.read_csv(dataset_file)
            if 'backspace_rate' not in df.columns:
                df['backspace_rate'] = 0.0  # Default for migrated data
                df.to_csv(dataset_file, index=False)
                print(f"Added backspace_rate column to {dataset_file}")

        if migrated:
            print(f"\n✅ Successfully migrated existing data to user profile: {user_id}")
            print("You can now use your existing training data!")
        else:
            print("No existing data found to migrate.")

        return migrated

    # --------------------------------
    # Typing Speed
    # --------------------------------

    def calculate_typing_speed(self):

        elapsed = time.time() - self.start_time

        if elapsed == 0:
            return 0

        wpm = (self.char_count / 5) / (elapsed / 60)

        return wpm

    # --------------------------------
    # Save dataset sample
    # --------------------------------

    def save_typing_sample(self, dwell, flight, speed, backspace_rate, label):

        df = pd.DataFrame([[dwell, flight, speed, backspace_rate, label]],
                          columns=[
                              "dwell_time",
                              "flight_time",
                              "typing_speed",
                              "backspace_rate",
                              "label"
                          ])

        df.to_csv(self.dataset_file, mode="a",
                  header=False, index=False)

    # --------------------------------
    # User baseline calculation
    # --------------------------------

    def calculate_user_baseline(self):

        data = pd.read_csv(self.dataset_file)

        user_data = data[data["label"] == 1].tail(100)

        if len(user_data) == 0:
            return

        self.user_mean = user_data[
            ["dwell_time", "flight_time", "typing_speed", "backspace_rate"]
        ].mean()

    # --------------------------------
    # Detect new user
    # --------------------------------

    def detect_new_user(self, dwell, flight, speed, backspace_rate):

        if self.user_mean is None:
            return False

        current = pd.Series(
            [dwell, flight, speed, backspace_rate],
            index=["dwell_time", "flight_time", "typing_speed", "backspace_rate"]
        )

        distance = ((current - self.user_mean) ** 2).sum() ** 0.5

        if distance > 0.5:
            return True

        return False

    # --------------------------------
    # Train ML models
    # --------------------------------

    def train_model(self):

        data = pd.read_csv(self.dataset_file)

        if len(data) < 30:
            print("Collect more typing data first")
            return

        self.calculate_user_baseline()

        X = data[["dwell_time", "flight_time", "typing_speed", "backspace_rate"]]
        y = data["label"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        scaler = StandardScaler()

        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        joblib.dump(scaler, self.scaler_file)

        rf = RandomForestClassifier()

        rf.fit(X_train_scaled, y_train)

        preds = rf.predict(X_test_scaled)

        accuracy = accuracy_score(y_test, preds)

        print("Model Accuracy:", round(accuracy * 100, 2), "%")
        print("Training samples:", len(X_train),
              "Testing samples:", len(X_test))

        joblib.dump(rf, self.model_file)

        iso = IsolationForest(contamination=0.05)

        iso.fit(X_train_scaled)

        joblib.dump(iso, self.anomaly_model_file)

    # --------------------------------
    # Authentication
    # --------------------------------

    def authenticate_user(self, dwell, flight, speed, backspace_rate):

        if not os.path.exists(self.model_file):
            return True

        rf = joblib.load(self.model_file)
        iso = joblib.load(self.anomaly_model_file)
        scaler = joblib.load(self.scaler_file)

        # For now, temporarily ignore backspace_rate in authentication
        # since training data is biased toward backspace_rate = 0.0
        sample = pd.DataFrame(
            [[dwell, flight, speed, 0.0]],  # Use 0.0 for backspace_rate temporarily
            columns=["dwell_time", "flight_time", "typing_speed", "backspace_rate"]
        )

        sample_scaled = scaler.transform(sample)

        rf_pred = rf.predict(sample_scaled)
        iso_pred = iso.predict(sample_scaled)

        authenticated = rf_pred[0] == 1 and iso_pred[0] == 1

        return authenticated

    # --------------------------------
    # Intrusion alert
    # --------------------------------

    def intrusion_alert(self):

        print("🚨 SECURITY ALERT 🚨")
        print("Unknown typing behaviour detected")

        if self.display:
            self.display.show_early_alert()

        with open("security_log.txt", "a") as f:
            user_info = f" for user {self.user_id}" if self.user_id else ""
            f.write(
                f"{datetime.datetime.now()} Intruder detected{user_info}\n"
            )

    # --------------------------------
    # Visualization
    # --------------------------------

    def visualize_typing_behavior(self):

        data = pd.read_csv(self.dataset_file)

        plt.figure()

        plt.scatter(
            data["dwell_time"],
            data["flight_time"]
        )

        plt.xlabel("Dwell Time")
        plt.ylabel("Flight Time")
        plt.title("Typing Behaviour Pattern")

        plt.show()

    # --------------------------------
    # Key press
    # --------------------------------

    def on_press(self, key):

        try:

            press_time = time.time()

            self.char_count += 1

            if key == keyboard.Key.backspace:
                self.backspace_counter += 1
                # Handle backspace in display
                if self.display:
                    self.display.backspace()

            if self.last_release_time:
                flight_time = press_time - self.last_release_time
            else:
                flight_time = 0

            self.key_press_times[key] = (press_time, flight_time)

        except:
            pass

    # --------------------------------
    # Key to character conversion
    # --------------------------------

    def key_to_char(self, key):
        """Convert keyboard key to displayable character"""
        try:
            # Handle special keys
            if key == keyboard.Key.space:
                return " "
            elif key == keyboard.Key.enter:
                return "\n"
            elif key == keyboard.Key.tab:
                return "\t"
            elif hasattr(key, 'char') and key.char:
                return key.char
            else:
                # Skip other special keys (shift, ctrl, etc.)
                return None
        except:
            return None

    # --------------------------------
    # Key release
    # --------------------------------

    def on_release(self, key):

        try:

            release_time = time.time()

            if key in self.key_press_times:

                press_time, flight = self.key_press_times[key]

                dwell = release_time - press_time

                speed = self.calculate_typing_speed()

                now = datetime.datetime.now()

                with open(self.keylog_file, "a") as f:
                    f.write(
                        f"{now} Key:{key} "
                        f"Dwell:{dwell:.3f} "
                        f"Flight:{flight:.3f} "
                        f"WPM:{speed:.2f}\n"
                    )

                # Update display with the typed character
                if self.display and key != keyboard.Key.backspace:
                    char_to_display = self.key_to_char(key)
                    if char_to_display:
                        self.display.append_char(char_to_display)

                self.feature_buffer.append((dwell, flight, speed))

                # early anomaly detection
                if len(self.feature_buffer) >= self.min_samples_for_check:

                    avg_dwell = np.mean([x[0] for x in self.feature_buffer])
                    avg_flight = np.mean([x[1] for x in self.feature_buffer])
                    avg_speed = np.mean([x[2] for x in self.feature_buffer])
                    early_elapsed = time.time() - self.window_start_time
                    early_backspace_rate = self.backspace_counter / early_elapsed * 60 if early_elapsed > 0 else 0

                    if os.path.exists(self.anomaly_model_file):

                        iso = joblib.load(self.anomaly_model_file)
                        scaler = joblib.load(self.scaler_file)

                        sample = pd.DataFrame(
                            [[avg_dwell, avg_flight, avg_speed, early_backspace_rate]],
                            columns=[
                                "dwell_time",
                                "flight_time",
                                "typing_speed",
                                "backspace_rate"
                            ]
                        )

                        sample_scaled = scaler.transform(sample)

                        anomaly = iso.predict(sample_scaled)

                        if anomaly[0] == -1:

                            print("\n🚨 EARLY INTRUDER DETECTION 🚨\n")

                            self.intrusion_alert()
                            self.save_typing_sample(avg_dwell, avg_flight, avg_speed, early_backspace_rate, label=0)
                            self.feature_buffer.clear()
                            self.backspace_counter = 0
                            self.window_start_time = time.time()

                            return

                # time window authentication
                if time.time() - self.window_start_time >= self.window_duration:

                    print("\nAnalyzing typing behaviour...\n")

                    avg_dwell = np.mean([x[0] for x in self.feature_buffer])
                    avg_flight = np.mean([x[1] for x in self.feature_buffer])
                    avg_speed = np.mean([x[2] for x in self.feature_buffer])
                    window_elapsed = time.time() - self.window_start_time
                    backspace_rate = self.backspace_counter / window_elapsed * 60 if window_elapsed > 0 else 0

                    if self.detect_new_user(avg_dwell, avg_flight, avg_speed, backspace_rate):

                        print("\nNew typing pattern detected\n")

                        self.save_typing_sample(
                            avg_dwell, avg_flight, avg_speed, backspace_rate, label=0
                        )

                    else:

                        self.save_typing_sample(
                            avg_dwell, avg_flight, avg_speed, backspace_rate, label=1
                        )

                    authenticated = self.authenticate_user(
                        avg_dwell, avg_flight, avg_speed, backspace_rate
                    )

                    self.total_checks += 1
                    if authenticated:
                        self.auth_count += 1

                    if self.total_checks >= 6:  # 6 checks per minute (every 10 seconds)
                        overall_authenticated = self.auth_count > 3  # more than half (3 out of 6)

                        if overall_authenticated:
                            print("User authenticated for the minute")
                        else:
                            self.intrusion_alert()

                        # Update display with minute authentication result
                        if self.display:
                            self.display.show_authentication_result(overall_authenticated, avg_dwell, avg_flight, avg_speed)

                        # Reset counters
                        self.auth_count = 0
                        self.total_checks = 0
                        self.minute_start = time.time()

                    self.feature_buffer.clear()
                    self.backspace_counter = 0
                    self.window_start_time = time.time()

            self.last_release_time = release_time

        except:
            pass

        if key == keyboard.Key.esc:
            # Close GUI window when ESC is pressed
            if self.display and self.display.root:
                def _close():
                    self.display.root.quit()
                    self.display.root.destroy()
                self.display.root.after(0, _close)
            return False

    # --------------------------------
    # Start system
    # --------------------------------

    def start(self):

        print(f"Starting authentication for user: {self.user_id}")
        print("⚠️  IMPORTANT: Type normally for 2-3 minutes to update your profile with backspace data!")
        print("Press ESC to stop\n")

        # Start keyboard listener in separate thread
        import threading
        listener_thread = threading.Thread(target=self._run_listener, daemon=True)
        listener_thread.start()

        # Start GUI mainloop in main thread (tkinter requirement)
        if self.display:
            self.display.root.mainloop()
        else:
            # If no display, just wait for listener to finish
            listener_thread.join()

        self.train_model()

        self.visualize_typing_behavior()

    def _run_listener(self):
        """Run the keyboard listener in a separate thread"""
        try:
            with keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release) as listener:

                listener.join()
        except Exception as e:
            print(f"Listener error: {e}")


# --------------------------------
# Main User Interface
# --------------------------------

def main():
    print("=== Multi-User Keystroke Authentication System ===\n")

    while True:
        print("Options:")
        print("1. Login as existing user")
        print("2. Register new user")
        print("3. List all users")
        print("4. Migrate existing data to user profile")
        print("5. Exit")

        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1":
            # Login
            users = SystemMonitor.list_users()
            if not users:
                print("No users registered yet. Please register first.")
                continue

            print("Available users:")
            for i, user in enumerate(users, 1):
                print(f"{i}. {user}")

            user_choice = input("Enter user number or name: ").strip()

            # Check if it's a number
            if user_choice.isdigit():
                idx = int(user_choice) - 1
                if 0 <= idx < len(users):
                    user_id = users[idx]
                else:
                    print("Invalid user number.")
                    continue
            else:
                user_id = user_choice

            if SystemMonitor.user_exists(user_id):
                monitor = SystemMonitor(user_id, show_display=True)
                monitor.start()
            else:
                print(f"User {user_id} does not exist.")

        elif choice == "2":
            # Register
            user_id = input("Enter new user ID: ").strip()
            if not user_id:
                print("User ID cannot be empty.")
                continue

            if SystemMonitor.user_exists(user_id):
                print(f"User {user_id} already exists!")
            else:
                SystemMonitor.register_user(user_id)
                print(f"\nWelcome {user_id}! Please type to build your profile.")
                monitor = SystemMonitor(user_id, show_display=True)
                monitor.start()

        elif choice == "3":
            # List users
            users = SystemMonitor.list_users()
            if users:
                print("Registered users:")
                for user in users:
                    print(f"- {user}")
            else:
                print("No users registered yet.")

        elif choice == "4":
            # Migrate existing data
            user_id = input("Enter user ID to migrate existing data to: ").strip()
            if not user_id:
                print("User ID cannot be empty.")
                continue

            SystemMonitor.migrate_existing_data(user_id)
            print(f"\nYou can now login as user '{user_id}' to use your migrated data.")

        elif choice == "5":
            # Exit
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()