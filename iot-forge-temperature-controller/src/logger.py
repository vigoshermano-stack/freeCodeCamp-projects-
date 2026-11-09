"""SQLite logging for forge heat-treat cycles.

Stores a timestamped row for every control-loop iteration so each blade's
thermal history can be reconstructed and verified afterward.
"""

import sqlite3
import datetime


class ForgeLogger:
    def __init__(self, db_path="forge_log.db"):
        self._db = sqlite3.connect(db_path)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS log (
                ts TEXT,
                temp REAL,
                setpoint REAL,
                duty REAL
            )"""
        )
        self._db.commit()

    def log(self, temp, setpoint, duty):
        self._db.execute(
            "INSERT INTO log VALUES (?, ?, ?, ?)",
            (datetime.datetime.now().isoformat(), temp, setpoint, duty),
        )
        self._db.commit()

    def close(self):
        self._db.close()
