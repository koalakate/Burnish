"""Ingestion service — converts presentation files to CSM."""

from services.ingestion.pptx_parser import parse_pptx

__all__ = ["parse_pptx"]
