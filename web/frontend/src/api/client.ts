/**
 * API client for Splendor backend using TanStack Query.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  GameState,
  RoomInfo,
  GameAction,
  CreateRoomResponse,
  JoinRoomResponse,
  ActionResponse,
  ModelMetadata,
} from '../types/game';

const API_BASE = '/api';

// Session storage keys
const TOKEN_KEY = 'splendor_token';
const ROOM_KEY = 'splendor_room';

export function getStoredSession(): { token: string; roomId: string } | null {
  const token = sessionStorage.getItem(TOKEN_KEY);
  const roomId = sessionStorage.getItem(ROOM_KEY);
  if (token && roomId) {
    return { token, roomId };
  }
  return null;
}

export function storeSession(token: string, roomId: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(ROOM_KEY, roomId);
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(ROOM_KEY);
}

async function fetchWithAuth<T>(
  url: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// --- API Functions ---

export async function createRoom(
  numPlayers: 2 | 3 | 4,
  playerName: string,
  playerEmoji: string = '👤'
): Promise<CreateRoomResponse> {
  return fetchWithAuth('/rooms', {
    method: 'POST',
    body: JSON.stringify({ num_players: numPlayers, player_name: playerName, player_emoji: playerEmoji }),
  });
}

export async function getRoomInfo(roomId: string): Promise<RoomInfo> {
  return fetchWithAuth(`/rooms/${roomId}`);
}

export async function joinRoom(
  roomId: string,
  playerName: string,
  playerEmoji: string = '👤'
): Promise<JoinRoomResponse> {
  return fetchWithAuth(`/rooms/${roomId}/join`, {
    method: 'POST',
    body: JSON.stringify({ player_name: playerName, player_emoji: playerEmoji }),
  });
}

export async function getModels(): Promise<ModelMetadata[]> {
  const response = await fetchWithAuth<{ models: ModelMetadata[] }>('/models');
  return response.models;
}

export async function configureSeat(
  roomId: string,
  token: string,
  seat: number,
  isBot: boolean,
  modelId: string = 'random'
): Promise<void> {
  await fetchWithAuth(
    `/rooms/${roomId}/configure-seat`,
    {
      method: 'POST',
      body: JSON.stringify({ seat, is_bot: isBot, model_id: modelId }),
    },
    token
  );
}

export async function startGame(roomId: string, token: string): Promise<void> {
  await fetchWithAuth(`/rooms/${roomId}/start`, { method: 'POST' }, token);
}

export async function getGameState(
  roomId: string,
  token: string
): Promise<GameState> {
  return fetchWithAuth(`/rooms/${roomId}/state`, {}, token);
}

export async function submitAction(
  roomId: string,
  token: string,
  action: GameAction
): Promise<ActionResponse> {
  return fetchWithAuth(
    `/rooms/${roomId}/action`,
    {
      method: 'POST',
      body: JSON.stringify({ action }),
    },
    token
  );
}

// --- TanStack Query Hooks ---

export function useRoomInfo(roomId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['room', roomId],
    queryFn: () => getRoomInfo(roomId!),
    enabled: enabled && !!roomId,
    refetchInterval: 2000,
    staleTime: 1000,
  });
}

export function useGameState(
  roomId: string | null,
  token: string | null,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['gameState', roomId],
    queryFn: () => getGameState(roomId!, token!),
    enabled: enabled && !!roomId && !!token,
    refetchInterval: (query) => {
      // Poll faster when waiting for opponent
      const state = query.state.data;
      if (state?.game_over) return false;
      return state?.is_your_turn ? 2000 : 1000;
    },
    staleTime: 500,
  });
}

export function useCreateRoom() {
  return useMutation({
    mutationFn: ({ numPlayers, playerName, playerEmoji }: { numPlayers: 2 | 3 | 4; playerName: string; playerEmoji: string }) =>
      createRoom(numPlayers, playerName, playerEmoji),
  });
}

export function useJoinRoom() {
  return useMutation({
    mutationFn: ({ roomId, playerName, playerEmoji }: { roomId: string; playerName: string; playerEmoji: string }) =>
      joinRoom(roomId, playerName, playerEmoji),
  });
}

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: getModels,
    staleTime: 60000, // Models don't change often
  });
}

export function useConfigureSeat(roomId: string, token: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ seat, isBot, modelId }: { seat: number; isBot: boolean; modelId?: string }) =>
      configureSeat(roomId, token, seat, isBot, modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room', roomId] });
    },
  });
}

export function useStartGame(roomId: string, token: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => startGame(roomId, token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room', roomId] });
    },
  });
}

export function useSubmitAction(roomId: string, token: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (action: GameAction) => submitAction(roomId, token, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gameState', roomId] });
    },
  });
}
