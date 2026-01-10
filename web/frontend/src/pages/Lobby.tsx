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
  useModels,
} from '../api/client';
import type { SeatInfo, ModelMetadata } from '../types/game';

type LobbyMode = 'menu' | 'create' | 'join' | 'waiting';

// Available player emojis
const PLAYER_EMOJIS = [
  '😎', '🦊', '🐺', '🦁', '🐯', '🐻', '🐼', '🐨',
  '🦄', '🐲', '🦅', '🦉', '🐢', '🦋', '🌟', '⚡',
  '🔥', '💎', '👑', '🎭', '🎪', '🎯', '🎲', '🃏',
  '🌸', '🌺', '🍀', '🌙', '☀️', '❄️', '🌊', '🏔️',
];

export function Lobby() {
  const navigate = useNavigate();
  const params = useParams({ strict: false });
  const joinRoomId = params.roomId || null;
  
  // Form state
  const [mode, setMode] = useState<LobbyMode>(joinRoomId ? 'join' : 'menu');
  const [playerName, setPlayerName] = useState('');
  const [playerEmoji, setPlayerEmoji] = useState('😎');
  const [numPlayers, setNumPlayers] = useState<2 | 3 | 4>(2);
  const [joinCode, setJoinCode] = useState(joinRoomId || '');
  const [error, setError] = useState<string | null>(null);
  
  // Session state
  const [roomId, setRoomId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [mySeat, setMySeat] = useState<number | null>(null);
  
  // Queries and mutations
  const { data: roomInfo } = useRoomInfo(roomId, mode === 'waiting');
  const { data: models } = useModels();
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
      { numPlayers, playerName: playerName.trim(), playerEmoji },
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
      { roomId: code, playerName: playerName.trim(), playerEmoji },
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

  const handleConfigureSeat = (seat: number, isBot: boolean, modelId?: string) => {
    if (!roomInfo) return;
    
    configureSeatMutation.mutate(
      { seat, isBot, modelId: modelId || 'random' },
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
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      const current = PLAYER_EMOJIS.indexOf(playerEmoji);
                      const next = (current + 1) % PLAYER_EMOJIS.length;
                      setPlayerEmoji(PLAYER_EMOJIS[next]);
                    }}
                    className="w-12 h-12 text-2xl bg-board border border-gray-600 rounded-lg hover:border-highlight transition-colors flex items-center justify-center"
                    data-testid="emoji-picker"
                    title="Click to change emoji"
                  >
                    {playerEmoji}
                  </button>
                  <input
                    type="text"
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    className="flex-1 bg-board border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-highlight"
                    placeholder="Enter your name"
                    maxLength={20}
                    data-testid="player-name"
                  />
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {PLAYER_EMOJIS.slice(0, 16).map((emoji) => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => setPlayerEmoji(emoji)}
                      className={`w-8 h-8 text-lg rounded transition-all ${
                        playerEmoji === emoji
                          ? 'bg-highlight/30 scale-110'
                          : 'hover:bg-gray-700'
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
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
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      const current = PLAYER_EMOJIS.indexOf(playerEmoji);
                      const next = (current + 1) % PLAYER_EMOJIS.length;
                      setPlayerEmoji(PLAYER_EMOJIS[next]);
                    }}
                    className="w-12 h-12 text-2xl bg-board border border-gray-600 rounded-lg hover:border-highlight transition-colors flex items-center justify-center"
                    data-testid="emoji-picker"
                    title="Click to change emoji"
                  >
                    {playerEmoji}
                  </button>
                  <input
                    type="text"
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    className="flex-1 bg-board border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-highlight"
                    placeholder="Enter your name"
                    maxLength={20}
                    data-testid="player-name"
                  />
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {PLAYER_EMOJIS.slice(0, 16).map((emoji) => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => setPlayerEmoji(emoji)}
                      className={`w-8 h-8 text-lg rounded transition-all ${
                        playerEmoji === emoji
                          ? 'bg-highlight/30 scale-110'
                          : 'hover:bg-gray-700'
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
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
                  models={models || []}
                  onConfigureSeat={(isBot, modelId) => handleConfigureSeat(idx, isBot, modelId)}
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
  models,
  onConfigureSeat,
}: {
  seat: SeatInfo;
  isMe: boolean;
  isHost: boolean;
  models: ModelMetadata[];
  onConfigureSeat: (isBot: boolean, modelId?: string) => void;
}) {
  const [showModelSelect, setShowModelSelect] = useState(false);
  const isEmpty = !seat.player_name && !seat.is_bot;
  
  const handleAddBot = (modelId: string) => {
    onConfigureSeat(true, modelId);
    setShowModelSelect(false);
  };
  
  const handleRemoveBot = () => {
    onConfigureSeat(false);
    setShowModelSelect(false);
  };
  
  // Find current model for display
  const currentModel = models.find(m => m.id === seat.model_id);
  
  return (
    <div
      className={`p-3 rounded-lg ${
        isMe ? 'bg-highlight/20 border border-highlight/50' : 'bg-board'
      }`}
      data-testid={`seat-${seat.seat}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center text-xl ${
              seat.is_bot
                ? 'bg-gradient-to-br from-violet-600 to-purple-700'
                : seat.player_name
                ? 'bg-highlight/20 border-2 border-highlight/50'
                : 'bg-gray-600'
            }`}
          >
            {seat.player_emoji || (seat.is_bot ? (seat.model_icon || '🧠') : '?')}
          </div>
          <div>
            <div className="font-medium">
              {seat.player_name || 'Empty'}
              {isMe && <span className="text-highlight ml-2">(You)</span>}
            </div>
            {seat.is_bot && currentModel && (
              <div className="text-xs text-gray-400 flex items-center gap-1">
                {currentModel.type === 'neural' ? (
                  <>
                    <span className="text-violet-400">{currentModel.algorithm}</span>
                    {currentModel.training_steps && (
                      <span>• {formatSteps(currentModel.training_steps)} steps</span>
                    )}
                  </>
                ) : (
                  <span>{currentModel.description}</span>
                )}
              </div>
            )}
          </div>
        </div>
        
        {isHost && !isMe && (
          <div className="relative">
            {seat.is_bot ? (
              <div className="flex gap-2">
                <button
                  onClick={() => setShowModelSelect(!showModelSelect)}
                  className="btn btn-secondary text-sm py-1"
                  data-testid={`change-model-${seat.seat}`}
                >
                  Change
                </button>
                <button
                  onClick={handleRemoveBot}
                  className="btn btn-secondary text-sm py-1 text-red-400 hover:text-red-300"
                  data-testid={`remove-bot-${seat.seat}`}
                >
                  Remove
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowModelSelect(!showModelSelect)}
                className="btn btn-secondary text-sm py-1"
                data-testid={`toggle-bot-${seat.seat}`}
              >
                {isEmpty ? 'Add Bot' : 'Replace'}
              </button>
            )}
          </div>
        )}
      </div>
      
      {/* Model Selection Dropdown */}
      {showModelSelect && isHost && !isMe && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <div className="text-sm text-gray-400 mb-2">Select AI Model:</div>
          <div className="space-y-2">
            {models.map((model) => (
              <button
                key={model.id}
                onClick={() => handleAddBot(model.id)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  seat.model_id === model.id
                    ? 'bg-violet-600/30 border border-violet-500'
                    : 'bg-panel hover:bg-gray-700 border border-transparent'
                }`}
                data-testid={`select-model-${model.id}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{model.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium flex items-center gap-2">
                      {model.name}
                      {model.type === 'neural' && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-violet-600/50 text-violet-200">
                          {model.algorithm}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {model.description}
                    </div>
                    {model.type === 'neural' && model.network && (
                      <div className="text-xs text-gray-500 mt-1 flex flex-wrap gap-x-3">
                        <span>Network: {model.network.architecture.join('×')}</span>
                        {model.training_steps && (
                          <span>Steps: {formatSteps(model.training_steps)}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatSteps(steps: number): string {
  if (steps >= 1_000_000) {
    return `${(steps / 1_000_000).toFixed(1)}M`;
  }
  if (steps >= 1_000) {
    return `${(steps / 1_000).toFixed(0)}K`;
  }
  return steps.toString();
}
