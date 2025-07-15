#!/usr/bin/env python3
"""
Health check script for the OpenAI proxy
"""

import sys
import requests

def check_health():
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        if response.status_code == 200:
            return 0
        else:
            return 1
    except Exception:
        return 1

if __name__ == "__main__":
    sys.exit(check_health())