"""
GPIO-to-MIDI Bridge for CDJ-100X.

Reads buttons, rotary encoders, and I2C pitch fader from Raspberry Pi GPIO,
translates them into MIDI messages, and sends them to Mixxx via a virtual
MIDI port. Also receives MIDI from Mixxx to control LEDs.

Based on CDJPlayer's GpioEvents.cs pin assignments and XDJ100SX's MIDI mapping.
"""

import threading
import time
import logging

try:
    import RPi.GPIO as GPIO
    import smbus2
    HAS_HARDWARE = True
except (ImportError, RuntimeError):
    HAS_HARDWARE = False

import rtmidi

from bridge.config import (
    BUTTONS, LEDS, JOG_ENCODER, BROWSE_ENCODER,
    I2C_BUS, ADS1115_ADDR, ADS1115_CONFIG, ADS1115_LO_THRESH, ADS1115_HI_THRESH,
    PITCH_POLL_HZ, PITCH_DEADBAND,
    CH1_NOTE_ON, CH1_NOTE_OFF, CH3_NOTE_ON, CH1_CC, CH2_CC,
    BUTTON_MIDI, BROWSE_DOWN_NOTE, BROWSE_UP_NOTE, BROWSE_BTN_NOTE,
    JOG_CC, PITCH_CC_MSB, PITCH_CC_LSB,
    LED_MIDI, DEBOUNCE_MS,
)

logger = logging.getLogger(__name__)


class GpioMidiBridge:
    """Translates RPi GPIO events into MIDI messages for Mixxx."""

    def __init__(self):
        self._running = False
        self._midi_out = None
        self._midi_in = None
        self._i2c_bus = None
        self._pitch_thread = None

        # Encoder state tracking
        self._jog_last_clk = None
        self._browse_last_clk = None

        # Pitch fader state
        self._last_pitch_raw = -1

    def start(self):
        """Initialize GPIO, MIDI ports, and I2C, then start reading."""
        self._running = True

        # Set up virtual MIDI output port (sends to Mixxx)
        self._midi_out = rtmidi.MidiOut()
        self._midi_out.open_virtual_port("CDJ100X")
        logger.info("Opened virtual MIDI output port: CDJ100X")

        # Set up MIDI input port (receives LED feedback from Mixxx)
        self._midi_in = rtmidi.MidiIn()
        self._midi_in.open_virtual_port("CDJ100X")
        self._midi_in.set_callback(self._on_midi_in)
        logger.info("Opened virtual MIDI input port: CDJ100X")

        if not HAS_HARDWARE:
            logger.warning("RPi.GPIO not available — running in simulation mode")
            return

        self._setup_gpio()
        self._setup_i2c()

        # Start pitch fader polling thread
        self._pitch_thread = threading.Thread(target=self._pitch_poll_loop, daemon=True)
        self._pitch_thread.start()

    def stop(self):
        """Clean up GPIO and MIDI resources."""
        self._running = False
        if self._pitch_thread:
            self._pitch_thread.join(timeout=2)
        if HAS_HARDWARE:
            GPIO.cleanup()
        if self._midi_out:
            self._midi_out.close_port()
        if self._midi_in:
            self._midi_in.close_port()
        if self._i2c_bus:
            self._i2c_bus.close()
        logger.info("GPIO-MIDI bridge stopped")

    # --- GPIO Setup ---

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Buttons — input with pull-up, interrupt on both edges
        for name, pin in BUTTONS.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                pin, GPIO.BOTH,
                callback=self._make_button_callback(name),
                bouncetime=DEBOUNCE_MS,
            )
            logger.debug("Button '%s' on GPIO %d", name, pin)

        # LEDs — output, initially off (active low per CDJPlayer)
        for name, pin in LEDS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # HIGH = LED off (active low)
            logger.debug("LED '%s' on GPIO %d", name, pin)

        # Jog encoder — input with pull-up, interrupt on CLK
        GPIO.setup(JOG_ENCODER["clk"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(JOG_ENCODER["dt"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._jog_last_clk = GPIO.input(JOG_ENCODER["clk"])
        GPIO.add_event_detect(
            JOG_ENCODER["clk"], GPIO.BOTH,
            callback=self._on_jog_encoder,
            bouncetime=1,
        )

        # Browse encoder — input with pull-up, interrupt on CLK
        GPIO.setup(BROWSE_ENCODER["clk"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(BROWSE_ENCODER["dt"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(BROWSE_ENCODER["btn"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._browse_last_clk = GPIO.input(BROWSE_ENCODER["clk"])
        GPIO.add_event_detect(
            BROWSE_ENCODER["clk"], GPIO.BOTH,
            callback=self._on_browse_encoder,
            bouncetime=1,
        )
        GPIO.add_event_detect(
            BROWSE_ENCODER["btn"], GPIO.BOTH,
            callback=self._make_button_callback("browse_btn"),
            bouncetime=DEBOUNCE_MS,
        )

        logger.info("GPIO setup complete — %d buttons, %d LEDs, 2 encoders",
                     len(BUTTONS), len(LEDS))

    # --- I2C Pitch Fader Setup ---

    def _setup_i2c(self):
        try:
            self._i2c_bus = smbus2.SMBus(I2C_BUS)
            # Configure ADS1115 (same config as CDJPlayer's GpioEvents.cs)
            self._i2c_bus.write_i2c_block_data(ADS1115_ADDR, ADS1115_CONFIG[0],
                                                list(ADS1115_CONFIG[1:]))
            self._i2c_bus.write_i2c_block_data(ADS1115_ADDR, ADS1115_LO_THRESH[0],
                                                list(ADS1115_LO_THRESH[1:]))
            self._i2c_bus.write_i2c_block_data(ADS1115_ADDR, ADS1115_HI_THRESH[0],
                                                list(ADS1115_HI_THRESH[1:]))
            logger.info("ADS1115 I2C pitch fader initialized at 0x%02X", ADS1115_ADDR)
        except Exception:
            logger.exception("Failed to initialize I2C pitch fader")
            self._i2c_bus = None

    # --- Button Callbacks ---

    def _make_button_callback(self, button_name):
        """Create a GPIO callback for the given button."""
        def callback(channel):
            pressed = GPIO.input(channel) == GPIO.LOW  # Active low (pull-up)

            if button_name == "browse_btn":
                # Browse encoder button → load track
                if pressed:
                    self._send_note(CH1_NOTE_ON, BROWSE_BTN_NOTE, 127)
                else:
                    self._send_note(CH1_NOTE_OFF, BROWSE_BTN_NOTE, 0)
                return

            midi_note = BUTTON_MIDI.get(button_name)
            if midi_note is None:
                return

            # Buttons that need press+release (held state matters)
            needs_release = button_name in (
                "cue", "search_fwd", "search_bwd",
                "jet", "zip", "wah", "auto_cue",
            )

            if pressed:
                self._send_note(CH1_NOTE_ON, midi_note, 127)
            elif needs_release:
                self._send_note(CH1_NOTE_OFF, midi_note, 0)

        return callback

    # --- Encoder Callbacks ---

    def _on_jog_encoder(self, channel):
        """Handle jog wheel rotation using quadrature decoding.

        Replicates CDJPlayer's EncoderRotary_ValueChange logic:
        - Read DT pin when CLK transitions HIGH→LOW
        - DT LOW = clockwise, DT HIGH = counter-clockwise
        - Send relative MIDI CC (64 = center, >64 = CW, <64 = CCW)
        """
        clk = GPIO.input(JOG_ENCODER["clk"])

        if self._jog_last_clk == GPIO.HIGH and clk == GPIO.LOW:
            dt = GPIO.input(JOG_ENCODER["dt"])
            if dt == GPIO.LOW:
                # Clockwise
                self._send_cc(CH2_CC, JOG_CC, 65)
            else:
                # Counter-clockwise
                self._send_cc(CH2_CC, JOG_CC, 63)

        self._jog_last_clk = clk

    def _on_browse_encoder(self, channel):
        """Handle browse encoder rotation.

        Sends browse down/up as Note On on MIDI channel 3 (0x92),
        matching XDJ100SX's mapping.
        """
        clk = GPIO.input(BROWSE_ENCODER["clk"])

        if self._browse_last_clk == GPIO.HIGH and clk == GPIO.LOW:
            dt = GPIO.input(BROWSE_ENCODER["dt"])
            if dt == GPIO.LOW:
                # Clockwise → browse down
                self._send_note(CH3_NOTE_ON, BROWSE_DOWN_NOTE, 127)
            else:
                # Counter-clockwise → browse up
                self._send_note(CH3_NOTE_ON, BROWSE_UP_NOTE, 127)

        self._browse_last_clk = clk

    # --- Pitch Fader Polling ---

    def _pitch_poll_loop(self):
        """Poll ADS1115 for pitch fader position and send 14-bit MIDI CC."""
        interval = 1.0 / PITCH_POLL_HZ

        while self._running:
            if self._i2c_bus is None:
                time.sleep(1)
                continue

            try:
                # Read conversion register (big-endian 16-bit signed)
                data = self._i2c_bus.read_i2c_block_data(ADS1115_ADDR, 0x00, 2)
                raw_value = (data[0] << 8) | data[1]
                if raw_value > 32767:
                    raw_value -= 65536

                # Convert to 14-bit MIDI range (0-16383)
                # ADS1115 range: -32768 to +32767
                # Map to 0-16383 for MIDI 14-bit
                midi_14bit = int(((raw_value + 32768) / 65536) * 16383)
                midi_14bit = max(0, min(16383, midi_14bit))

                # Only send if changed beyond deadband
                if abs(midi_14bit - self._last_pitch_raw) > PITCH_DEADBAND:
                    self._last_pitch_raw = midi_14bit
                    msb = (midi_14bit >> 7) & 0x7F
                    lsb = midi_14bit & 0x7F
                    self._send_cc(CH1_CC, PITCH_CC_MSB, msb)
                    self._send_cc(CH1_CC, PITCH_CC_LSB, lsb)

            except Exception:
                logger.debug("I2C read error", exc_info=True)

            time.sleep(interval)

    # --- MIDI Input (LED feedback from Mixxx) ---

    def _on_midi_in(self, event, data=None):
        """Handle MIDI messages from Mixxx to control LEDs."""
        message, _ = event
        if len(message) < 3:
            return

        status, note, velocity = message[0], message[1], message[2]

        # Check if this is a Note On/Off for a mapped LED
        if status in (0x90, 0x80):
            led_name = LED_MIDI.get(note)
            if led_name and led_name in LEDS:
                pin = LEDS[led_name]
                if HAS_HARDWARE:
                    # XDJ100SX mapping uses inverted logic: on=0x00, off=0x7F
                    led_on = (velocity == 0x00) if status == 0x90 else False
                    GPIO.output(pin, GPIO.LOW if led_on else GPIO.HIGH)
                    logger.debug("LED %s: %s", led_name, "ON" if led_on else "OFF")

    # --- MIDI Output Helpers ---

    def _send_note(self, status, note, velocity):
        """Send a MIDI Note On/Off message."""
        if self._midi_out:
            self._midi_out.send_message([status, note, velocity])

    def _send_cc(self, status, cc, value):
        """Send a MIDI Control Change message."""
        if self._midi_out:
            self._midi_out.send_message([status, cc, value])
