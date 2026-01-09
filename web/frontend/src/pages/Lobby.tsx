import { useState } from 'react';
import { useNavigate, useParams } from '@tanstack/react-router';
import {
  storeSession,
  getStoredSession,
  useRoomInfo,
  useCreateRoom,
  useJoinRoom,
  useConfigureSeat,
  useStartGame,
} from '../api/client';
import type { SeatInfo } from '../types/game';

type LobbyMode = 'menu' | 'create' | 'join' | 'waiting';

export function Lobby() {
  const navigate = useNavigate();
  const params = useParams({ strict: false });
  const joinRoomId = params.roomId || null;
  
  // Form state
  const [mode, setMode] = useState<LobbyMode>(joinRoomId ? 'join' : 'menu');
  const [playerName, setPlayerName] = useState('');
  const [numPlayers, setNumPlayers] = useState<2 | 3 | 4>(2);
  const [joinCode, setJoinCode] = useState(joinRoomId || '');
  const [error, setError] = useState<string | null>(null);
  
  // Session state
  const [roomId, setRoomId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [mySeat, setMySeat] = useState<number | null>(null);
  
  // Queries and mutations
  const { data: roomInfo } = useRoomInfo(roomId, mode === 'waiting');
  const createRoomMutation = useCreateRoom();
  const joinRoomMutation = useJoinRoom();
  const configureSeatMutation = useConfigureSeat(roomId || '', token || '');
  const startGameMutation = useStartGame(roomId || '', token || '');

  // Navigate to game when it starts
  if (roomInfo?.game_started && roomId) {
    navigate({ to: '/game/$roomId', params: { roomId } });
  }

  const handleCreateRoom = () => {
    if (!playerName.trim()) {
      setError('Please enter your name');
      return;
    }
    
    setError(null);
    createRoomMutation.mutate(
      { numPlayers, playerName: playerName.trim() },
      {
        onSuccess: (response) => {
          storeSession(response.player_token, response.room_id);
          setRoomId(response.room_id);
          setToken(response.player_token);
          setMySeat(response.seat);
          setMode('waiting');
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Failed to create room');
        },
      }
    );
  };

  const handleJoinRoom = () => {
    if (!playerName.trim()) {
      setError('Please enter your name');
      return;
    }
    if (!joinCode.trim()) {
      setError('Please enter a room code');
      return;
    }
    
    const code = joinCode.trim().toUpperCase();
    setError(null);
    
    joinRoomMutation.mutate(
      { roomId: code, playerName: playerName.trim() },
      {
        onSuccess: (response) => {
          storeSession(response.player_token, code);
          setRoomId(code);
          setToken(response.player_token);
          setMySeat(response.seat);
          setMode('waiting');
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Failed to join room');
        },
      }
    );
  };

  const handleToggleBot = (seat: number) => {
    if (!roomInfo) return;
    
    const seatInfo = roomInfo.seats[seat];
    configureSeatMutation.mutate(
      { seat, isBot: !seatInfo.is_bot },
      {
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Failed to configure seat');
        },
      }
    );
  };

  const handleStartGame = () => {
    setError(null);
    startGameMutation.mutate(undefined, {
      onError: (err) => {
        setError(err instanceof Error ? err.message : 'Failed to start game');
      },
    });
  };

  const isHost = roomInfo && mySeat === roomInfo.host_seat;
  const canStart = roomInfo && roomInfo.seats.every(s => s.player_name !== null || s.is_bot);
  const isLoading = createRoomMutation.isPending || joinRoomMutation.isPending || startGameMutation.isPending;

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        {/* Title */}
        <div className="text-center mb-8 animate-slide-up">
          <h1 className="text-5xl font-display font-bold text-highlight mb-2">
            SPLENDOR
          </h1>
          <p className="text-gray-400">
            A game of gem collection and prestige
          </p>
        </div>

        {/* Main Menu */}
        {mode === 'menu' && (
          <div className="space-y-4 animate-slide-up">
            <button
              onClick={() => setMode('create')}
              className="w-full btn btn-primary text-xl py-4"
              data-testid="create-room"
            >
              Create New Game
            </button>
            <button
              onClick={() => setMode('join')}
              className="w-full btn btn-secondary text-xl py-4"
              data-testid="join-room-btn"
            >
              Join Game
            </button>
          </div>
        )}

        {/* Create Room Form */}
        {mode === 'create' && (
          <div className="bg-panel rounded-xl p-6 animate-slide-up" data-testid="create-form">
            <h2 className="text-2xl font-display mb-6">Create Game</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Your Name</label>
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  className="w-full bg-board border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-highlight"
                  placeholder="Enter your name"
                  maxLength={20}
                  data-testid="player-name"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">Number of Players</label>
                <div className="flex gap-2">
                  {([2, 3, 4] as const).map((n) => (
                    <button
                      key={n}
                      onClick={() => setNumPlayers(n)}
                      className={`flex-1 py-2 rounded-lg border transition-colors ${
                        numPlayers === n
                          ? 'bg-highlight text-board border-highlight'
                          : 'bg-board border-gray-600 hover:border-gray-500'
                      }`}
                      data-testid={`num-players-${n}`}
                    >
                      {n} Players
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <p className="text-red-400 text-sm">{error}</p>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => { setMode('menu'); setError(null); }}
                  className="btn btn-secondary flex-1"
                >
                  Back
                </button>
                <button
                  onClick={handleCreateRoom}
                  disabled={isLoading}
                  className="btn btn-primary flex-1"
                  data-testid="start-room"
                >
                  {isLoading ? 'Creating...' : 'Create Room'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Join Room Form */}
        {mode === 'join' && (
          <div className="bg-panel rounded-xl p-6 animate-slide-up" data-testid="join-form">
            <h2 className="text-2xl font-display mb-6">Join Game</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Your Name</label>
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  className="w-full bg-board border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-highlight"
                  placeholder="Enter your name"
                  maxLength={20}
                  data-testid="player-name"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Room Code</label>
                <input
                  type="text"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  className="w-full bg-board border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-highlight text-center text-2xl tracking-widest"
                  placeholder="ABC123"
                  maxLength={6}
                  data-testid="join-code"
                />
              </div>

              {error && (
                <p className="text-red-400 text-sm">{error}</p>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => { setMode('menu'); setError(null); }}
                  className="btn btn-secondary flex-1"
                >
                  Back
                </button>
                <button
                  onClick={handleJoinRoom}
                  disabled={isLoading}
                  className="btn btn-primary flex-1"
                  data-testid="join-room"
                >
                  {isLoading ? 'Joining...' : 'Join Room'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Waiting Room */}
        {mode === 'waiting' && roomInfo && (
          <div className="bg-panel rounded-xl p-6 animate-slide-up">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-display mb-2">Room Code</h2>
              <div
                className="text-4xl font-mono tracking-widest text-highlight"
                data-testid="room-code"
              >
                {roomId}
              </div>
              <p className="text-sm text-gray-400 mt-2">
                Share this code with friends to join
              </p>
            </div>

            <div className="space-y-3 mb-6">
              <h3 className="text-lg font-semibold">Players</h3>
              {roomInfo.seats.map((seat, idx) => (
                <SeatRow
                  key={idx}
                  seat={seat}
                  isMe={idx === mySeat}
                  isHost={isHost || false}
                  onToggleBot={() => handleToggleBot(idx)}
                />
              ))}
            </div>

            {error && (
              <p className="text-red-400 text-sm mb-4">{error}</p>
            )}

            {isHost ? (
              <button
                onClick={handleStartGame}
                disabled={isLoading || !canStart}
                className="w-full btn btn-primary text-lg py-3"
                data-testid="start-game"
              >
                {isLoading ? 'Starting...' : canStart ? 'Start Game' : 'Waiting for players...'}
              </button>
            ) : (
              <p className="text-center text-gray-400">
                Waiting for host to start the game...
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SeatRow({
  seat,
  isMe,
  isHost,
  onToggleBot,
}: {
  seat: SeatInfo;
  isMe: boolean;
  isHost: boolean;
  onToggleBot: () => void;
}) {
  const isEmpty = !seat.player_name && !seat.is_bot;
  
  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg ${
        isMe ? 'bg-highlight/20 border border-highlight/50' : 'bg-board'
      }`}
      data-testid={`seat-${seat.seat}`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
            seat.is_bot
              ? 'bg-purple-600'
              : seat.player_name
              ? 'bg-highlight text-board'
              : 'bg-gray-600'
          }`}
        >
          {seat.is_bot ? '🤖' : seat.player_name?.[0]?.toUpperCase() || '?'}
        </div>
        <div>
          <div className="font-medium">
            {seat.is_bot ? `Bot ${seat.seat + 1}` : seat.player_name || 'Empty'}
            {isMe && <span className="text-highlight ml-2">(You)</span>}
          </div>
          {seat.is_bot && (
            <div className="text-xs text-gray-400">
              {seat.bot_policy === 'ppo' ? 'PPO AI' : 'Random'}
            </div>
          )}
        </div>
      </div>
      
      {isHost && !isMe && (
        <button
          onClick={onToggleBot}
          className="btn btn-secondary text-sm py-1"
          data-testid={`toggle-bot-${seat.seat}`}
        >
          {isEmpty ? 'Add Bot' : seat.is_bot ? 'Remove Bot' : 'Replace with Bot'}
        </button>
      )}
    </div>
  );
}
