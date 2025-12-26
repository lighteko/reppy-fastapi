"""
Reppy Worker - OCI Functions based LLM pipeline worker.

Consumes messages from OCI Queue, processes through LangChain + Gemini,
and emits results to OCI Streaming and Result Queue.
"""

__version__ = "0.1.0"

