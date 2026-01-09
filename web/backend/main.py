"""FastAPI backend for Splendor web game."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for splendor imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from rooms import room_manager, Room
from schemas import (
    CreateRoomRequest,
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    ConfigureSeatRequest,
    RoomInfoSchema,
    SeatInfo,
    GameStateSchema,
    SubmitActionRequest,
    SubmitActionResponse,
)

app = FastAPI(
    title="Splendor Web API",
    description="Backend API for multiplayer Splendor game",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_room_or_404(room_id: str) -> Room:
    """Get room or raise 404."""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


def get_player_seat(room: Room, authorization: Optional[str]) -> int:
    """Get player seat from token or raise 401."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    token = authorization.replace("Bearer ", "")
    seat = room.get_seat_by_token(token)
    if seat is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return seat


@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "game": "splendor"}


@app.post("/rooms", response_model=CreateRoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new game room."""
    room, token, seat = room_manager.create_room(
        num_players=request.num_players,
        player_name=request.player_name,
    )
    return CreateRoomResponse(
        room_id=room.room_id,
        player_token=token,
        seat=seat,
    )


@app.get("/rooms/{room_id}", response_model=RoomInfoSchema)
async def get_room_info(room_id: str):
    """Get room info for lobby display."""
    room = get_room_or_404(room_id)
    
    seats = [
        SeatInfo(
            seat=i,
            player_name=s.player_name,
            is_bot=s.is_bot,
            bot_policy=s.bot_policy if s.is_bot else None,
            is_connected=s.is_connected,
        )
        for i, s in enumerate(room.seats)
    ]
    
    return RoomInfoSchema(
        room_id=room.room_id,
        num_players=room.num_players,
        seats=seats,
        game_started=room.game_started,
        host_seat=room.host_seat,
    )


@app.post("/rooms/{room_id}/join", response_model=JoinRoomResponse)
async def join_room(room_id: str, request: JoinRoomRequest):
    """Join an existing room."""
    room = get_room_or_404(room_id)
    
    if room.game_started:
        raise HTTPException(status_code=400, detail="Game already started")
    
    try:
        token, seat = room.add_player(request.player_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return JoinRoomResponse(player_token=token, seat=seat)


@app.post("/rooms/{room_id}/configure-seat")
async def configure_seat(
    room_id: str,
    request: ConfigureSeatRequest,
    authorization: Optional[str] = Header(None),
):
    """Configure a seat as bot or human (host only)."""
    room = get_room_or_404(room_id)
    seat = get_player_seat(room, authorization)
    
    if seat != room.host_seat:
        raise HTTPException(status_code=403, detail="Only host can configure seats")
    
    try:
        room.configure_seat(request.seat, request.is_bot, request.bot_policy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True}


@app.post("/rooms/{room_id}/start")
async def start_game(
    room_id: str,
    authorization: Optional[str] = Header(None),
):
    """Start the game (host only)."""
    room = get_room_or_404(room_id)
    seat = get_player_seat(room, authorization)
    
    if seat != room.host_seat:
        raise HTTPException(status_code=403, detail="Only host can start game")
    
    try:
        room.start_game()
        # Execute any initial bot turns
        room.execute_bot_turns()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True}


@app.get("/rooms/{room_id}/state", response_model=GameStateSchema)
async def get_game_state(
    room_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get current game state from player's perspective."""
    room = get_room_or_404(room_id)
    seat = get_player_seat(room, authorization)
    
    if not room.game_started:
        raise HTTPException(status_code=400, detail="Game not started")
    
    return room.get_state_for_player(seat)


@app.post("/rooms/{room_id}/action", response_model=SubmitActionResponse)
async def submit_action(
    room_id: str,
    request: SubmitActionRequest,
    authorization: Optional[str] = Header(None),
):
    """Submit a game action."""
    room = get_room_or_404(room_id)
    seat = get_player_seat(room, authorization)
    
    try:
        room.submit_action(seat, request.action)
        # Execute bot turns after human move
        room.execute_bot_turns()
        return SubmitActionResponse(success=True)
    except ValueError as e:
        return SubmitActionResponse(success=False, error=str(e))
    except RuntimeError as e:
        return SubmitActionResponse(success=False, error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
