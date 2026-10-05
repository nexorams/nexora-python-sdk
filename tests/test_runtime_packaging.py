"""Standalone runtime and packaging contract checks."""

from __future__ import annotations

from pathlib import Path

from nexorams import Nexora, NexoraClient, NexoraError, __version__


def test_public_package_exports_and_version() -> None:
    assert isinstance(__version__, str)
    assert __version__
    assert NexoraClient is Nexora
    assert issubclass(NexoraError, Exception)


def test_server_side_client_defaults_and_sector_resources() -> None:
    key = "nx_test_runtime_contract_123"
    client = Nexora(api_key=key)
    try:
        assert client.environment == "sandbox"
        assert client.base_url.endswith("/developer/v1")
        assert client.school is not None
        assert client.hospital is not None
        assert client.pharmacy is not None
        assert client.hotel is not None
        assert client.company is not None
        assert key not in repr(client)
    finally:
        client.close()


def test_typed_marker_is_packaged_with_source() -> None:
    marker = Path(__file__).parents[1] / "src" / "nexorams" / "py.typed"
    assert marker.is_file()


def test_version_matches_pyproject_and_user_agent():
    """__version__ and the User-Agent (shown in Developer Portal request logs) must match pyproject.toml."""
    import pathlib
    import re

    from nexorams._http import USER_AGENT

    pyproject = (pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE).group(1)
    assert __version__ == declared
    assert USER_AGENT == f"nexorams-python/{declared}"
