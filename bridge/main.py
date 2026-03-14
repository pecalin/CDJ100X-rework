#!/usr/bin/env python3
"""
CDJ-100X Bridge — Main entry point.

Orchestrates three modules:
  1. GPIO-to-MIDI bridge (hardware ↔ Mixxx)
  2. Rekordbox USB library reader
  3. Pro DJ Link network bridge

All run as threads within a single process, started as a systemd service
before Mixxx launches.
"""

import argparse
import logging
import signal
import sys
import time

from bridge.gpio_midi import GpioMidiBridge
from bridge.rekordbox_usb import RekordboxUSB
from bridge.prodj_bridge import ProDjBridge
from bridge.config import PLAYER_NUMBER

logger = logging.getLogger("cdj100x")


class CDJ100XBridge:
    """Main orchestrator for all bridge components."""

    def __init__(self, enable_gpio=True, enable_rekordbox=True, enable_prodj=True):
        self._running = False
        self._gpio = GpioMidiBridge() if enable_gpio else None
        self._rekordbox = RekordboxUSB() if enable_rekordbox else None
        self._prodj = ProDjBridge() if enable_prodj else None

    def start(self):
        """Start all bridge components."""
        self._running = True
        logger.info("CDJ-100X Bridge starting (Player %d)", PLAYER_NUMBER)

        if self._gpio:
            self._gpio.start()
            logger.info("GPIO-MIDI bridge: started")

        if self._rekordbox:
            self._rekordbox.set_library_loaded_callback(self._on_library_loaded)
            self._rekordbox.start()
            logger.info("Rekordbox USB monitor: started")

        if self._prodj:
            self._prodj.set_player_update_callback(self._on_linked_player_update)
            self._prodj.start()
            logger.info("Pro DJ Link bridge: started")

        logger.info("CDJ-100X Bridge running")

    def stop(self):
        """Stop all bridge components."""
        logger.info("CDJ-100X Bridge shutting down...")
        self._running = False

        if self._prodj:
            self._prodj.stop()
        if self._rekordbox:
            self._rekordbox.stop()
        if self._gpio:
            self._gpio.stop()

        logger.info("CDJ-100X Bridge stopped")

    def run_forever(self):
        """Block until interrupted."""
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    # --- Internal Callbacks ---

    def _on_library_loaded(self, tracks, playlists):
        """Called when a Rekordbox USB is detected and parsed."""
        logger.info("Rekordbox library loaded: %d tracks, %d playlists",
                     len(tracks), len(playlists))

        # Generate M3U playlists for Mixxx to import
        if playlists and self._rekordbox:
            try:
                m3u_dir = "/tmp/cdj100x-playlists"
                generated = self._rekordbox.generate_m3u_playlists(m3u_dir)
                logger.info("Generated %d M3U playlists in %s", len(generated), m3u_dir)
            except Exception:
                logger.exception("Failed to generate M3U playlists")

    def _on_linked_player_update(self, player_number, player_info):
        """Called when a linked player's state changes on the Pro DJ Link network."""
        logger.debug("Player %d update: BPM=%.1f playing=%s",
                     player_number,
                     player_info.get("bpm", 0),
                     player_info.get("is_playing", False))


def main():
    parser = argparse.ArgumentParser(description="CDJ-100X Bridge")
    parser.add_argument("--no-gpio", action="store_true",
                        help="Disable GPIO-MIDI bridge (for testing without hardware)")
    parser.add_argument("--no-rekordbox", action="store_true",
                        help="Disable Rekordbox USB monitor")
    parser.add_argument("--no-prodj", action="store_true",
                        help="Disable Pro DJ Link bridge")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    bridge = CDJ100XBridge(
        enable_gpio=not args.no_gpio,
        enable_rekordbox=not args.no_rekordbox,
        enable_prodj=not args.no_prodj,
    )

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    bridge.start()
    bridge.run_forever()


if __name__ == "__main__":
    main()
