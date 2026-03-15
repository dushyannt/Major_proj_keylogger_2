import time
import os
import datetime
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

from pynput import keyboard
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler


class SystemMonitor:

    def __init__(self):

        # files
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

        # feature buffer
        self.feature_buffer = []

        # time window authentication
        self.window_duration = 10
        self.window_start_time = time.time()

        # early detection
        self.min_samples_for_check = 15

        # baseline user profile
        self.user_mean = None

        # create dataset if not exists
        if not os.path.exists(self.dataset_file):
            df = pd.DataFrame(columns=[
                "dwell_time",
                "flight_time",
                "typing_speed",
                "label"
            ])
            df.to_csv(self.dataset_file, index=False)

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

    def save_typing_sample(self, dwell, flight, speed, label):

        df = pd.DataFrame([[dwell, flight, speed, label]],
                          columns=[
                              "dwell_time",
                              "flight_time",
                              "typing_speed",
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
            ["dwell_time", "flight_time", "typing_speed"]
        ].mean()

    # --------------------------------
    # Detect new user
    # --------------------------------

    def detect_new_user(self, dwell, flight, speed):

        if self.user_mean is None:
            return False

        current = pd.Series(
            [dwell, flight, speed],
            index=["dwell_time", "flight_time", "typing_speed"]
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

        X = data[["dwell_time", "flight_time", "typing_speed"]]
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

    def authenticate_user(self, dwell, flight, speed):

        if not os.path.exists(self.model_file):
            return True

        rf = joblib.load(self.model_file)
        iso = joblib.load(self.anomaly_model_file)
        scaler = joblib.load(self.scaler_file)

        sample = pd.DataFrame(
            [[dwell, flight, speed]],
            columns=["dwell_time", "flight_time", "typing_speed"]
        )

        sample_scaled = scaler.transform(sample)

        rf_pred = rf.predict(sample_scaled)
        iso_pred = iso.predict(sample_scaled)

        if rf_pred[0] == 1 and iso_pred[0] == 1:
            print("User authenticated")
            return True
        else:
            self.intrusion_alert()
            return False

    # --------------------------------
    # Intrusion alert
    # --------------------------------

    def intrusion_alert(self):

        print("🚨 SECURITY ALERT 🚨")
        print("Unknown typing behaviour detected")

        with open("security_log.txt", "a") as f:
            f.write(
                f"{datetime.datetime.now()} Intruder detected\n"
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

            if self.last_release_time:
                flight_time = press_time - self.last_release_time
            else:
                flight_time = 0

            self.key_press_times[key] = (press_time, flight_time)

        except:
            pass

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

                self.feature_buffer.append((dwell, flight, speed))

                # early anomaly detection
                if len(self.feature_buffer) >= self.min_samples_for_check:

                    avg_dwell = np.mean([x[0] for x in self.feature_buffer])
                    avg_flight = np.mean([x[1] for x in self.feature_buffer])
                    avg_speed = np.mean([x[2] for x in self.feature_buffer])

                    if os.path.exists(self.anomaly_model_file):

                        iso = joblib.load(self.anomaly_model_file)
                        scaler = joblib.load(self.scaler_file)

                        sample = pd.DataFrame(
                            [[avg_dwell, avg_flight, avg_speed]],
                            columns=[
                                "dwell_time",
                                "flight_time",
                                "typing_speed"
                            ]
                        )

                        sample_scaled = scaler.transform(sample)

                        anomaly = iso.predict(sample_scaled)

                        if anomaly[0] == -1:

                            print("\n🚨 EARLY INTRUDER DETECTION 🚨\n")

                            self.intrusion_alert()
                            self.save_typing_sample(avg_dwell, avg_flight, avg_speed, label=0)
                            self.feature_buffer.clear()
                            self.window_start_time = time.time()

                            return

                # time window authentication
                if time.time() - self.window_start_time >= self.window_duration:

                    print("\nAnalyzing typing behaviour...\n")

                    avg_dwell = np.mean([x[0] for x in self.feature_buffer])
                    avg_flight = np.mean([x[1] for x in self.feature_buffer])
                    avg_speed = np.mean([x[2] for x in self.feature_buffer])

                    if self.detect_new_user(avg_dwell, avg_flight, avg_speed):

                        print("\nNew typing pattern detected\n")

                        self.save_typing_sample(
                            avg_dwell, avg_flight, avg_speed, label=0
                        )

                    else:

                        self.save_typing_sample(
                            avg_dwell, avg_flight, avg_speed, label=1
                        )

                    self.authenticate_user(
                        avg_dwell, avg_flight, avg_speed
                    )

                    self.feature_buffer.clear()
                    self.window_start_time = time.time()

            self.last_release_time = release_time

        except:
            pass

        if key == keyboard.Key.esc:
            return False

    # --------------------------------
    # Start system
    # --------------------------------

    def start(self):

        print("Start typing...")
        print("Press ESC to stop\n")

        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:

            listener.join()

        self.train_model()

        self.visualize_typing_behavior()


if __name__ == "__main__":

    monitor = SystemMonitor()

    monitor.start()