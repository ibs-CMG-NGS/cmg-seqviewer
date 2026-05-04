import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass
class IGVTrack:
    path: str
    name: str
    genome: str = ""
    color: str = ""


class IGVConnector:
    DEFAULT_PORT = 60151
    TIMEOUT = 1.5

    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self._base = f"http://127.0.0.1:{port}"

    def _get(self, path: str) -> Optional[str]:
        try:
            url = self._base + path
            with urllib.request.urlopen(url, timeout=self.TIMEOUT) as r:
                return r.read().decode()
        except Exception:
            return None

    def is_running(self) -> bool:
        return self._get("/status") is not None

    def goto(self, locus: str) -> bool:
        encoded = urllib.parse.quote(locus)
        return self._get(f"/goto?locus={encoded}") is not None

    def goto_peak(self, chrom: str, start: int, end: int,
                  padding: int = 500) -> bool:
        locus = f"{chrom}:{max(0, start - padding)}-{end + padding}"
        return self.goto(locus)

    def load_track(self, track: IGVTrack) -> bool:
        encoded_path = urllib.parse.quote(track.path)
        encoded_name = urllib.parse.quote(track.name)
        params = f"/load?file={encoded_path}&name={encoded_name}"
        if track.color:
            params += f"&color={urllib.parse.quote(track.color)}"
        return self._get(params) is not None

    def set_genome(self, genome: str) -> bool:
        return self._get(f"/genome?genome={urllib.parse.quote(genome)}") is not None
