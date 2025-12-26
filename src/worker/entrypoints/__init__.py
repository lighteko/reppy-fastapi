"""Entrypoints for the worker."""

from .oci_function import handler
from .local_runner import run_local

__all__ = ["handler", "run_local"]

