import csv
import json
import numpy as np
from datetime import datetime
from pathlib import Path


class DataExporter:
    """
    Exports telemetry data from stored sessions to CSV format.

    Handles loading session data and converting lap telemetry to
    CSV files for external analysis tools.
    """

    def __init__(self, export_dir="data/exports"):
        """
        Initialize the data exporter.

        Args:
            export_dir (str): Directory to save exported CSV files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def load_session(self, session_filepath):
        """
        Load session data from JSON file.

        Args:
            session_filepath (str): Path to session JSON file

        Returns:
            dict: Session data or None if file not found
        """
        try:
            with open(session_filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing session file: {e}")
            return None

    def export_complete_session_to_csv(self, session_data):
        """
        Export all laps from a session to a single CSV file.

        Args:
            session_data (dict): Complete session data

        Returns:
            str: Path to exported CSV file, or None if export failed
        """
        laps = session_data.get('laps', [])
        if not laps:
            print("Error: No laps found in session")
            return None

        # Generate filename
        metadata = session_data.get('metadata', {})
        track_name = metadata.get('track_name', 'Unknown').replace(' ', '_').replace('/', '-')
        session_type = metadata.get('session_type', 'Unknown').replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{track_name}_{session_type}_{timestamp}_complete.csv"
        filepath = self.export_dir / filename

        # Write CSV file
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['lap', 'time', 'distance', 'distance_pct', 'speed',
                         'throttle', 'brake', 'steering', 'gear', 'rpm',
                         'lat_accel', 'long_accel', 'yaw_rate', 'steering_wheel_angle']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for lap in laps:
                # Convert 0-based lap_number to 1-based for output
                lap_number_display = lap.get('lap_number', 0) + 1
                telemetry = lap.get('telemetry', [])

                for sample in telemetry:
                    writer.writerow({
                        'lap': lap_number_display,
                        'time': sample.get('time', 0),
                        'distance': sample.get('lap_dist', 0),
                        'distance_pct': sample.get('lap_dist_pct', 0),
                        'speed': sample.get('speed', 0),
                        'throttle': sample.get('throttle', 0),
                        'brake': sample.get('brake', 0),
                        'steering': sample.get('steering', 0),
                        'gear': sample.get('gear', 0),
                        'rpm': sample.get('rpm', 0),
                        'lat_accel': sample.get('lat_accel', 0),
                        'long_accel': sample.get('long_accel', 0),
                        'yaw_rate': sample.get('yaw_rate', 0),
                        'steering_wheel_angle': sample.get('steering_wheel_angle', 0)
                    })

        return str(filepath)

    def export_lap_to_csv(self, session_data, lap_number):
        """
        Export a single lap's telemetry data to CSV.

        Args:
            session_data (dict): Complete session data
            lap_number (int): Lap number to export (1-based, as user sees it)

        Returns:
            str: Path to exported CSV file, or None if export failed
        """
        # Convert from 1-based user input to 0-based array index
        lap_index = lap_number - 1

        # Find the requested lap
        lap_data = None
        for lap in session_data.get('laps', []):
            if lap.get('lap_number') == lap_index:
                lap_data = lap
                break

        if not lap_data:
            print(f"Error: Lap {lap_number} not found in session")
            return None

        # Check if lap has telemetry data
        telemetry = lap_data.get('telemetry', [])
        if not telemetry or len(telemetry) == 0:
            print(f"Error: Lap {lap_number} has no telemetry data")
            return None

        # Generate filename
        metadata = session_data.get('metadata', {})
        track_name = metadata.get('track_name', 'Unknown').replace(' ', '_').replace('/', '-')
        session_type = metadata.get('session_type', 'Unknown').replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{track_name}_{session_type}_lap{lap_number}_{timestamp}.csv"
        filepath = self.export_dir / filename

        # Write CSV file
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['lap', 'time', 'distance', 'distance_pct', 'speed',
                         'throttle', 'brake', 'steering', 'gear', 'rpm',
                         'lat_accel', 'long_accel', 'yaw_rate', 'steering_wheel_angle']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for sample in telemetry:
                writer.writerow({
                    'lap': lap_number,
                    'time': sample.get('time', 0),
                    'distance': sample.get('lap_dist', 0),
                    'distance_pct': sample.get('lap_dist_pct', 0),
                    'speed': sample.get('speed', 0),
                    'throttle': sample.get('throttle', 0),
                    'brake': sample.get('brake', 0),
                    'steering': sample.get('steering', 0),
                    'gear': sample.get('gear', 0),
                    'rpm': sample.get('rpm', 0),
                    'lat_accel': sample.get('lat_accel', 0),
                    'long_accel': sample.get('long_accel', 0),
                    'yaw_rate': sample.get('yaw_rate', 0),
                    'steering_wheel_angle': sample.get('steering_wheel_angle', 0)
                })

        return str(filepath)

    def export_multiple_laps_to_csv(self, session_data, lap_numbers):
        """
        Export multiple laps' telemetry data to a single CSV.

        Args:
            session_data (dict): Complete session data
            lap_numbers (list): List of lap numbers to export (1-based, as user sees them)

        Returns:
            str: Path to exported CSV file, or None if export failed
        """
        # Collect all requested laps
        laps_to_export = []
        for lap_number in lap_numbers:
            # Convert from 1-based user input to 0-based array index
            lap_index = lap_number - 1
            for lap in session_data.get('laps', []):
                if lap.get('lap_number') == lap_index:
                    laps_to_export.append(lap)
                    break

        if not laps_to_export:
            print("Error: None of the requested laps found in session")
            return None

        # Generate filename
        metadata = session_data.get('metadata', {})
        track_name = metadata.get('track_name', 'Unknown').replace(' ', '_').replace('/', '-')
        session_type = metadata.get('session_type', 'Unknown').replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        lap_range = f"{min(lap_numbers)}-{max(lap_numbers)}" if len(lap_numbers) > 1 else str(lap_numbers[0])
        filename = f"{track_name}_{session_type}_laps{lap_range}_{timestamp}.csv"
        filepath = self.export_dir / filename

        # Write CSV file
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['lap', 'time', 'distance', 'distance_pct', 'speed',
                         'throttle', 'brake', 'steering', 'gear', 'rpm',
                         'lat_accel', 'long_accel', 'yaw_rate', 'steering_wheel_angle']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for lap in laps_to_export:
                # Convert 0-based lap_number to 1-based for CSV output
                lap_number_display = lap.get('lap_number', 0) + 1
                telemetry = lap.get('telemetry', [])

                for sample in telemetry:
                    writer.writerow({
                        'lap': lap_number_display,
                        'time': sample.get('time', 0),
                        'distance': sample.get('lap_dist', 0),
                        'distance_pct': sample.get('lap_dist_pct', 0),
                        'speed': sample.get('speed', 0),
                        'throttle': sample.get('throttle', 0),
                        'brake': sample.get('brake', 0),
                        'steering': sample.get('steering', 0),
                        'gear': sample.get('gear', 0),
                        'rpm': sample.get('rpm', 0),
                        'lat_accel': sample.get('lat_accel', 0),
                        'long_accel': sample.get('long_accel', 0),
                        'yaw_rate': sample.get('yaw_rate', 0),
                        'steering_wheel_angle': sample.get('steering_wheel_angle', 0)
                    })

        return str(filepath)

    def _interpolate_telemetry(self, telemetry, target_distances):
        """
        Interpolate telemetry data to align with target distance points.

        Args:
            telemetry (list): List of telemetry samples
            target_distances (np.array): Array of target lap_dist_pct values

        Returns:
            dict: Dictionary mapping telemetry fields to interpolated arrays
        """
        if not telemetry:
            return None

        # Extract distance and telemetry values
        distances = np.array([s.get('lap_dist_pct', 0) for s in telemetry])
        speed = np.array([s.get('speed', 0) for s in telemetry])
        throttle = np.array([s.get('throttle', 0) for s in telemetry])
        brake = np.array([s.get('brake', 0) for s in telemetry])
        steering = np.array([s.get('steering', 0) for s in telemetry])
        gear = np.array([s.get('gear', 0) for s in telemetry])
        rpm = np.array([s.get('rpm', 0) for s in telemetry])
        lat_accel = np.array([s.get('lat_accel', 0) for s in telemetry])
        long_accel = np.array([s.get('long_accel', 0) for s in telemetry])
        yaw_rate = np.array([s.get('yaw_rate', 0) for s in telemetry])
        steering_wheel_angle = np.array([s.get('steering_wheel_angle', 0) for s in telemetry])

        # Interpolate each field to target distances
        interpolated = {
            'speed': np.interp(target_distances, distances, speed),
            'throttle': np.interp(target_distances, distances, throttle),
            'brake': np.interp(target_distances, distances, brake),
            'steering': np.interp(target_distances, distances, steering),
            'gear': np.interp(target_distances, distances, gear),
            'rpm': np.interp(target_distances, distances, rpm),
            'lat_accel': np.interp(target_distances, distances, lat_accel),
            'long_accel': np.interp(target_distances, distances, long_accel),
            'yaw_rate': np.interp(target_distances, distances, yaw_rate),
            'steering_wheel_angle': np.interp(target_distances, distances, steering_wheel_angle)
        }

        return interpolated

    def export_comparison_csv(self, session_data, lap_numbers):
        """
        Export multi-lap comparison CSV with distance-aligned data.

        Args:
            session_data (dict): Complete session data
            lap_numbers (list): List of lap numbers to compare (1-based, as user sees them)

        Returns:
            str: Path to exported CSV file, or None if export failed
        """
        # Collect telemetry for all requested laps
        laps_data = []

        for lap_num in lap_numbers:
            # Convert from 1-based user input to 0-based array index
            lap_index = lap_num - 1

            # Get full lap telemetry
            lap_data = None
            for lap in session_data.get('laps', []):
                if lap.get('lap_number') == lap_index:
                    lap_data = lap
                    break

            if lap_data and lap_data.get('telemetry'):
                laps_data.append({
                    'lap_number': lap_num,  # Keep user-facing lap number for output
                    'telemetry': lap_data['telemetry']
                })
            else:
                print(f"Error: Lap {lap_num} not found or has no telemetry")
                return None

        if not laps_data:
            print("Error: No valid laps to compare")
            return None

        if len(laps_data) < 2:
            print("Warning: Only one valid lap found, comparison requires at least 2 laps")
            return None

        # Create common distance array (every 0.1% of lap distance)
        target_distances = np.arange(0, 1.0, 0.001)  # 1000 points around the lap

        # Interpolate all laps to common distance points
        interpolated_laps = []
        for lap_data in laps_data:
            interpolated = self._interpolate_telemetry(
                lap_data['telemetry'],
                target_distances
            )
            if interpolated:
                interpolated_laps.append({
                    'lap_number': lap_data['lap_number'],
                    'data': interpolated
                })

        if not interpolated_laps:
            print("Error: Failed to interpolate telemetry data")
            return None

        # Generate filename
        metadata = session_data.get('metadata', {})
        track_name = metadata.get('track_name', 'Unknown').replace(' ', '_').replace('/', '-')
        session_type = metadata.get('session_type', 'Unknown').replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        lap_range = f"{min(lap_numbers)}-{max(lap_numbers)}" if len(lap_numbers) > 1 else str(lap_numbers[0])
        filename = f"{track_name}_{session_type}_comparison_laps{lap_range}_{timestamp}.csv"
        filepath = self.export_dir / filename

        # Write CSV file
        with open(filepath, 'w', newline='') as csvfile:
            # Build column headers
            fieldnames = ['distance_pct', 'distance']

            for lap_data in interpolated_laps:
                lap_num = lap_data['lap_number']
                fieldnames.extend([
                    f'lap{lap_num}_speed',
                    f'lap{lap_num}_throttle',
                    f'lap{lap_num}_brake',
                    f'lap{lap_num}_steering',
                    f'lap{lap_num}_gear',
                    f'lap{lap_num}_rpm',
                    f'lap{lap_num}_lat_accel',
                    f'lap{lap_num}_long_accel',
                    f'lap{lap_num}_yaw_rate',
                    f'lap{lap_num}_steering_wheel_angle'
                ])

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write data rows
            for i, dist_pct in enumerate(target_distances):
                row = {
                    'distance_pct': dist_pct,
                    'distance': dist_pct * 1000  # Approximate distance in meters (will vary by track)
                }

                for lap_data in interpolated_laps:
                    lap_num = lap_data['lap_number']
                    data = lap_data['data']

                    row[f'lap{lap_num}_speed'] = data['speed'][i]
                    row[f'lap{lap_num}_throttle'] = data['throttle'][i]
                    row[f'lap{lap_num}_brake'] = data['brake'][i]
                    row[f'lap{lap_num}_steering'] = data['steering'][i]
                    row[f'lap{lap_num}_gear'] = int(data['gear'][i])
                    row[f'lap{lap_num}_rpm'] = data['rpm'][i]
                    row[f'lap{lap_num}_lat_accel'] = data['lat_accel'][i]
                    row[f'lap{lap_num}_long_accel'] = data['long_accel'][i]
                    row[f'lap{lap_num}_yaw_rate'] = data['yaw_rate'][i]
                    row[f'lap{lap_num}_steering_wheel_angle'] = data['steering_wheel_angle'][i]

                writer.writerow(row)

        return str(filepath)
