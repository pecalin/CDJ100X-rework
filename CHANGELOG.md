# Changelog

## v1.0.0 — Initial Release

Complete rework of the CDJ-100 mod, consolidating two previous projects
(CDJPlayer and XDJ100SX) into a unified platform.

### Platform Change

Migrated from **Windows 10 IoT (UWP)** to **Raspberry Pi OS (Linux) + Mixxx**.

| Aspect | Before (CDJPlayer) | After (CDJ100X) |
|--------|-------------------|-----------------|
| OS | Windows 10 IoT (deprecated) | Raspberry Pi OS Lite |
| Audio engine | Windows AudioGraph | Mixxx (professional DJ engine) |
| Hardware I/O | Direct GPIO (C#) | Python GPIO-to-MIDI bridge |
| UI | XAML + WaveSurfer.js | Mixxx skin (XML/QSS) |
| Networking | None | Pro DJ Link (full) |
| Hot cues | 3 | 8 |
| Pitch ranges | 3 (±10/16/100%) | 5 (±8/10/16/24/50%) |
| Pitch precision | ~10-bit (I2C ADC) | 14-bit (I2C ADC) |

### New Features

- **Pro DJ Link** — Full networking via RJ45: device discovery, BPM sync, beat phase, remote track loading, metadata sharing. Compatible with CDJ-2000, CDJ-3000, XDJ-1000, DJM-900NXS/NXS2.
- **Rekordbox USB** — Read Rekordbox-exported USB sticks (tracks, playlists, cue points, artwork, waveforms)
- **8 Hot Cues** (A-H) across 3 button modes
- **Loop Rolls** — 1/8, 1/4, 1/2 beat
- **Beat Jump** — 6 sizes (4, 8, 16, 32, 64, 128 beats)
- **Key Shift** — Up/down/reset
- **5" DSI Capacitive Touch Display** support
- **Auto-start** via systemd services
- **USB auto-mount** via udev rules

### GPIO Conflict Resolution

The original CDJPlayer `GPIO_PINS.cs` had several pin conflicts and issues
that are fixed in CDJ100X:

| GPIO | Problem | Fix |
|------|---------|-----|
| **24** | Double-assigned to Hold button AND PITCH1_PIN | Removed PITCH1_PIN — dead code, pitch reads via I2C (ADS1115) |
| **25** | Double-assigned to Jog encoder DT AND PITCH2_PIN | Removed PITCH2_PIN — dead code, pitch reads via I2C (ADS1115) |
| **8** | Assigned to PITCH3_PIN, which is also SPI CE0 | Removed PITCH3_PIN — dead code, pin freed |
| **7** | Browse encoder button on SPI CE1 | **Moved to GPIO 12** — SPI CE1 pulled LOW blocks Raspberry Pi boot |
| **14, 15** | Browse encoder CLK/DT on UART TX/RX | Install script disables serial console to free these pins |
| **9, 10, 11** | Zip/Jet/Wah buttons on SPI MISO/MOSI/SCLK | Install script disables SPI to free these pins |

**Background:** CDJPlayer's `GPIO_PINS.cs` defined `PITCH1_PIN` (GPIO 24),
`PITCH2_PIN` (GPIO 25), and `PITCH3_PIN` (GPIO 8), but these were never used
in any event handler. The pitch fader was always read via I2C using the ADS1115
ADC at address 0x48. These pin definitions were leftovers from an older design
that read the pitch fader through direct GPIO, before the I2C converter was added.

The browse encoder (CLK/DT/BTN on GPIO 15/14/7) was also commented out in
`GpioEvents.cs` and never activated in the CDJPlayer code, likely due to
conflicts with the UART serial console on GPIO 14/15.

### Wiring Change Required

If upgrading from CDJPlayer hardware:

**Browse encoder push button must be rewired from GPIO 7 to GPIO 12**
(physical pin 32 on the RPi header).

All other wiring remains the same as CDJPlayer's original instructions.

### Project Structure

```
CDJ100X-rework/
├── bridge/              # Python bridge (GPIO, Rekordbox, Pro DJ Link)
├── mixxx/controllers/   # Mixxx MIDI mapping
├── mixxx/skins/CDJ100X/ # Mixxx UI skin
├── system/              # systemd services, udev rules, install script
└── hardware/            # GPIO pinout documentation
```

### Credits

Built on:
- [CDJPlayer](https://github.com/Lukaszm328/CDJPlayer) — GPIO pinout and hardware mod instructions
- [XDJ100SX](https://github.com/Lukaszm328/XDJ100SX) — Mixxx skin, MIDI mapping, feature set
- [python-prodj-link](https://github.com/Lukaszm328/python-prodj-link) — Pro DJ Link protocol
- [Mixxx](https://mixxx.org) — Open-source DJ software
