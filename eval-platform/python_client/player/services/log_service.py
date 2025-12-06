import datetime
import os

class LogService:
    def __init__(self, filename="bot_history.log"):
        self.filename = filename
        # Initialize file (append mode)
        with open(self.filename, "a") as f:
            f.write("\n>>> NEW PYTHON SESSION STARTED <<<\n")

    def info(self, message):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        full_message = timestamp + str(message)
        
        # 1. Print to console
        print(full_message)
        
        # 2. Write to file
        self._write_to_file(full_message)

    def log_raw(self, message):
        # Writes raw message without timestamp (good for JSON dumps)
        self._write_to_file(str(message))

    def _write_to_file(self, message):
        try:
            with open(self.filename, "a") as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"Error writing to log: {e}")