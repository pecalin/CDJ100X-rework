# CDJ-100X GPIO Pinout

All connections use BCM pin numbering on Raspberry Pi 3B+.
Buttons use internal pull-up resistors (active LOW).
LEDs are active LOW (GPIO LOW = LED ON).

## Conflict Resolution

The original CDJPlayer `GPIO_PINS.cs` had several pin conflicts that are
resolved in this project:

| Issue | Original | Resolution |
|-------|----------|------------|
| GPIO 24 double-assigned | Hold button + PITCH1_PIN | PITCH1 removed (pitch uses I2C now) |
| GPIO 25 double-assigned | Jog encoder DT + PITCH2_PIN | PITCH2 removed (pitch uses I2C now) |
| GPIO 8 (SPI CE0) | PITCH3_PIN | PITCH3 removed (pitch uses I2C now) |
| GPIO 7 (SPI CE1) | Browse encoder button | **Moved to GPIO 12** (SPI CE1 can block boot) |
| GPIO 14/15 (UART) | Browse encoder | Serial console must be disabled |
| GPIO 9/10/11 (SPI) | Zip/Jet/Wah buttons | SPI must be disabled |

**PITCH1/2/3_PIN were dead code** — CDJPlayer reads pitch via I2C (ADS1115),
not through direct GPIO pins. Those pin definitions were left over from an
older design and are completely removed in CDJ100X.

## Required System Configuration

The install script handles this automatically, but for reference:

```bash
# Disable serial console (frees GPIO 14/15 for browse encoder)
sudo raspi-config → Interface Options → Serial Port → Login shell: No

# Disable SPI (frees GPIO 7/8/9/10/11 for buttons)
# Add to /boot/config.txt:
dtparam=spi=off
```

## Buttons (Input, Pull-Up)

| Function | GPIO | CDJ-100 Wire | MIDI Note | Notes |
|----------|------|--------------|-----------|-------|
| Play/Pause | 20 | Play button | 0x3C | |
| Cue | 21 | Cue button | 0x3D | |
| Next Track | 4 | Track >> button | 0x49 | |
| Back/Prev | 17 | Track << button | 0x3F | |
| Search Forward | 27 | Search >> button | 0x43 | |
| Search Backward | 22 | Search << button | 0x42 | |
| Jet (EFX 1) | 10 | Jet button | 0x44 | SPI MOSI — disable SPI |
| Zip (EFX 2) | 9 | Zip button | 0x45 | SPI MISO — disable SPI |
| Wah (EFX 3) | 11 | Wah button | 0x46 | SPI SCLK — disable SPI |
| Hold/Mode | 24 | Hold button | 0x48 | |
| Auto Cue (Shift) | 5 | Time/Auto Cue | 0x47 | |
| Remove Disc | 6 | Eject button | 0x4A | |
| Tempo Master | 13 | Master Tempo | 0x3E | |

## LEDs (Output, Active Low)

| Function | GPIO | CDJ-100 Wire |
|----------|------|--------------|
| Play LED | 19 | Play LED |
| Cue LED | 26 | Cue LED |

## Jog Wheel Encoder

| Signal | GPIO | Notes |
|--------|------|-------|
| CLK | 18 | |
| DT | 25 | Was also PITCH2_PIN — conflict resolved |

## Browse Encoder

| Signal | GPIO | Notes |
|--------|------|-------|
| CLK | 15 | UART RX — serial console must be disabled |
| DT | 14 | UART TX — serial console must be disabled |
| Button | **12** | **CHANGED from GPIO 7** (SPI CE1 boot issue) |

## Pitch Fader (I2C via ADS1115)

| Signal | Connection | Description |
|--------|------------|-------------|
| I2C SDA | GPIO 2 (I2C1 SDA) | I2C data line |
| I2C SCL | GPIO 3 (I2C1 SCL) | I2C clock line |
| ADS1115 A0 | Pitch fader wiper | Analog input |
| ADS1115 VDD | 3.3V or 5V | Power supply |
| ADS1115 GND | Ground | Ground |
| ADS Address | 0x48 | I2C address (ADDR pin to GND) |

## Reserved / Unavailable GPIO

| GPIO | Function | Status |
|------|----------|--------|
| 0 | I2C0 SDA (EEPROM) | Do not use |
| 1 | I2C0 SCL (EEPROM) | Do not use |
| 2 | I2C1 SDA | Reserved for ADS1115 |
| 3 | I2C1 SCL | Reserved for ADS1115 |
| 7 | SPI CE1 | **FREE** (was browse BTN, moved to 12) |
| 8 | SPI CE0 | **FREE** (was PITCH3, removed) |
| 16 | — | **FREE** |
| 23 | ADS Alert | Optional (not used in current code) |

## Complete GPIO Map

| GPIO | Assignment | Direction | Pin Group |
|------|-----------|-----------|-----------|
| 2 | I2C SDA | Bidirectional | I2C (ADS1115) |
| 3 | I2C SCL | Output | I2C (ADS1115) |
| 4 | Next Track button | Input | Button |
| 5 | Auto Cue / Shift button | Input | Button |
| 6 | Remove Disc button | Input | Button |
| 7 | — | FREE | — |
| 8 | — | FREE | — |
| 9 | Zip button | Input | Button (disable SPI) |
| 10 | Jet button | Input | Button (disable SPI) |
| 11 | Wah button | Input | Button (disable SPI) |
| 12 | Browse encoder button | Input | Browse encoder |
| 13 | Tempo Master button | Input | Button |
| 14 | Browse encoder DT | Input | Browse encoder (disable serial) |
| 15 | Browse encoder CLK | Input | Browse encoder (disable serial) |
| 16 | — | FREE | — |
| 17 | Back button | Input | Button |
| 18 | Jog encoder CLK | Input | Jog encoder |
| 19 | Play LED | Output | LED |
| 20 | Play/Pause button | Input | Button |
| 21 | Cue button | Input | Button |
| 22 | Search Backward button | Input | Button |
| 23 | — | FREE (ADS Alert optional) | — |
| 24 | Hold/Mode button | Input | Button |
| 25 | Jog encoder DT | Input | Jog encoder |
| 26 | Cue LED | Output | LED |
| 27 | Search Forward button | Input | Button |

Total: 13 buttons + 2 encoders (5 pins) + 2 LEDs + I2C (2 pins) = 22 GPIO used, 4 free

## Raspberry Pi 3B+ GPIO Header

```
                3V3  (1)  (2)  5V
    [I2C SDA]   GP2  (3)  (4)  5V
    [I2C SCL]   GP3  (5)  (6)  GND
   Next Track   GP4  (7)  (8)  GP14  Browse DT [UART TX]
                GND  (9)  (10) GP15  Browse CLK [UART RX]
    Auto Cue    GP17 (11) (12) GP18  Jog CLK
  Remove Disc   GP27 (13) (14) GND
    Search -    GP22 (15) (16) GP23  (free / ADS Alert)
                3V3  (17) (18) GP24  Hold/Mode
    Zip [SPI]   GP10 (19) (20) GND
    Jet [SPI]   GP9  (21) (22) GP25  Jog DT
    Wah [SPI]   GP11 (23) (24) GP8   (free)
                GND  (25) (26) GP7   (free)
                GP0  (27) (28) GP1
       Back     GP5  (29) (30) GND
  Browse BTN*   GP12 (31) (32) GP6   Search +
  Tempo Mstr    GP13 (33) (34) GND
    Play LED    GP19 (35) (36) GP16  (free)
     Cue LED    GP26 (37) (38) GP20  Play/Pause
                GND  (39) (40) GP21  Cue
```

\* Browse encoder button moved from GPIO 7 to GPIO 12 to avoid SPI CE1 boot conflict.

Note: Physical pin numbers in parentheses. BCM GPIO numbers shown as GPxx.
[SPI] = requires SPI disabled. [UART] = requires serial console disabled.
