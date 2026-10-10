#!/usr/bin/env bash
# ThreatDefender AI - one-command start (Linux / macOS)
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
python desktop/launcher.py
