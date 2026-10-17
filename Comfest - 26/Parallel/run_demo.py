"""
Quickstart Launcher for Decentralized URL Trust Verifier.
Runs Flask Web Server and serves the UI + APIs.
"""
import os
import sys
import webbrowser
import threading
import time

def open_browser(port):
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n[LAUNCHER] Opening browser at {url}...")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[LAUNCHER] Note: Could not auto-open browser: {e}")

if __name__ == "__main__":
    from backend.app import app

    port = 5000
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    print("\n" + "="*60)
    print("  🚀 DECENTRALIZED URL TRUST VERIFIER (WEB3 SECURITY MVP)")
    print("="*60)
    print(f"  • Interface URL:    http://127.0.0.1:{port}")
    print(f"  • Health & Status:  http://127.0.0.1:{port}/api/status")
    print(f"  • Check Endpoint:   http://127.0.0.1:{port}/api/check?url=ethereum.org")
    print(f"  • Register API:     http://127.0.0.1:{port}/api/register")
    print("="*60 + "\n")

    app.run(host="127.0.0.1", port=port, debug=False)
