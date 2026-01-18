# iRacing Telemetry Tool

Capture live telemetry from iRacing and export to CSV/JSON for AI-powered driving analysis.

## Features

- **Live capture** at 60Hz with real-time lap time display
- **Auto-export** when you stop capturing (Ctrl+C, exit iRacing, or session change)
- **14 telemetry channels**: throttle, brake, steering, speed, RPM, g-forces, and more
- **Lap comparison exports** for analyzing your driving with AI (Claude, ChatGPT)
- **GUI and CLI** interfaces - choose your preferred workflow
- Works with any car/track combination

## Quick Start

### Option 1: Download & Run (Recommended)

1. Download the [latest release](https://github.com/ethansheffield/iracing-telemetry-tool/releases)
2. Extract the zip file
3. Double-click `setup.bat` and wait for installation to complete
4. Double-click `Start Telemetry.bat` to launch the GUI

### Option 2: Git Clone

```bash
git clone https://github.com/ethansheffield/iracing-telemetry-tool.git
cd iracing-telemetry-tool
pip install -r requirements.txt

# Launch GUI
python gui.py

# Or use command line
python main.py capture
```

## Requirements

- Windows 10/11
- Python 3.10 or higher ([Download](https://www.python.org/downloads/))
  - **Important**: Check "Add Python to PATH" during installation
- iRacing (must be running for capture)

## Usage

### GUI Mode

Launch `Start Telemetry.bat` or run `python gui.py`

**Capturing Telemetry:**
1. **Start iRacing** and load into a session (Practice, Qualify, or Race)
2. **Click "Start Capture"** in the telemetry tool
3. **Drive your laps** - you'll see live updates
4. **Click "Stop Capture"** when done, or just close iRacing
   - Data exports automatically to `data/exports/`

**Viewing Past Sessions:**
1. Click on a session in the left sidebar
2. View lap times with deltas to your best lap
3. Click "Export" on specific laps for detailed analysis
4. Click "Export All" to export the complete session

### Command Line

| Command | Description |
|---------|-------------|
| `python main.py capture` | Start live capture |
| `python main.py list` | View all sessions |
| `python main.py info --session <id>` | Session details and lap times |
| `python main.py export --session <id> --lap 2` | Export single lap |
| `python main.py export --session <id> --lap 1 2 3` | Export specific laps |
| `python main.py export --session <id> --lap 2-5` | Export lap range |

**Session ID:** Use the full ID or just the first 8 characters shown in `list` output.

## Data Channels

The tool captures 14 telemetry channels at 60Hz (every ~16ms):

| Category | Channels |
|----------|----------|
| Position | `lap`, `time`, `distance`, `distance_pct` |
| Inputs | `throttle`, `brake`, `steering`, `gear` |
| Engine | `rpm` |
| Dynamics | `speed`, `lat_accel`, `long_accel`, `yaw_rate`, `steering_wheel_angle` |

**Units:**
- Speed: m/s (multiply by 2.237 for mph)
- Accelerations: G-forces
- Steering: radians
- Throttle/Brake: 0.0 to 1.0 (0% to 100%)

## Using with AI

Export your lap data, then upload to Claude or ChatGPT with a prompt like:

> "Here's my telemetry from Laguna Seca in a GT3 car. My best lap was 1:23.4.
> Analyze my braking points and throttle application, especially through the Corkscrew.
> Where am I leaving time on the table?"

**What the AI can identify:**
- Late/early braking points relative to optimal
- Throttle application issues (too early, not smooth enough)
- Steering corrections indicating oversteer/understeer
- Speed differentials through corner sections
- Comparing fast vs slow laps to find where you gained/lost time

**Example AI Insights:**
- "You're braking 20m later into Turn 1 on your slow laps"
- "Your throttle application is smoother on Lap 4 (best lap) - gradual from 0% to 100% over 1.2s vs abrupt 0.4s on Lap 7"
- "Lateral G-force shows understeer mid-corner on Lap 3 - you're fighting the wheel (yaw rate oscillating)"

## Export Formats

### Single Lap Export
All telemetry samples for one lap, row-by-row at 60Hz.

**Filename:** `{Track}_{SessionType}_lap{N}_{timestamp}.csv`

**Use for:** Detailed analysis of one specific lap.

### Multi-Lap Export (Concatenated)
Multiple laps appended sequentially in one file.

**Filename:** `{Track}_{SessionType}_laps{N-M}_{timestamp}.csv`

**Use for:** Viewing progression over multiple laps.

### Multi-Lap Comparison Export
Distance-aligned data for comparing laps side-by-side.

**Columns:** `distance_pct`, `distance`, `lap1_speed`, `lap1_throttle`, ..., `lap2_speed`, `lap2_throttle`, ...

**Filename:** `{Track}_{SessionType}_comparison_laps{N-M}_{timestamp}.csv`

**Use for:** Direct comparison of driving inputs at the same track positions.

### Complete Session Export
All laps from a session (auto-generated when you stop capturing).

**Filename:** `{Track}_{SessionType}_{timestamp}_complete.csv`

**Use for:** Full session overview and AI analysis.

## File Locations

- **Captured Sessions:** `./data/sessions/{track}/{session_type}/`
  - Raw JSON with all telemetry samples
  - Organized by track and session type
- **Exports:** `./data/exports/`
  - CSV files ready for analysis
  - Session JSON copies for reference

## Troubleshooting

### "Python is not installed"
Download Python from [python.org](https://www.python.org/downloads/). During installation, **check "Add Python to PATH"**.

### "iRacing not detected"
- Make sure iRacing is running and you're **in a session** (not main menu)
- Try test drive or practice session
- Restart the telemetry tool after iRacing is fully loaded

### "No data captured" / Empty files
- Check that you're actually driving (not paused, not in pits with engine off)
- Some sessions like replays may not broadcast telemetry
- Make sure iRacing SDK is enabled (it's on by default)

### GUI won't launch
Run from command line to see error messages:
```bash
cd iracing-telemetry-tool
venv\Scripts\activate
python gui.py
```

Check that all dependencies installed:
```bash
pip install -r requirements.txt
```

### setup.bat fails
- Verify Python is installed and in PATH: `python --version`
- Run Command Prompt as Administrator
- Manually create venv: `python -m venv venv`
- Manually install deps: `venv\Scripts\activate` then `pip install -r requirements.txt`

### Capture stops immediately
- This is normal if iRacing is not in a session
- Load into a track (Test Drive, Practice, etc.) before starting capture

## Technical Details

**How it works:**
1. Connects to iRacing's shared memory interface via pyirsdk
2. Polls telemetry at 60Hz (adjustable)
3. Buffers data in memory organized by lap
4. Writes to JSON when lap completes or session ends
5. Auto-exports to CSV for easy analysis

**Session Detection:**
- New session starts when you load into a track
- Sessions are tracked by iRacing's internal SessionNum
- Session auto-saves when you:
  - Press Ctrl+C in capture mode
  - Exit iRacing
  - Change session type (Practice → Qualify → Race)

**Lap Detection:**
- Laps increment when you cross start/finish line
- First lap is always Lap 1 (not 0)
- Incomplete laps are saved if you stop mid-lap

## Development

**Project structure:**
```
iracing-telemetry-tool/
├── main.py                 # CLI entry point
├── gui.py                  # Tkinter GUI
├── setup.bat               # Windows installer
├── src/
│   ├── capture.py         # Telemetry capture (60Hz)
│   ├── storage.py         # Session JSON storage
│   └── exporter.py        # CSV export logic
├── data/
│   ├── sessions/          # Captured sessions (JSON)
│   └── exports/           # Exported data (CSV/JSON)
└── requirements.txt       # Python dependencies
```

**Running from source:**
```bash
# Clone repo
git clone https://github.com/ethansheffield/iracing-telemetry-tool.git
cd iracing-telemetry-tool

# Create venv (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run GUI
python gui.py

# Run CLI
python main.py capture
python main.py list
python main.py export --session abc123 --lap 2
```

## License

MIT License - use freely, attribution appreciated.

## Contributing

Issues and pull requests welcome! Please test with multiple cars/tracks before submitting.

**Testing checklist:**
- [ ] Capture works in Practice, Qualify, and Race sessions
- [ ] Multiple laps captured correctly
- [ ] Session changes handled (Practice → Qualify)
- [ ] Disconnection/reconnection handled gracefully
- [ ] Exports work for single lap, multi-lap, and comparison formats
- [ ] GUI displays session list correctly
- [ ] GUI start/stop capture works

## Credits

Built with [pyirsdk](https://github.com/kutu/pyirsdk) for iRacing SDK integration.
