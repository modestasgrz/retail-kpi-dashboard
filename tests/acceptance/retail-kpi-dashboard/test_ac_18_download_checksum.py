"""AC-18 — Given download(dest) with the network mocked to return bytes whose SHA-256 differs from DEC-03, then ChecksumError is raised and no file is written to dest."""

import io
from pathlib import Path
from typing import Any

import pytest


def test_ac_18_download_checksum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import kpi.download as d

    def fake(url: str, timeout: float = 0) -> Any:
        return io.BytesIO(b"not the real archive")

    monkeypatch.setattr(d.urllib.request, "urlopen", fake)
    dest = tmp_path / "raw"
    with pytest.raises(d.ChecksumError):
        d.download(dest)
    assert not dest.exists() or not any(dest.iterdir())
