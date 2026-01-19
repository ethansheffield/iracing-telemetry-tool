import json
import os
import uuid
from datetime import datetime
from pathlib import Path


class SessionStorage:
    SESSION_TYPES = {
        0: "Testing",
        1: "Practice",
        2: "Qualifying",
        3: "Warmup",
        4: "Race"
    }

    def __init__(self, base_dir="data/sessions"):
        self.base_dir = Path(base_dir)
        self.session_id = None
        self.session_data = None
        self.current_lap = None
        self.current_lap_number = None
        self.metadata = None

    def initialize_session(self, track_name, track_config, car_name,
                          session_type_id, driver_name):
        self.session_id = str(uuid.uuid4())
        session_type = self.SESSION_TYPES.get(session_type_id, "Unknown")

        self.metadata = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "track_name": track_name,
            "track_config": track_config,
            "car_name": car_name,
            "session_type": session_type,
            "session_type_id": session_type_id,
            "driver_name": driver_name,
            "total_laps": 0
        }

        self.session_data = {
            "metadata": self.metadata,
            "laps": []
        }

        self.current_lap_number = 0
        self._start_new_lap(0)

        return self.session_id

    def _start_new_lap(self, lap_number):
        self.current_lap_number = lap_number
        self.current_lap = {
            "lap_number": lap_number,
            "lap_time": None,
            "telemetry": []
        }

    def add_telemetry_sample(self, sample):
        if self.current_lap is None:
            return

        self.current_lap["telemetry"].append(sample)

    def complete_lap(self, lap_time):
        if self.current_lap is None:
            return None

        self.current_lap["lap_time"] = lap_time
        self.session_data["laps"].append(self.current_lap)
        self.metadata["total_laps"] = len(self.session_data["laps"])

        completed_lap = self.current_lap_number
        self._start_new_lap(self.current_lap_number + 1)

        return completed_lap

    def _get_session_directory(self):
        track_name = self.metadata["track_name"].replace(" ", "_").replace("/", "-")
        session_type = self.metadata["session_type"].replace(" ", "_")
        return self.base_dir / track_name / session_type

    def _get_session_filename(self):
        timestamp = datetime.fromisoformat(self.metadata["timestamp"])
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{timestamp_str}_{self.session_id[:8]}.json"

    def finalize_session(self, include_incomplete_lap=True):
        if self.session_data is None:
            return None

        if include_incomplete_lap and self.current_lap and len(self.current_lap["telemetry"]) > 0:
            self.current_lap["lap_time"] = None
            self.session_data["laps"].append(self.current_lap)
            self.metadata["total_laps"] = len(self.session_data["laps"])

        if len(self.session_data["laps"]) == 0:
            return None

        session_dir = self._get_session_directory()
        session_dir.mkdir(parents=True, exist_ok=True)

        filename = self._get_session_filename()
        filepath = session_dir / filename

        with open(filepath, 'w') as f:
            json.dump(self.session_data, f, indent=2)

        return str(filepath)

    def reset(self):
        self.session_id = None
        self.session_data = None
        self.current_lap = None
        self.current_lap_number = None
        self.metadata = None


def list_all_sessions(base_dir="data/sessions"):
    base_path = Path(base_dir)

    if not base_path.exists():
        return []

    sessions = []

    for json_file in base_path.rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                session_data = json.load(f)
                metadata = session_data.get('metadata', {})

                laps = session_data.get('laps', [])
                total_duration = 0
                for lap in laps:
                    if lap.get('lap_time'):
                        total_duration += lap['lap_time']

                sessions.append({
                    'filepath': str(json_file),
                    'session_id': metadata.get('session_id', 'Unknown'),
                    'timestamp': metadata.get('timestamp', ''),
                    'track_name': metadata.get('track_name', 'Unknown'),
                    'track_config': metadata.get('track_config', ''),
                    'car_name': metadata.get('car_name', 'Unknown'),
                    'session_type': metadata.get('session_type', 'Unknown'),
                    'driver_name': metadata.get('driver_name', 'Unknown'),
                    'total_laps': metadata.get('total_laps', 0),
                    'duration': total_duration
                })

        except (json.JSONDecodeError, IOError):
            continue

    sessions.sort(key=lambda x: x['timestamp'], reverse=True)

    return sessions


def load_session(session_id, base_dir="data/sessions"):
    base_path = Path(base_dir)

    if not base_path.exists():
        return None, None

    for json_file in base_path.rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                session_data = json.load(f)
                stored_id = session_data.get('metadata', {}).get('session_id', '')

                if stored_id == session_id or stored_id.startswith(session_id):
                    return session_data, str(json_file)

        except (json.JSONDecodeError, IOError):
            continue

    return None, None
