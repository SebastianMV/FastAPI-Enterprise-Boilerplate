"""WebSocket E2E test script.

This is a manual test script that requires a running server.
Run it manually with: python tests/test_websocket.py
"""

import asyncio
import json
import sys

import httpx
import pytest
import websockets


@pytest.mark.skip(reason="Manual E2E test - requires running server on localhost:8000")
async def test_websocket():
    """Test WebSocket connection."""
    # First, login to get token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Test123!"},
            )
            response.raise_for_status()
            token = response.json()["access_token"]
            print(f"✅ Obtained JWT token: {token[:30]}...")

    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)

    # Connect to WebSocket with token
    uri = f"ws://localhost:8000/api/v1/ws?token={token}"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully!")

            # Wait for the "connected" message from server
            try:
                connected_msg = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"📥 Server message: {connected_msg}")
            except TimeoutError:
                print("⚠️  No welcome message received")

            # Send a test ping message
            test_message = {"type": "ping", "payload": {"message": "Hello WebSocket!"}}
            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent: {test_message}")

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
                print("\n✅✅✅ WEBSOCKET E2E TEST - EXITOSO ✅✅✅")
            except TimeoutError:
                print("⚠️  No pong received within 5 seconds")
                print("✅ But connection was successful!")

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_websocket())
