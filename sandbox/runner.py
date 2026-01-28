"""
Sandbox runner - placeholder for isolated execution
In MVP, execution happens in backend process with multiprocessing
This container is for future expansion
"""
import time
import sys

print("🔒 Sandbox container running", file=sys.stderr)
print("Waiting for execution requests...", file=sys.stderr)

# Keep container alive
while True:
    time.sleep(60)
