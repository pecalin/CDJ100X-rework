# CDJ-100X Rework

A complete rework of the Pioneer CDJ-100 player, turning it into a modern standalone digital DJ player using a Raspberry Pi 3B+, Mixxx DJ software, and Pro DJ Link networking.

Two modded CDJ-100 units can be linked via RJ45 Ethernet cable — and they'll also work alongside real Pioneer CDJs (CDJ-2000, XDJ-1000, etc.) and DJM mixers on the same Pro DJ Link network.

## Features

- **Mixxx DJ Engine** — Professional-grade audio playback, beat detection, time-stretching, effects, and library management
- **8 Hot Cues** — Spread across 3 button modes (A-H)
- **Loop Rolls** — 1/8, 1/4, 1/2 beat rolls
- **Beat Jump** — 6 configurable jump sizes (4, 8, 16, 32, 64, 128 beats)
- **Key Shift** — Pitch up/down and reset
- **5 Tempo Ranges** — ±8%, ±10%, ±16%, ±24%, ±50%
- **14-bit Pitch Fader** — High-precision tempo control via I2C ADC
- **Master Tempo** — Key lock toggle
- **Rekordbox USB** — Read Rekordbox-exported USB sticks (tracks, playlists, cue points, artwork)
- **Pro DJ Link** — Full networking: device discovery, BPM sync, beat phase, remote track loading, metadata sharing
- **5" DSI Capacitive Touch Display** — Spectrum waveforms, library browsing, hot cue display

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Raspberry Pi 3B+ (Raspberry Pi OS Lite)                 │
│                                                          │
│  ┌──────────┐  virtual   ┌─────────────────────────────┐ │
│  │  Mixxx   │◄──MIDI───►│  cdj-bridge (Python)         │ │
│  │ (DJ      │            │                              │ │
│  │  engine  │            │  ├─ GPIO-to-MIDI module      │ │
│  │  + skin) │            │  │  (buttons, encoders,      │ │
│  │          │            │  │   LEDs, I2C pitch fader)  │ │
│  └──────────┘            │  │                           │ │
│       │                  │  ├─ Rekordbox PDB reader     │ │
│   5" DSI                 │  │  (USB library browsing)   │ │
│   capacitive             │  │                           │ │
│   touch                  │  ├─ Pro DJ Link module       │ │
│                          │  │  (Vcdj, beat sync,        │ │
│                          │  │   metadata, track load)   │ │
│                          │  └───────┬───────────────────┘ │
│                          │     UDP 50000/50001/50002      │
│                          └──────────┬────────────────────┘ │
│                                ┌────┴────┐                │
│                                │  RJ45   │                │
│                                │Ethernet │                │
│                                └─────────┘                │
└──────────────────────────────────────────────────────────┘
                                     │
                                To other CDJ
```

The **cdj-bridge** is a single Python process that handles three jobs:
1. **GPIO-to-MIDI** — Reads hardware buttons, rotary encoders, and I2C pitch fader from RPi GPIO pins, translates them into virtual MIDI messages for Mixxx
2. **Rekordbox USB** — Detects Rekordbox-exported USB sticks, parses the PDB database, and generates M3U playlists for Mixxx
3. **Pro DJ Link** — Announces the unit as a Virtual CDJ on the network, broadcasts BPM/beat/status, receives linked player state

## Hardware

### Bill of Materials

| Component | Description |
|-----------|-------------|
| Pioneer CDJ-100 | Donor unit (shell, buttons, jog wheel, pitch fader) |
| Raspberry Pi 3B+ | Main computer |
| 5" DSI Capacitive Touch Display | 800x480 resolution |
| ADS1115 ADC Module | I2C analog-to-digital converter for pitch fader |
| Wires, connectors | For button/LED/encoder connections |

### GPIO Pinout

All connections use **BCM pin numbering**. Buttons use internal pull-up resistors (active LOW).
See [CHANGELOG.md](CHANGELOG.md) for GPIO changes from the original CDJPlayer project.

#### Buttons

| Function | GPIO | MIDI Note | Description |
|----------|------|-----------|-------------|
| Play/Pause | 20 | 0x3C | Toggle play/pause |
| Cue | 21 | 0x3D | CDJ-style cue (press & hold) |
| Next Track | 4 | 0x49 | Load selected track |
| Back | 17 | 0x3F | Navigate back in library |
| Search Forward | 27 | 0x43 | Seek forward (hold) |
| Search Backward | 22 | 0x42 | Seek backward (hold) |
| Jet (EFX 1) | 10 | 0x44 | Multi-function button 1 |
| Zip (EFX 2) | 9 | 0x45 | Multi-function button 2 |
| Wah (EFX 3) | 11 | 0x46 | Multi-function button 3 |
| Hold/Mode | 24 | 0x48 | Cycle button modes |
| Auto Cue (Shift) | 5 | 0x47 | Shift modifier |
| Remove Disc | 6 | 0x4A | Eject |
| Tempo Master | 13 | 0x3E | Key lock / tempo range (with shift) |

#### LEDs

| Function | GPIO | Description |
|----------|------|-------------|
| Play LED | 19 | Active LOW — lights when playing |
| Cue LED | 26 | Active LOW — lights when cue is set |

#### Encoders

| Encoder | CLK | DT | Button | Description |
|---------|-----|-----|--------|-------------|
| Jog Wheel | 18 | 25 | — | Pitch bend (playing) / scratch (paused) |
| Browse | 15 | 14 | 12 | Scroll library / push to load |

#### Pitch Fader (I2C)

| Connection | Pin | Description |
|------------|-----|-------------|
| I2C SDA | GPIO 2 | Data line |
| I2C SCL | GPIO 3 | Clock line |
| ADS1115 Address | 0x48 | ADDR pin to GND |
| Analog Input | A0 | Pitch fader wiper |

### Raspberry Pi GPIO Header

```
                3V3  (1)  (2)  5V
    [I2C SDA]   GP2  (3)  (4)  5V
    [I2C SCL]   GP3  (5)  (6)  GND
   Next Track   GP4  (7)  (8)  GP14  Browse DT
                GND  (9)  (10) GP15  Browse CLK
    Auto Cue    GP17 (11) (12) GP18  Jog CLK
  Remove Disc   GP27 (13) (14) GND
    Search -    GP22 (15) (16) GP23  (free)
                3V3  (17) (18) GP24  Hold/Mode
        Zip     GP10 (19) (20) GND
        Jet     GP9  (21) (22) GP25  Jog DT
        Wah     GP11 (23) (24) GP8   (free)
                GND  (25) (26) GP7   (free)
                GP0  (27) (28) GP1
       Back     GP5  (29) (30) GND
  Browse BTN    GP12 (31) (32) GP6   Search +
  Tempo Master  GP13 (33) (34) GND
    Play LED    GP19 (35) (36) GP16  (free)
     Cue LED    GP26 (37) (38) GP20  Play/Pause
                GND  (39) (40) GP21  Cue
```

## Button Modes

The three EFX buttons (Jet, Zip, Wah) change function depending on the current mode. Press **Hold/Mode** to cycle through modes:

| Mode | Button 1 (Jet) | Button 2 (Zip) | Button 3 (Wah) |
|------|---------------|----------------|-----------------|
| 0 | Hot Cue A | Hot Cue B | Hot Cue C |
| 1 | Hot Cue D | Hot Cue E | Hot Cue F |
| 2 | Hot Cue G | Hot Cue H | — |
| 3 | Loop Roll 1/8 | Loop Roll 1/4 | Loop Roll 1/2 |
| 4 | Beat Jump Back | Beat Jump Fwd | Change Jump Size |
| 5 | Key Shift - | Key Shift + | Key Reset |

Hold **Shift** (Auto Cue) + Hot Cue button to **clear** a hot cue.
Hold **Shift** + **Tempo Master** to **change tempo range**.

## Pro DJ Link

### How It Works

Pro DJ Link is Pioneer's networking protocol that lets DJ equipment communicate over Ethernet. Each modded CDJ-100X appears as a real CDJ on the network.

**What gets shared between linked players:**
- BPM and beat position (for visual beat sync)
- Play/pause state
- Track metadata (artist, title)
- Tempo/pitch fader position

**Advanced features:**
- Remote track loading (tell another player to load a track)
- Master tempo sync negotiation
- On-air status from DJM mixer

### Network Setup

**Two CDJ-100X units (direct cable):**
```
CDJ-100X (Player 1) ──── RJ45 ──── CDJ-100X (Player 2)
```

**Mixed setup with real Pioneer gear:**
```
Ethernet Switch
├── CDJ-100X (Player 1) ── DJM Ch1
├── CDJ-100X (Player 2) ── DJM Ch2
├── CDJ-2000 (Player 3)  ── DJM Ch3
└── DJM-900NXS2 (Mixer)
```

Each unit needs a unique player number (1-4). Set it in `/etc/cdj-link.conf`:
```ini
[player]
number = 1
name = CDJ-100X
```

### Compatibility

The Pro DJ Link bridge uses [python-prodj-link](https://github.com/Lukaszm328/python-prodj-link), tested with:
- CDJ-2000 / CDJ-2000NXS / CDJ-2000NXS2
- CDJ-3000
- XDJ-1000 / XDJ-1000MK2
- DJM-900NXS / DJM-900NXS2

## Rekordbox USB Support

Insert a Rekordbox-exported USB stick and the bridge will automatically:
1. Detect the `PIONEER/rekordbox/export.pdb` database
2. Parse tracks, playlists, artists, albums, cue points
3. Generate M3U playlists for Mixxx to import
4. Make all tracks available for browsing and loading

## Project Structure

```
CDJ100X-rework/
├── bridge/                      # Python bridge process
│   ├── main.py                  # Entry point
│   ├── config.py                # GPIO pins, MIDI mapping, settings
│   ├── gpio_midi.py             # GPIO → virtual MIDI → Mixxx
│   ├── rekordbox_usb.py         # Rekordbox USB library reader
│   └── prodj_bridge.py          # Pro DJ Link network bridge
│
├── mixxx/                       # Mixxx configuration
│   ├── controllers/
│   │   ├── CDJ100X.midi.xml     # MIDI control mapping
│   │   └── CDJ100X.js           # Controller script
│   └── skins/
│       └── CDJ100X/             # UI skin (based on XDJ100SX)
│
├── system/                      # System integration
│   ├── cdj-bridge.service       # systemd service (bridge)
│   ├── mixxx.service            # systemd service (Mixxx)
│   ├── 99-usb-mount.rules       # USB auto-mount udev rules
│   ├── cdj-link.conf            # Per-unit config
│   └── install.sh               # Installation script
│
├── hardware/                    # Hardware documentation
│   └── pinout.md                # GPIO pin reference
│
└── requirements.txt             # Python dependencies
```

## Installation

### Prerequisites

- Raspberry Pi 3B+ with Raspberry Pi OS Lite installed
- 5" DSI capacitive touch display connected
- All buttons, encoders, LEDs, and pitch fader wired to GPIO (see pinout above)
- ADS1115 ADC connected via I2C for pitch fader

### Quick Install

```bash
git clone https://github.com/Lukaszm328/CDJ100X-rework.git
cd CDJ100X-rework
sudo bash system/install.sh
```

The install script will:
1. Install Mixxx, Python dependencies, and I2C tools
2. Enable I2C in boot config
3. Set up Python virtual environment with all dependencies
4. Clone python-prodj-link
5. Install Mixxx skin and controller mapping
6. Enable systemd services for auto-start
7. Configure display for 800x480

### Post-Install

1. Edit `/etc/cdj-link.conf` to set unique player number (1 or 2)
2. Reboot: `sudo reboot`
3. Mixxx will auto-start in fullscreen
4. Open Mixxx preferences → Controllers → select **CDJ100X**
5. Open Mixxx preferences → Interface → select **CDJ100X** skin

### Manual Start (for testing)

```bash
# Start the bridge without hardware (simulation mode)
python3 -m bridge.main --no-gpio --log-level DEBUG

# Start with GPIO but no Pro DJ Link
python3 -m bridge.main --no-prodj

# Start everything
python3 -m bridge.main
```

## Dependencies

### Python

| Package | Version | Purpose |
|---------|---------|---------|
| gpiozero | >=2.0 | GPIO abstraction (fallback) |
| RPi.GPIO | >=0.7.1 | Direct GPIO access |
| smbus2 | >=0.4.3 | I2C communication (ADS1115) |
| python-rtmidi | >=1.5.8 | Virtual MIDI ports |
| construct | >=2.10.70 | Binary protocol parsing (Pro DJ Link) |
| netifaces | >=0.11.0 | Network interface detection |
| pyudev | >=0.24.1 | USB hotplug monitoring |

### System

| Package | Purpose |
|---------|---------|
| Mixxx | DJ software |
| i2c-tools | I2C diagnostics |
| libasound2-dev | ALSA audio (MIDI) |

## Development

### Testing Without Hardware

The bridge runs in simulation mode when RPi.GPIO is not available (e.g., on a desktop PC). Virtual MIDI ports are still created, so you can test the Mixxx integration:

```bash
python3 -m bridge.main --no-gpio --no-prodj --log-level DEBUG
```

### Testing I2C Pitch Fader

```bash
# Check if ADS1115 is detected
i2cdetect -y 1
# Should show 0x48

# Read raw value
i2cget -y 1 0x48 0x00 w
```

### Testing GPIO

```bash
# Monitor button presses
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_UP)
while True:
    if GPIO.input(20) == GPIO.LOW:
        print('Play pressed')
"
```

## Credits

- **CDJPlayer** — Original UWP mod by [Lukaszm328](https://github.com/Lukaszm328/CDJPlayer) (GPIO pinout and hardware mod instructions)
- **XDJ100SX** — Mixxx-based mod by [Lukaszm328](https://github.com/Lukaszm328/XDJ100SX) (skin, MIDI mapping, feature set)
- **python-prodj-link** — Pro DJ Link protocol implementation (device discovery, beat sync, metadata)
- **Mixxx** — Open-source DJ software ([mixxx.org](https://mixxx.org))

## License

This project builds on open-source components. See individual component licenses:
- Mixxx: GPL v2
- python-prodj-link: See repository license
- XDJ100SX skin: See LICENSE file in skin folder
