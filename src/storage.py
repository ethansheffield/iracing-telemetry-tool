import json
import os
import uuid
from datetime import datetime
from pathlib import Path


class SessionStorage:
    """
    Manages storage of telemetry data to disk.

    Organizes sessions by track and session type, stores complete lap data
    with telemetry samples, and handles graceful completion of sessions.
    """

    # Map session type IDs to readable names
    SESSION_TYPES = {
        0: "Testing",
        1: "Practice",
        2: "Qualifying",
        3: "Warmup",
        4: "Race"
    }

    def __init__(self, base_dir="data/sessions"):
        """
        Initialize session storage.

        Args:
            base_dir (str): Base directory for storing session data
        """
        self.base_dir = Path(base_dir)
        self.session_id = None
        self.session_data = None
        self.current_lap = None
        self.current_lap_number = None
        self.metadata = None

    def initialize_session(self, track_name, track_config, car_name,
                          session_type_id, driver_name):
        """
        Initialize a new session with metadata.

        Args:
            track_name (str): Name of the track
            track_config (str): Track configuration (e.g., "Road Course", "Oval")
            car_name (str): Name of the car being driven
            session_type_id (int): Session type ID (0-4)
            driver_name (str): Name of the driver

        Returns:
            str: Unique session ID
        """
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

        # Start first lap
        self.current_lap_number = 0
        self._start_new_lap(0)

        return self.session_id

    def _start_new_lap(self, lap_number):
        """
        Start tracking a new lap.

        Args:
            lap_number (int): Lap number
        """
        self.current_lap_number = lap_number
        self.current_lap = {
            "lap_number": lap_number,
            "lap_time": None,
            "telemetry": []
        }

    def add_telemetry_sample(self, sample):
        """
        Add a telemetry sample to the current lap.

        Args:
            sample (dict): Telemetry data point containing:
                - time: session time
                - lap_dist: distance around track (meters)
                - lap_dist_pct: percentage around track (0-1)
                - speed: speed in m/s
                - throttle: throttle position (0-1)
                - brake: brake position (0-1)
                - steering: steering wheel angle (-1 to 1)
                - gear: current gear
                - rpm: engine RPM
        """
        if self.current_lap is None:
            return

        self.current_lap["telemetry"].append(sample)

    def complete_lap(self, lap_time):
        """
        Complete the current lap and prepare for next lap.

        Args:
            lap_time (float): Lap time in seconds

        Returns:
            int: The lap number that was completed
        """
        if self.current_lap is None:
            return None

        self.current_lap["lap_time"] = lap_time

        # Add completed lap to session data
        self.session_data["laps"].append(self.current_lap)

        # Update total lap count
        self.metadata["total_laps"] = len(self.session_data["laps"])

        completed_lap = self.current_lap_number

        # Start next lap
        self._start_new_lap(self.current_lap_number + 1)

        return completed_lap

    def _get_session_directory(self):
        """
        Generate directory path for current session.

        Returns:
            Path: Directory path for session files
        """
        track_name = self.metadata["track_name"].replace(" ", "_").replace("/", "-")
        session_type = self.metadata["session_type"].replace(" ", "_")

        session_dir = self.base_dir / track_name / session_type
        return session_dir

    def _get_session_filename(self):
        """
        Generate filename for current session.

        Returns:
            str: Filename in format {timestamp}_{session_id}.json
        """
        timestamp = datetime.fromisoformat(self.metadata["timestamp"])
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{timestamp_str}_{self.session_id[:8]}.json"

    def finalize_session(self, include_incomplete_lap=True):
        """
        Write complete session data to disk.

        Args:
            include_incomplete_lap (bool): Whether to include current incomplete lap

        Returns:
            str: Full path to saved session file, or None if no data
        """
        if self.session_data is None:
            return None

        # Optionally include incomplete lap if it has any telemetry
        if include_incomplete_lap and self.current_lap and len(self.current_lap["telemetry"]) > 0:
            self.current_lap["lap_time"] = None  # Mark as incomplete
            self.session_data["laps"].append(self.current_lap)
            self.metadata["total_laps"] = len(self.session_data["laps"])

        # Don't save if no laps were recorded
        if len(self.session_data["laps"]) == 0:
            return None

        # Create directory structure
        session_dir = self._get_session_directory()
        session_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename and full path
        filename = self._get_session_filename()
        filepath = session_dir / filename

        # Write JSON to file
        with open(filepath, 'w') as f:
            json.dump(self.session_data, f, indent=2)

        return str(filepath)

    def reset(self):
        """Reset storage for a new session."""
        self.session_id = None
        self.session_data = None
        self.current_lap = None
        self.current_lap_number = None
        self.metadata = None


def list_all_sessions(base_dir="data/sessions"):
    """
    Scan the sessions directory and return metadata for all sessions.

    Args:
        base_dir (str): Base directory containing session data

    Returns:
        list: List of dicts containing session metadata and filepath
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        return []

    sessions = []

    # Recursively find all JSON files in session directory
    for json_file in base_path.rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                session_data = json.load(f)
                metadata = session_data.get('metadata', {})

                # Calculate session duration from laps
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

        except (json.JSONDecodeError, IOError) as e:
            # Skip files that can't be parsed
            continue

    # Sort by timestamp (newest first)
    sessions.sort(key=lambda x: x['timestamp'], reverse=True)

    return sessions


def load_session(session_id, base_dir="data/sessions"):
    """
    Load a specific session by session ID.

    Args:
        session_id (str): Full or partial session ID to load
        base_dir (str): Base directory containing session data

    Returns:
        tuple: (session_data dict, filepath str) or (None, None) if not found
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        return None, None

    # Search for session file containing this ID
    for json_file in base_path.rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                session_data = json.load(f)
                stored_id = session_data.get('metadata', {}).get('session_id', '')

                # Match full ID or partial ID (first 8 chars)
                if stored_id == session_id or stored_id.startswith(session_id):
                    return session_data, str(json_file)

        except (json.JSONDecodeError, IOError):
            continue

    return None, None
