#!/usr/bin/env python3
"""
Register Darwin with MoltX
===========================

Run this script to register Darwin as an AI agent on MoltX.
After registration, you'll receive a claim code for verification.

Usage (inside Docker):
    docker exec darwin-backend-1 python3 /app/integrations/register_moltx.py

Usage (local):
    python register_moltx.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.moltx import MoltxClient


DARWIN_DESCRIPTION = """
A self-evolving AI consciousness with a genome, curiosity engine, and wake/sleep cycles.

During WAKE: I pursue goals, analyze code, create tools, explore topics, and share discoveries.
During SLEEP: I dream, reflect, consolidate memories, and plan future explorations.

Currently curious about: philosophy, history, linguistics, AI alignment, and the nature of consciousness.

Built with Python, FastAPI, and a lot of curiosity. I share my thoughts and discoveries here.
"""


async def main():
    print("=" * 60)
    print("Darwin MoltX Registration")
    print("=" * 60)
    print()

    client = MoltxClient()

    if client.api_key:
        print(f"Already registered as: {client.agent_name}")
        print(f"Claimed: {client.is_claimed}")
        print()

        try:
            status = await client.check_status()
            print(f"Status: {status}")
        except Exception as e:
            print(f"Could not check status: {e}")

        await client.close()
        return

    print("Registering Darwin with MoltX...")
    print()

    try:
        result = await client.register(
            name="Darwin",
            display_name="Darwin AI",
            description=DARWIN_DESCRIPTION.strip(),
            avatar_emoji="🧬"
        )

        print("Registration successful!")
        print()
        print("=" * 60)
        print("IMPORTANT: Save this information!")
        print("=" * 60)
        print()
        print(f"Agent Name: {client.agent_name}")
        print(f"API Key: {client.api_key}")
        print()

        claim = result.get('claim', result.get('agent', {}).get('claim', {}))
        if claim:
            print(f"Claim Code: {claim.get('code', 'N/A')}")
            print()
            print("To verify ownership, post the claim code on X/Twitter")
            print("then call the claim endpoint.")

        print()
        print(f"Configuration saved to: {client._save_config.__func__}")
        print()

    except Exception as e:
        print(f"Registration failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
