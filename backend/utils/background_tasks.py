import json
from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages active WebSocket connections mapped to their specific Session IDs.
    Ensures that telemetry streams are routed only to the frontend dashboard 
    that requested the computation.
    """
    def __init__(self):
        # Maps session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        self.latest_messages: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        origin = websocket.headers.get("origin")
        print(f"WebSocket connection attempt from origin: {origin}")
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connection accepted for session {session_id}")

        # If there is a buffered latest progress message (e.g. fast completion), send it immediately
        if session_id in self.latest_messages:
            try:
                await websocket.send_text(json.dumps(self.latest_messages[session_id]))
            except Exception as e:
                print(f"Error sending buffered telemetry to {session_id}: {e}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def broadcast_progress(self, session_id: str, stage: str, progress: int, metrics: dict = None):
        """
        Pushes a JSON payload to the specific active session socket.
        """
        payload = {
            "stage": stage,
            "progress": progress
        }
        if metrics:
            payload["metrics"] = metrics
            
        self.latest_messages[session_id] = payload

        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(payload))
            except Exception as e:
                print(f"Error broadcasting to socket {session_id}: {e}")
                self.disconnect(session_id)

# Global Manager Instance
manager = ConnectionManager()
