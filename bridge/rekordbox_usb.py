"""
Rekordbox USB Library Reader for CDJ-100X.

Monitors USB mount events and parses Rekordbox-exported USB sticks
using python-prodj-link's PDB parser. Extracts tracks, playlists,
cue points, artwork, and waveform data.
"""

import os
import logging
import threading
import time

from bridge.config import USB_MOUNT_BASE, REKORDBOX_PDB_PATH, REKORDBOX_ANLZ_PATH

logger = logging.getLogger(__name__)


class RekordboxUSB:
    """Detects and reads Rekordbox-exported USB sticks."""

    def __init__(self, pdb_provider=None):
        self._running = False
        self._monitor_thread = None
        self._mounted_usb = None
        self._pdb_provider = pdb_provider  # python-prodj-link PDBProvider if available
        self._tracks = []
        self._playlists = {}
        self._on_library_loaded = None

    def set_library_loaded_callback(self, callback):
        """Set callback for when a Rekordbox library is loaded.

        callback(tracks, playlists) where:
          tracks: list of track dicts
          playlists: dict of playlist_name -> list of track_ids
        """
        self._on_library_loaded = callback

    def start(self):
        """Start monitoring for USB mount events."""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Rekordbox USB monitor started, watching %s", USB_MOUNT_BASE)

    def stop(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    @property
    def tracks(self):
        return self._tracks

    @property
    def playlists(self):
        return self._playlists

    @property
    def is_loaded(self):
        return len(self._tracks) > 0

    def get_track(self, track_id):
        """Get track info by ID."""
        for track in self._tracks:
            if track.get("id") == track_id:
                return track
        return None

    def _monitor_loop(self):
        """Poll for USB mounts with Rekordbox data."""
        while self._running:
            try:
                self._check_usb_mounts()
            except Exception:
                logger.debug("USB monitor error", exc_info=True)
            time.sleep(2)

    def _check_usb_mounts(self):
        """Scan mount points for Rekordbox USB sticks."""
        if not os.path.isdir(USB_MOUNT_BASE):
            return

        for entry in os.listdir(USB_MOUNT_BASE):
            mount_path = os.path.join(USB_MOUNT_BASE, entry)
            if not os.path.isdir(mount_path):
                continue

            pdb_path = os.path.join(mount_path, REKORDBOX_PDB_PATH)

            if os.path.isfile(pdb_path):
                if self._mounted_usb != mount_path:
                    logger.info("Rekordbox USB detected at %s", mount_path)
                    self._mounted_usb = mount_path
                    self._load_library(mount_path, pdb_path)
            elif self._mounted_usb == mount_path:
                # USB was removed
                logger.info("Rekordbox USB removed from %s", mount_path)
                self._mounted_usb = None
                self._tracks = []
                self._playlists = {}

    def _load_library(self, usb_path, pdb_path):
        """Parse the Rekordbox PDB file and extract track data."""
        try:
            self._parse_pdb(usb_path, pdb_path)
            logger.info("Loaded %d tracks from Rekordbox USB", len(self._tracks))

            if self._on_library_loaded:
                self._on_library_loaded(self._tracks, self._playlists)

        except Exception:
            logger.exception("Failed to parse Rekordbox PDB at %s", pdb_path)

    def _parse_pdb(self, usb_path, pdb_path):
        """Parse PDB file using python-prodj-link's pdblib if available,
        otherwise use a minimal built-in parser."""
        try:
            from prodj.pdblib.pdbfile import PDBFile
            self._parse_with_prodj(usb_path, pdb_path)
        except ImportError:
            logger.warning("python-prodj-link not available, using minimal PDB parser")
            self._parse_minimal(usb_path, pdb_path)

    def _parse_with_prodj(self, usb_path, pdb_path):
        """Parse PDB using python-prodj-link's full parser."""
        from prodj.pdblib.pdbfile import PDBFile

        pdb = PDBFile(pdb_path)

        self._tracks = []
        for track in pdb.get_tracks():
            track_info = {
                "id": track.id,
                "title": track.title or "Unknown",
                "artist": self._resolve_name(pdb, "artists", track.artist_id),
                "album": self._resolve_name(pdb, "albums", track.album_id),
                "genre": self._resolve_name(pdb, "genres", track.genre_id),
                "bpm": track.tempo / 100.0 if hasattr(track, "tempo") else 0,
                "duration": getattr(track, "duration", 0),
                "key": self._resolve_name(pdb, "keys", getattr(track, "key_id", 0)),
                "rating": getattr(track, "rating", 0),
                "bitrate": getattr(track, "bitrate", 0),
                "path": self._resolve_file_path(usb_path, track),
                "artwork_id": getattr(track, "artwork_id", 0),
            }
            self._tracks.append(track_info)

        # Parse playlists if available
        self._playlists = {}
        try:
            for playlist in pdb.get_playlists():
                name = getattr(playlist, "name", f"Playlist {playlist.id}")
                track_ids = getattr(playlist, "track_ids", [])
                self._playlists[name] = track_ids
        except Exception:
            logger.debug("No playlists found in PDB")

    def _resolve_name(self, pdb, table_name, item_id):
        """Resolve an ID to a name string from the PDB."""
        if not item_id:
            return ""
        try:
            items = getattr(pdb, f"get_{table_name}")()
            for item in items:
                if item.id == item_id:
                    return item.name or ""
        except Exception:
            pass
        return ""

    def _resolve_file_path(self, usb_path, track):
        """Convert Rekordbox internal path to actual filesystem path."""
        raw_path = getattr(track, "path", "") or getattr(track, "filename", "")
        if not raw_path:
            return ""
        # Rekordbox paths are typically like "/Contents/..." relative to USB root
        # Strip leading slash and join with USB mount path
        clean = raw_path.lstrip("/")
        return os.path.join(usb_path, clean)

    def _parse_minimal(self, usb_path, pdb_path):
        """Minimal fallback: just list audio files on the USB."""
        self._tracks = []
        audio_extensions = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".aiff", ".ogg"}
        track_id = 1

        for root, dirs, files in os.walk(usb_path):
            # Skip Rekordbox system directories
            if "PIONEER" in root:
                continue
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in audio_extensions:
                    self._tracks.append({
                        "id": track_id,
                        "title": os.path.splitext(f)[0],
                        "artist": "",
                        "album": "",
                        "genre": "",
                        "bpm": 0,
                        "duration": 0,
                        "key": "",
                        "rating": 0,
                        "bitrate": 0,
                        "path": os.path.join(root, f),
                        "artwork_id": 0,
                    })
                    track_id += 1

    def generate_m3u_playlists(self, output_dir):
        """Generate M3U playlist files from Rekordbox playlists.

        This allows Mixxx to import the playlists through its normal
        playlist import feature.
        """
        os.makedirs(output_dir, exist_ok=True)
        generated = []

        for name, track_ids in self._playlists.items():
            safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
            m3u_path = os.path.join(output_dir, f"{safe_name}.m3u")

            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for tid in track_ids:
                    track = self.get_track(tid)
                    if track and track["path"]:
                        duration = track.get("duration", 0)
                        title = track.get("title", "Unknown")
                        artist = track.get("artist", "")
                        display = f"{artist} - {title}" if artist else title
                        f.write(f"#EXTINF:{duration},{display}\n")
                        f.write(f"{track['path']}\n")

            generated.append(m3u_path)
            logger.info("Generated M3U playlist: %s (%d tracks)", m3u_path, len(track_ids))

        return generated
