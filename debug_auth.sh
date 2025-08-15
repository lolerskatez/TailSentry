#!/bin/bash
# TailSentry Authentication Debug Wrapper
# This script automatically activates the virtual environment

cd /opt/tailsentry
source venv/bin/activate
python3 debug_auth.py
