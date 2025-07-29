#!/usr/bin/env python3
"""
Entry point for LUCA Agent Testing CLI.

Usage:
    python -m agent-test <command> <args>
"""

from .cli import cli

if __name__ == '__main__':
    cli()