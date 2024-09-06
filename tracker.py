import datetime
import json
from collections import deque

class PollyUsageTracker:
    def __init__(self, max_log_entries=100):
        self.log = deque(maxlen=max_log_entries)
        self.total_characters = 0
        self.total_requests = 0

    def add_entry(self, text_length, voice_id):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "characters": text_length,
            "voice_id": voice_id,
        }
        self.log.appendleft(entry)
        self.total_characters += text_length
        self.total_requests += 1

    def get_log(self):
        return list(self.log)

    def get_summary(self):
        return {
            "total_characters": self.total_characters,
            "total_requests": self.total_requests,
            "average_characters_per_request": self.total_characters / self.total_requests if self.total_requests > 0 else 0
        }

    def save_to_file(self, filename="polly_usage_log.json"):
        data = {
            "log": list(self.log),
            "summary": self.get_summary()
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filename="polly_usage_log.json"):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                self.log = deque(data["log"], maxlen=self.log.maxlen)
                self.total_characters = data["summary"]["total_characters"]
                self.total_requests = data["summary"]["total_requests"]
        except FileNotFoundError:
            print(f"Log file {filename} not found. Starting with empty log.")