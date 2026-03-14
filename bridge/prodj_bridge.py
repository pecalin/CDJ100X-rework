"""
Pro DJ Link Bridge for CDJ-100X.

Makes each modded CDJ-100 appear as a real CDJ on the Pioneer Pro DJ Link
network. Bridges between Mixxx's internal state (via MIDI) and the Pro DJ
Link protocol (via UDP on ports 50000/50001/50002).

Uses python-prodj-link as the protocol implementation.
"""

import logging
import threading
import time

from bridge.config import PLAYER_NUMBER, DEVICE_NAME

logger = logging.getLogger(__name__)


class ProDjBridge:
    """Bridges Mixxx state to/from the Pro DJ Link network."""

    def __init__(self):
        self._running = False
        self._prodj = None
        self._vcdj = None

        # Current player state (updated by Mixxx via MIDI callbacks)
        self.bpm = 0.0
        self.pitch = 0.0         # -1.0 to +1.0
        self.position_ms = 0     # Current position in milliseconds
        self.is_playing = False
        self.track_title = ""
        self.track_artist = ""
        self.beat_count = 0
        self.beat_in_measure = 1  # 1-4

        # Linked player state (received from network)
        self._linked_players = {}
        self._on_player_update = None

    def set_player_update_callback(self, callback):
        """Set callback for when a linked player's state changes.

        callback(player_number, player_info) where player_info is a dict with:
          bpm, pitch, is_playing, track_title, track_artist, beat_count
        """
        self._on_player_update = callback

    def get_linked_players(self):
        """Return dict of player_number -> player state for all discovered players."""
        return dict(self._linked_players)

    def start(self):
        """Start the Pro DJ Link bridge."""
        self._running = True

        try:
            from prodj.core.prodj import ProDj
            self._prodj = ProDj()
            self._prodj.set_client_keepalive_callback(self._on_keepalive)
            self._prodj.set_client_change_callback(self._on_client_change)
            self._prodj.start()
            self._prodj.vcdj_set_player_number(PLAYER_NUMBER)
            self._prodj.vcdj_enable()
            logger.info("Pro DJ Link bridge started as Player %d (%s)",
                        PLAYER_NUMBER, DEVICE_NAME)
        except ImportError:
            logger.warning("python-prodj-link not available — Pro DJ Link disabled")
            self._prodj = None
        except Exception:
            logger.exception("Failed to start Pro DJ Link")
            self._prodj = None

    def stop(self):
        """Stop the Pro DJ Link bridge."""
        self._running = False
        if self._prodj:
            try:
                self._prodj.stop()
            except Exception:
                pass
        logger.info("Pro DJ Link bridge stopped")

    # --- State Update Methods (called by main bridge from MIDI data) ---

    def update_bpm(self, bpm):
        """Update the BPM being broadcast on the network."""
        self.bpm = bpm

    def update_pitch(self, pitch):
        """Update the pitch/rate value (-1.0 to +1.0)."""
        self.pitch = pitch

    def update_playing(self, is_playing):
        """Update the play/pause state."""
        self.is_playing = is_playing

    def update_position(self, position_ms):
        """Update the current playback position in milliseconds."""
        self.position_ms = position_ms

    def update_track_info(self, title="", artist=""):
        """Update the currently loaded track metadata."""
        self.track_title = title
        self.track_artist = artist

    def update_beat(self, beat_count, beat_in_measure):
        """Update the current beat position."""
        self.beat_count = beat_count
        self.beat_in_measure = beat_in_measure

    # --- Remote Commands ---

    def load_track_on_player(self, target_player, source_player, slot, track_id):
        """Send a command to load a track on another CDJ.

        Args:
            target_player: Player number to load track on (1-4)
            source_player: Player number that has the media (1-4)
            slot: Media slot ("usb", "sd", "cd")
            track_id: Rekordbox track ID
        """
        if not self._prodj:
            logger.warning("Cannot load track — Pro DJ Link not available")
            return

        try:
            self._prodj.vcdj.command_load_track(
                player_number=target_player,
                load_player_number=source_player,
                load_slot=slot,
                load_track_id=track_id,
            )
            logger.info("Sent load command: track %d from player %d to player %d",
                        track_id, source_player, target_player)
        except Exception:
            logger.exception("Failed to send load track command")

    # --- Pro DJ Link Callbacks ---

    def _on_keepalive(self, player_number):
        """Called when a player sends a keepalive (discovered or still alive)."""
        if player_number == PLAYER_NUMBER:
            return  # Ignore our own keepalives

        if player_number not in self._linked_players:
            logger.info("Discovered player %d on Pro DJ Link network", player_number)
            self._linked_players[player_number] = {
                "bpm": 0.0,
                "pitch": 0.0,
                "is_playing": False,
                "track_title": "",
                "track_artist": "",
                "beat_count": 0,
            }

    def _on_client_change(self, player_number):
        """Called when a player's state changes."""
        if not self._prodj or player_number == PLAYER_NUMBER:
            return

        try:
            client = self._prodj.cl.getClient(player_number)
            if client is None:
                return

            player_info = {
                "bpm": getattr(client, "bpm", 0.0),
                "pitch": getattr(client, "pitch", 0.0),
                "is_playing": getattr(client, "play_state", "") == "playing",
                "track_title": getattr(client, "track_title", ""),
                "track_artist": getattr(client, "track_artist", ""),
                "beat_count": getattr(client, "beat_count", 0),
                "position": getattr(client, "position", 0),
            }

            self._linked_players[player_number] = player_info

            if self._on_player_update:
                self._on_player_update(player_number, player_info)

        except Exception:
            logger.debug("Error reading client %d state", player_number, exc_info=True)
