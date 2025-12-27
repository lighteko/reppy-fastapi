"""Entrypoints for Reppy Worker.

Note:
We intentionally avoid importing OCI-specific modules at import time so that
`python -m src.entrypoints.local_runner` works in lightweight local dev
environments without the OCI SDK installed.
"""

__all__: list[str] = []

