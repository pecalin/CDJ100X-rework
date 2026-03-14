"""
CDJ100X Configuration — GPIO pins, MIDI mappings, and system settings.

GPIO pin assignments follow CDJPlayer's hardware mod wiring, with conflicts
resolved from the original GPIO_PINS.cs.

MIDI note/CC numbers match the XDJ100SX Mixxx controller mapping.

GPIO CONFLICT RESOLUTION (vs original CDJPlayer GPIO_PINS.cs):
  - PITCH1/2/3_PIN (24, 25, 8) REMOVED — obsolete, pitch uses I2C (ADS1115)
  - GPIO 24 was double-assigned (Hold button + PITCH1) — kept as Hold button
  - GPIO 25 was double-assigned (Jog DT + PITCH2) — kept as Jog encoder DT
  - GPIO 8 (PITCH3 / SPI CE0) — freed, no longer used
  - GPIO 7 (Browse BTN / SPI CE1) — moved to GPIO 12 to avoid SPI boot issue
  - GPIO 14/15 (Browse encoder / UART) — requires disabling serial console
  - GPIO 9/10/11 (Zip/Jet/Wah / SPI) — safe, SPI is disabled by default

IMPORTANT: Serial console must be disabled for browse encoder to work:
  sudo raspi-config → Interface Options → Serial Port → Login shell: No
  Or: remove 'console=serial0,115200' from /boot/cmdline.txt
"""

# --- GPIO Pin Assignments (BCM numbering) ---

BUTTONS = {
    "play_pause":   20,
    "cue":          21,
    "next_track":    4,
    "back":         17,
    "search_fwd":   27,
    "search_bwd":   22,
    "jet":          10,  # EFX button 1  (also SPI MOSI — SPI must be disabled)
    "zip":           9,  # EFX button 2  (also SPI MISO — SPI must be disabled)
    "wah":          11,  # EFX button 3  (also SPI SCLK — SPI must be disabled)
    "hold_mode":    24,  # Button mode switcher
    "auto_cue":      5,  # Shift modifier
    "remove_disc":   6,  # Eject
    "tempo":        13,  # Master tempo / tempo range
}

LEDS = {
    "play":  19,
    "cue":   26,
}

JOG_ENCODER = {
    "clk": 18,
    "dt":  25,
}

BROWSE_ENCODER = {
    "clk": 15,  # Also UART RX — serial console must be disabled
    "dt":  14,  # Also UART TX — serial console must be disabled
    "btn": 12,  # Moved from GPIO 7 (SPI CE1 — can block boot if pulled low)
}

# NOTE: GPIO 7 (original browse encoder button) is SPI CE1.
# If this pin is LOW during boot, the Pi may fail to start.
# Rewire the browse encoder button to GPIO 12 instead.
# GPIO 12 is a free general-purpose pin with no special boot function.

# --- I2C Pitch Fader (ADS1115 ADC) ---

I2C_BUS = 1
ADS1115_ADDR = 0x48
PITCH_POLL_HZ = 100         # How often to read the fader
PITCH_DEADBAND = 30          # Ignore changes smaller than this (out of 16383)

# ADS1115 config register bytes:
# - MUX: AIN0 vs GND (single-ended)
# - PGA: ±6.144V (matches CDJPlayer's 0xc0 config)
# - Mode: continuous conversion
# - Data rate: 860 SPS
ADS1115_CONFIG = bytes([0x01, 0xC0, 0xE0])
ADS1115_LO_THRESH = bytes([0x02, 0x00, 0x00])
ADS1115_HI_THRESH = bytes([0x03, 0xFF, 0xFF])

# Voltage calibration (from CDJPlayer's GpioEvents.cs)
PITCH_VOLTAGE_MAX = 5.00
PITCH_VOLTAGE_ZERO = 2.50
PITCH_VOLTAGE_MIN = 0.00

# --- MIDI Mapping (matches XDJ100SX.midi.xml) ---

# MIDI channel bytes
CH1_NOTE_ON  = 0x90   # Channel 1 Note On
CH1_NOTE_OFF = 0x80   # Channel 1 Note Off
CH3_NOTE_ON  = 0x92   # Channel 3 Note On (browse encoder)
CH1_CC       = 0xB0   # Channel 1 Control Change (pitch)
CH2_CC       = 0xB1   # Channel 2 Control Change (jog)

# Button → MIDI Note mapping
BUTTON_MIDI = {
    "play_pause":   0x3C,
    "cue":          0x3D,
    "tempo":        0x3E,  # Master tempo / tempo range
    "back":         0x3F,
    "search_bwd":   0x42,
    "search_fwd":   0x43,
    "jet":          0x44,  # Button 1
    "zip":          0x45,  # Button 2
    "wah":          0x46,  # Button 3
    "auto_cue":     0x47,  # Shift
    "hold_mode":    0x48,  # Button mode
    "next_track":   0x49,  # Load track
    "remove_disc":  0x4A,  # Eject (custom, not in original XDJ100SX)
}

# Browse encoder MIDI notes (on channel 3)
BROWSE_DOWN_NOTE = 0x46
BROWSE_UP_NOTE   = 0x47
BROWSE_BTN_NOTE  = 0x49  # Same as load track

# Jog wheel MIDI CC
JOG_CC = 0x14

# Pitch fader MIDI CC (14-bit: MSB + LSB)
PITCH_CC_MSB = 0x00
PITCH_CC_LSB = 0x20

# LED MIDI notes (received from Mixxx outputs)
LED_MIDI = {
    0x3D: "play",   # play_indicator
    0x3E: "cue",    # cue_indicator
}

# --- Encoder Settings ---

DEBOUNCE_MS = 10             # Button debounce time
JOG_SENSITIVITY = 1          # Jog wheel ticks per MIDI message

# --- Pro DJ Link Settings ---

PLAYER_NUMBER = 1            # 1-4, unique per unit
DEVICE_NAME = "CDJ-100X"     # Name shown on Pro DJ Link network

# --- System Paths ---

USB_MOUNT_BASE = "/media"
REKORDBOX_PDB_PATH = "PIONEER/rekordbox/export.pdb"
REKORDBOX_ANLZ_PATH = "PIONEER/USBANLZ"
