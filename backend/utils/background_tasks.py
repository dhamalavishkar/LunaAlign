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

    async def connect(self, websocket: WebSocket, session_id: str):
        # For WebSocket connections, we need to handle CORS manually.
        # In a production environment, you should validate the origin against a list of allowed origins.
        # For this demo, we accept all origins to allow the frontend (localhost:5173) to connect.
        # Origin can be retrieved from websocket.headers.get("origin")
        origin = websocket.headers.get("origin")
        print(f"WebSocket connection attempt from origin: {origin}")
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connection accepted for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def broadcast_progress(self, session_id: str, stage: str, progress: int, metrics: dict = None):
        """
        Pushes a JSON payload to the specific active session socket.
        """
        if session_id in self.active_connections:
            payload = {
                "stage": stage,
                "progress": progress
            }
            if metrics:
                payload["metrics"] = metrics
                
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(payload))
            except Exception as e:
                print(f"Error broadcasting to socket {session_id}: {e}")
                self.disconnect(session_id)

# Global Manager Instance
manager = ConnectionManager()
