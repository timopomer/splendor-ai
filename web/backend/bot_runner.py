"""Bot turn execution utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rooms import Room


def execute_bot_turns_sync(room: "Room") -> int:
    """
    Execute bot turns synchronously.
    
    This is called after each human action to let bots play.
    Returns the number of bot actions executed.
    """
    return room.execute_bot_turns()

