#!/usr/bin/env python3
# ==============================================================================
# X4: Foundations (v8.0+) - Supreme Command & Empire Intelligence Terminal
# Version: V1.7.7 Enterprise - Supreme Intelligence Edition
# Launcher: python x4_supreme_auditor_1_7_7.py [save] [--game-dir PATH] [--out PATH] [--html PATH]
# ==============================================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from x4_supreme_auditor.cli import main

if __name__ == "__main__":
    main()
