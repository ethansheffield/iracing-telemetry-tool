#!/usr/bin/env python3
"""
iRacing Telemetry Analysis Tool - CLI Entry Point

This is the main command-line interface for the telemetry tool.
Use 'python main.py capture' to start capturing telemetry data.
"""

import argparse
import sys
from datetime import datetime
from src.capture import TelemetryCapture
from src.storage import list_all_sessions, load_session
from src.exporter import DataExporter


def cmd_capture(args):
    """
    Handle the 'capture' command - starts live telemetry capture.

    Args:
        args: Parsed command-line arguments
    """
    print("="*80)
    print("iRacing Telemetry Capture")
    print("="*80)
    print()

    # Create and run telemetry capture
    capture = TelemetryCapture(poll_rate=60)
    capture.run()


def cmd_list(args):
    """
    Handle the 'list' command - shows all captured sessions.

    Args:
        args: Parsed command-line arguments
    """
    sessions = list_all_sessions()

    if not sessions:
        print("No sessions found.")
        print("\nCapture your first session with: python main.py capture")
        return

    # Print header
    print("="*120)
    print(f"{'Session ID':<10} | {'Date':<19} | {'Track':<25} | {'Config':<15} | {'Type':<12} | {'Laps':>5} | {'Duration':>10}")
    print("="*120)

    # Print each session
    for session in sessions:
        # Format timestamp
        try:
            dt = datetime.fromisoformat(session['timestamp'])
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            date_str = session['timestamp'][:19]

        # Truncate long names
        track_name = session['track_name'][:25]
        track_config = session['track_config'][:15] if session['track_config'] else '-'

        # Format duration
        duration = session['duration']
        if duration > 0:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = "-"

        # Print row
        session_id_short = session['session_id'][:8]
        print(f"{session_id_short:<10} | {date_str:<19} | {track_name:<25} | {track_config:<15} | "
              f"{session['session_type']:<12} | {session['total_laps']:>5} | {duration_str:>10}")

    print("="*120)
    print(f"\nTotal sessions: {len(sessions)}")
    print("\nUse 'python main.py info --session <session_id>' for detailed information")


def cmd_info(args):
    """
    Handle the 'info' command - shows detailed session information.

    Args:
        args: Parsed command-line arguments
    """
    session_id = args.session

    # Load session
    session_data, filepath = load_session(session_id)

    if not session_data:
        print(f"Error: Session '{session_id}' not found")
        print("\nUse 'python main.py list' to see all available sessions")
        sys.exit(1)

    metadata = session_data.get('metadata', {})
    laps = session_data.get('laps', [])

    # Display session metadata
    print("="*80)
    print("SESSION INFORMATION")
    print("="*80)
    print(f"Session ID:     {metadata.get('session_id', 'Unknown')}")
    print(f"Date:           {metadata.get('timestamp', 'Unknown')}")
    print(f"Track:          {metadata.get('track_name', 'Unknown')}")
    print(f"Configuration:  {metadata.get('track_config', '-')}")
    print(f"Car:            {metadata.get('car_name', 'Unknown')}")
    print(f"Driver:         {metadata.get('driver_name', 'Unknown')}")
    print(f"Session Type:   {metadata.get('session_type', 'Unknown')}")
    print(f"Total Laps:     {metadata.get('total_laps', 0)}")
    print(f"File:           {filepath}")
    print()

    # Display lap information
    if laps:
        print("="*80)
        print("LAP TIMES")
        print("="*80)
        print(f"{'Lap':>5} | {'Time':>10} | {'Telemetry Points':>17}")
        print("-"*80)

        best_lap = None
        best_time = float('inf')
        total_duration = 0

        for lap in laps:
            lap_num = lap.get('lap_number', 0)
            lap_time = lap.get('lap_time')
            telemetry_count = len(lap.get('telemetry', []))

            if lap_time is not None:
                time_str = f"{lap_time:.3f}s"
                total_duration += lap_time

                # Track best lap
                if lap_time > 0 and lap_time < best_time:
                    best_time = lap_time
                    best_lap = lap_num
            else:
                time_str = "Incomplete"

            print(f"{lap_num:>5} | {time_str:>10} | {telemetry_count:>17}")

        print("-"*80)

        if best_lap is not None:
            print(f"\nBest Lap:       Lap {best_lap} - {best_time:.3f}s")

        if total_duration > 0:
            minutes = int(total_duration // 60)
            seconds = total_duration % 60
            print(f"Total Duration: {minutes}m {seconds:.1f}s")

        print()
    else:
        print("No lap data available")

    print("="*80)


def _parse_lap_numbers(lap_arg):
    """
    Parse lap number argument(s) which can be single value, list, or range.

    Args:
        lap_arg (str or list): Lap number specification

    Returns:
        list: List of lap numbers

    Examples:
        "5" -> [5]
        ["2", "5", "7"] -> [2, 5, 7]
        "2-5" -> [2, 3, 4, 5]
    """
    if isinstance(lap_arg, list):
        lap_numbers = []
        for item in lap_arg:
            if '-' in str(item):
                # Handle range like "2-5"
                start, end = map(int, str(item).split('-'))
                lap_numbers.extend(range(start, end + 1))
            else:
                lap_numbers.append(int(item))
        return lap_numbers
    else:
        # Single value or range
        if '-' in str(lap_arg):
            start, end = map(int, str(lap_arg).split('-'))
            return list(range(start, end + 1))
        else:
            return [int(lap_arg)]


def cmd_export(args):
    """
    Handle the 'export' command - exports lap data to CSV.

    Args:
        args: Parsed command-line arguments
    """
    session_id = args.session
    lap_arg = args.lap

    # Parse lap numbers (can be single, multiple, or range)
    try:
        lap_numbers = _parse_lap_numbers(lap_arg)
    except ValueError as e:
        print(f"Error: Invalid lap specification '{lap_arg}'")
        print("Examples: --lap 5, --lap 2 5 7, --lap 2-5")
        sys.exit(1)

    # Load session
    session_data, filepath = load_session(session_id)

    if not session_data:
        print(f"Error: Session '{session_id}' not found")
        print("\nUse 'python main.py list' to see all available sessions")
        sys.exit(1)

    # Create exporter
    exporter = DataExporter()

    # Determine export type based on number of laps
    if len(lap_numbers) == 1:
        # Single lap export
        lap_number = lap_numbers[0]
        output_path = exporter.export_lap_to_csv(session_data, lap_number)
    else:
        # Multi-lap comparison export
        output_path = exporter.export_comparison_csv(session_data, lap_numbers)

    if output_path:
        print(f"✓ Exported to: {output_path}")
    else:
        sys.exit(1)


def main():
    """
    Main CLI entry point - parses arguments and dispatches to appropriate command.
    """
    # Create main parser
    parser = argparse.ArgumentParser(
        description='iRacing Telemetry Analysis Tool',
        epilog='For more information, see README.md'
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )

    # Add 'capture' command
    capture_parser = subparsers.add_parser(
        'capture',
        help='Start live telemetry capture from iRacing'
    )
    capture_parser.set_defaults(func=cmd_capture)

    # Add 'list' command
    list_parser = subparsers.add_parser(
        'list',
        help='List all captured sessions'
    )
    list_parser.set_defaults(func=cmd_list)

    # Add 'info' command
    info_parser = subparsers.add_parser(
        'info',
        help='Show detailed information about a session'
    )
    info_parser.add_argument(
        '--session',
        required=True,
        help='Session ID (full or first 8 characters)'
    )
    info_parser.set_defaults(func=cmd_info)

    # Add 'export' command
    export_parser = subparsers.add_parser(
        'export',
        help='Export lap telemetry to CSV'
    )
    export_parser.add_argument(
        '--session',
        required=True,
        help='Session ID (full or first 8 characters)'
    )
    export_parser.add_argument(
        '--lap',
        required=True,
        nargs='+',
        help='Lap number(s) to export. Examples: 5, or "2 5 7", or "2-5" for range'
    )
    export_parser.set_defaults(func=cmd_export)

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate command
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
