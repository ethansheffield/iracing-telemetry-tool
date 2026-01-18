import irsdk
import time
import sys
from src.storage import SessionStorage


class TelemetryCapture:
    """
    Captures live telemetry data from iRacing using the iRacing SDK.

    This class manages the connection to iRacing's shared memory interface,
    polls telemetry data at 60Hz for real-time monitoring, and stores
    complete session data to disk.
    """

    def __init__(self, poll_rate=60):
        """
        Initialize the telemetry capture system.

        Args:
            poll_rate (int): Polling frequency in Hz (default: 60)
        """
        self.ir = irsdk.IRSDK()
        self.poll_interval = 1.0 / poll_rate  # Convert Hz to seconds
        self.is_connected = False
        self.storage = SessionStorage()

        # Track session and lap state
        self.current_session_num = None
        self.current_lap = None
        self.last_lap_time = None
        self.best_lap_time = None
        self.session_start_time = None

    def connect(self):
        """
        Establish connection to iRacing.

        The iRacing SDK uses shared memory to communicate with the sim.
        This method attempts to connect to that shared memory segment.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.ir.startup():
            self.is_connected = True
            print("✓ Connected to iRacing")
            return True
        return False

    def disconnect(self):
        """Safely disconnect from iRacing and cleanup resources."""
        if self.is_connected:
            self.ir.shutdown()
            self.is_connected = False
            print("\n✓ Disconnected from iRacing")

    def wait_for_iracing(self):
        """
        Wait for iRacing to start, checking every second.
        Displays a waiting message until connection is established.
        """
        print("Waiting for iRacing...")
        while not self.connect():
            time.sleep(1)

    def get_session_metadata(self):
        """
        Extract session metadata from iRacing SDK.

        Returns:
            dict: Session metadata or None if unavailable
        """
        try:
            # Get session info from SDK
            session_info = self.ir['SessionInfo']
            weekend_info = self.ir['WeekendInfo']
            driver_info = self.ir['DriverInfo']

            if not session_info or not weekend_info or not driver_info:
                return None

            # Extract track information
            track_name = weekend_info.get('TrackDisplayName', 'Unknown Track')
            track_config = weekend_info.get('TrackConfigName', '')

            # Extract driver information
            driver = driver_info.get('Drivers', [{}])[0]
            driver_name = driver.get('UserName', 'Unknown Driver')

            # Extract car information
            car_name = driver.get('CarScreenName', 'Unknown Car')

            # Get current session type - map string to ID
            session_num = self.ir['SessionNum']
            sessions = session_info.get('Sessions', [])

            session_type_str = 'Unknown'
            session_type_id = 0

            if session_num is not None and session_num < len(sessions):
                session_type_str = sessions[session_num].get('SessionType', 'Unknown')

                # Map session type string to ID
                type_map = {
                    'Offline Testing': 0,
                    'Practice': 1,
                    'Open Practice': 1,
                    'Lone Practice': 1,
                    'Qualify': 2,
                    'Open Qualify': 2,
                    'Lone Qualify': 2,
                    'Warmup': 3,
                    'Race': 4
                }
                session_type_id = type_map.get(session_type_str, 0)

            return {
                'track_name': track_name,
                'track_config': track_config,
                'car_name': car_name,
                'session_type_id': session_type_id,
                'driver_name': driver_name,
                'session_num': session_num
            }

        except Exception as e:
            return None

    def get_telemetry(self):
        """
        Retrieve current telemetry data from iRacing.

        Returns:
            dict: Dictionary containing telemetry values, or None if unavailable
        """
        # Freeze the data to prevent changes during read
        self.ir.freeze_var_buffer_latest()

        # Extract comprehensive telemetry values from the SDK
        try:
            telemetry = {
                # For display
                'throttle': self.ir['Throttle'],
                'brake': self.ir['Brake'],
                'speed': self.ir['Speed'],
                'gear': self.ir['Gear'],
                'lap': self.ir['Lap'],
                'lap_dist': self.ir['LapDist'],

                # Additional data for storage
                'time': self.ir['SessionTime'],
                'lap_dist_pct': self.ir['LapDistPct'],
                'steering': self.ir['SteeringWheelAngle'],
                'rpm': self.ir['RPM'],
                'lap_last_lap_time': self.ir['LapLastLapTime'],
                'session_num': self.ir['SessionNum'],

                # Vehicle dynamics (for AI analysis)
                'lat_accel': self.ir['LatAccel'],
                'long_accel': self.ir['LongAccel'],
                'yaw_rate': self.ir['YawRate'],
                'steering_wheel_angle': self.ir['SteeringWheelAngle']
            }

            return telemetry
        except Exception as e:
            return None

    def format_telemetry_line(self, data):
        """
        Format telemetry data for console display.

        Args:
            data (dict): Telemetry data dictionary

        Returns:
            str: Formatted string for display
        """
        if not data:
            return "No data available"

        # Convert speed from m/s to mph (multiply by 2.237)
        speed_mph = data['speed'] * 2.237 if data['speed'] is not None else 0

        # Format percentages for throttle and brake
        throttle_pct = (data['throttle'] * 100) if data['throttle'] is not None else 0
        brake_pct = (data['brake'] * 100) if data['brake'] is not None else 0

        # Handle gear display (negative values indicate reverse)
        gear = data['gear'] if data['gear'] is not None else 0
        gear_display = 'R' if gear < 0 else ('N' if gear == 0 else str(gear))

        # Get lap information
        lap = data['lap'] if data['lap'] is not None else 0
        lap_dist = data['lap_dist'] if data['lap_dist'] is not None else 0

        return (f"Throttle: {throttle_pct:5.1f}% | "
                f"Brake: {brake_pct:5.1f}% | "
                f"Speed: {speed_mph:6.1f} mph | "
                f"Gear: {gear_display:>2} | "
                f"Lap: {lap:3d} | "
                f"LapDist: {lap_dist:7.1f}m")

    def initialize_new_session(self):
        """Initialize a new session when detected."""
        metadata = self.get_session_metadata()
        if not metadata:
            return False

        session_id = self.storage.initialize_session(
            track_name=metadata['track_name'],
            track_config=metadata['track_config'],
            car_name=metadata['car_name'],
            session_type_id=metadata['session_type_id'],
            driver_name=metadata['driver_name']
        )

        self.current_session_num = metadata['session_num']
        self.current_lap = None
        self.last_lap_time = None
        self.best_lap_time = None
        self.session_start_time = time.time()

        # Display session info
        print("\n" + "="*80)
        print(f"Session Started: {metadata['track_name']}")
        if metadata['track_config']:
            print(f"Configuration: {metadata['track_config']}")
        print(f"Car: {metadata['car_name']}")
        print(f"Driver: {metadata['driver_name']}")
        print(f"Session Type: {self.storage.SESSION_TYPES.get(metadata['session_type_id'], 'Unknown')}")
        print(f"Session ID: {session_id[:8]}")
        print("="*80 + "\n")

        return True

    def save_current_session(self, include_incomplete_lap=True):
        """Save the current session to disk with summary and auto-export."""
        if not self.storage.session_data:
            return None

        filepath = self.storage.finalize_session(include_incomplete_lap)
        if not filepath:
            return None

        # Calculate session summary
        laps = self.storage.session_data.get('laps', [])
        total_laps = len(laps)
        total_points = sum(len(lap.get('telemetry', [])) for lap in laps)

        # Get file size
        import os
        import shutil
        from src.exporter import DataExporter

        file_size = os.path.getsize(filepath)
        size_mb = file_size / (1024 * 1024)

        # Auto-export complete session to CSV and copy JSON
        csv_path = None
        json_copy_path = None

        try:
            exporter = DataExporter()

            # Export complete session CSV
            csv_path = exporter.export_complete_session_to_csv(self.storage.session_data)

            # Copy session JSON to exports folder
            metadata = self.storage.session_data.get('metadata', {})
            track_name = metadata.get('track_name', 'Unknown').replace(' ', '_').replace('/', '-')
            session_type = metadata.get('session_type', 'Unknown').replace(' ', '_')
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"{track_name}_{session_type}_{timestamp}_session.json"
            json_copy_path = os.path.join(exporter.export_dir, json_filename)
            shutil.copy2(filepath, json_copy_path)

        except Exception as e:
            print(f"Warning: Auto-export failed: {e}")

        # Display enhanced summary
        print("\n" + "="*80)
        print("SESSION SUMMARY")
        print("="*80)
        print(f"Total Laps:        {total_laps}")
        if self.best_lap_time:
            print(f"Best Lap Time:     {self.best_lap_time:.3f}s")
        print(f"Telemetry Points:  {total_points:,}")
        print(f"\nFiles saved:")
        print(f"  Session data: {filepath}")
        if csv_path:
            print(f"  Complete CSV: {csv_path}")
        if json_copy_path:
            print(f"  Session JSON: {json_copy_path}")
        print(f"\nCSV includes: throttle, brake, steering, speed, gear, rpm, lat/long accel, yaw rate")
        print(f"\nNext steps:")
        print(f"  • Analyze with AI using the complete CSV")
        session_id = self.storage.session_data.get('metadata', {}).get('session_id', '')[:8]
        print(f"  • View details: python main.py info --session {session_id}")
        print(f"  • Export specific lap: python main.py export --session {session_id} --lap 2")
        print(f"  • Compare laps: python main.py export --session {session_id} --lap 1 2 3")
        print("="*80)

        return filepath

    def process_telemetry(self, telemetry):
        """
        Process telemetry data: store it and detect session/lap changes.

        Args:
            telemetry (dict): Current telemetry snapshot

        Returns:
            bool: True if processing successful
        """
        if not telemetry:
            return False

        # Check for session change
        session_num = telemetry.get('session_num')
        if session_num is not None and session_num != self.current_session_num:
            # Save previous session if exists
            if self.current_session_num is not None:
                self.save_current_session(include_incomplete_lap=False)
                self.storage.reset()

            # Initialize new session
            if not self.initialize_new_session():
                return False

        # Ensure we have an active session
        if self.storage.session_data is None:
            if not self.initialize_new_session():
                return False

        # Check for lap change
        current_lap_num = telemetry.get('lap')
        if current_lap_num is not None:
            if self.current_lap is None:
                self.current_lap = current_lap_num
            elif current_lap_num > self.current_lap:
                # Lap completed!
                lap_time = telemetry.get('lap_last_lap_time')
                if lap_time is not None and lap_time > 0:
                    self.storage.complete_lap(lap_time)

                    # Update best lap time
                    is_best = False
                    if self.best_lap_time is None or lap_time < self.best_lap_time:
                        self.best_lap_time = lap_time
                        is_best = True

                    # Display lap completion
                    delta_str = ""
                    if not is_best and self.best_lap_time:
                        delta = lap_time - self.best_lap_time
                        delta_str = f" (+{delta:.3f}s)"

                    best_indicator = " 🏆 NEW BEST LAP!" if is_best else delta_str

                    print(f"\n✓ Lap {self.current_lap} completed: {lap_time:.3f}s{best_indicator}")

                self.current_lap = current_lap_num

        # Store telemetry sample
        sample = {
            'time': telemetry.get('time', 0),
            'lap_dist': telemetry.get('lap_dist', 0),
            'lap_dist_pct': telemetry.get('lap_dist_pct', 0),
            'speed': telemetry.get('speed', 0),
            'throttle': telemetry.get('throttle', 0),
            'brake': telemetry.get('brake', 0),
            'steering': telemetry.get('steering', 0),
            'gear': telemetry.get('gear', 0),
            'rpm': telemetry.get('rpm', 0),
            # Vehicle dynamics
            'lat_accel': telemetry.get('lat_accel', 0),
            'long_accel': telemetry.get('long_accel', 0),
            'yaw_rate': telemetry.get('yaw_rate', 0),
            'steering_wheel_angle': telemetry.get('steering_wheel_angle', 0)
        }
        self.storage.add_telemetry_sample(sample)

        return True

    def run(self):
        """
        Main capture loop - runs continuously until Ctrl+C.

        This loop:
        1. Waits for iRacing to start
        2. Polls telemetry at specified rate
        3. Displays live data to console
        4. Stores data to disk with lap-by-lap organization
        5. Handles disconnections and session changes gracefully
        """
        try:
            # Wait for iRacing to start
            self.wait_for_iracing()

            print("\n" + "="*80)
            print("Live Telemetry Capture (Press Ctrl+C to stop)")
            print("="*80 + "\n")

            # Main telemetry capture loop
            while True:
                try:
                    # Check if we're still connected to iRacing
                    if not self.ir.is_connected:
                        print("\n⚠ Lost connection to iRacing")
                        # Save session before disconnecting
                        self.save_current_session(include_incomplete_lap=True)
                        self.storage.reset()
                        self.current_session_num = None
                        self.current_lap = None
                        self.best_lap_time = None
                        self.is_connected = False
                        self.wait_for_iracing()
                        continue

                    # Get and process telemetry data
                    telemetry = self.get_telemetry()

                    if telemetry:
                        # Process and store telemetry
                        self.process_telemetry(telemetry)

                        # Display live telemetry (use \r to overwrite line)
                        print(f"\r{self.format_telemetry_line(telemetry)}", end='', flush=True)

                    # Wait before next poll (60Hz = ~16ms between polls)
                    time.sleep(self.poll_interval)

                except Exception as e:
                    print(f"\n⚠ Error in capture loop: {e}")
                    time.sleep(0.1)

        except KeyboardInterrupt:
            # User pressed Ctrl+C - clean shutdown
            print("\n\n✓ Capture stopped by user")
        except Exception as e:
            # Catch any unexpected errors
            print(f"\n✗ Error during capture: {e}")
            sys.exit(1)
        finally:
            # Save final session and disconnect
            self.save_current_session(include_incomplete_lap=True)
            self.disconnect()


if __name__ == "__main__":
    # Allow running this module directly for testing
    capture = TelemetryCapture()
    capture.run()
