/**
 * TypeScript types for Splendor game state.
 * These mirror the Python Pydantic schemas.
 */

export type GemType = 'diamond' | 'sapphire' | 'emerald' | 'ruby' | 'onyx' | 'gold';

export const BASE_GEMS: GemType[] = ['diamond', 'sapphire', 'emerald', 'ruby', 'onyx'];
export const ALL_GEMS: GemType[] = [...BASE_GEMS, 'gold'];

export interface GemCollection {
  diamond: number;
  sapphire: number;
  emerald: number;
  ruby: number;
  onyx: number;
  gold: number;
}

export interface Card {
  id: string;
  tier: 1 | 2 | 3;
  bonus: GemType;
  points: number;
  cost: GemCollection;
}

export interface HiddenCard {
  hidden: true;
  tier: 1 | 2 | 3;
}

export type ReservedCard = Card | HiddenCard;

export function isHiddenCard(card: ReservedCard): card is HiddenCard {
  return 'hidden' in card && card.hidden === true;
}

export interface Noble {
  id: string;
  points: number;
  requirements: GemCollection;
}

export interface Player {
  id: number;
  tokens: GemCollection;
  bonuses: GemCollection;
  points: number;
  card_count: number;
  cards: Card[];
  reserved: ReservedCard[];
  noble_count: number;
  nobles: Noble[];
}

export interface GameState {
  room_id: string;
  your_seat: number;
  is_your_turn: boolean;
  current_player_idx: number;
  turn_number: number;
  is_final_round: boolean;
  game_over: boolean;
  winner: number | null;
  
  bank: GemCollection;
  nobles: Noble[];
  visible_cards: Record<string, Card[]>;
  deck_counts: Record<string, number>;
  
  // Players array is rotated so you (the requesting player) are at index 0
  players: Player[];
}

// Room types
export interface SeatInfo {
  seat: number;
  player_name: string | null;
  is_bot: boolean;
  bot_policy: string | null;
  is_connected: boolean;
}

export interface RoomInfo {
  room_id: string;
  num_players: number;
  seats: SeatInfo[];
  game_started: boolean;
  host_seat: number;
}

// Action types
export interface TakeThreeDifferentAction {
  type: 'take_three_different';
  gems: GemType[];
  return_gems?: GemType[];
}

export interface TakeTwoSameAction {
  type: 'take_two_same';
  gem: GemType;
  return_gems?: GemType[];
}

export interface ReserveVisibleAction {
  type: 'reserve_visible';
  card_id: string;
  return_gems?: GemType[];
}

export interface ReserveFromDeckAction {
  type: 'reserve_from_deck';
  tier: 1 | 2 | 3;
  return_gems?: GemType[];
}

export interface PurchaseVisibleAction {
  type: 'purchase_visible';
  card_id: string;
}

export interface PurchaseReservedAction {
  type: 'purchase_reserved';
  card_id: string;
}

export type GameAction =
  | TakeThreeDifferentAction
  | TakeTwoSameAction
  | ReserveVisibleAction
  | ReserveFromDeckAction
  | PurchaseVisibleAction
  | PurchaseReservedAction;

// API Response types
export interface CreateRoomResponse {
  room_id: string;
  player_token: string;
  seat: number;
}

export interface JoinRoomResponse {
  player_token: string;
  seat: number;
}

export interface ActionResponse {
  success: boolean;
  error?: string;
}

// Gem colors for rendering
export const GEM_COLORS: Record<GemType, string> = {
  diamond: '#e8e8e8',
  sapphire: '#3b82f6',
  emerald: '#22c55e',
  ruby: '#ef4444',
  onyx: '#1f2937',
  gold: '#fbbf24',
};

export const GEM_TEXT_COLORS: Record<GemType, string> = {
  diamond: '#1f2937',
  sapphire: '#ffffff',
  emerald: '#ffffff',
  ruby: '#ffffff',
  onyx: '#ffffff',
  gold: '#1f2937',
};

// Helper to count total tokens
export function totalTokens(gems: GemCollection): number {
  return gems.diamond + gems.sapphire + gems.emerald + gems.ruby + gems.onyx + gems.gold;
}

// Helper to check if can afford
export function canAfford(cost: GemCollection, tokens: GemCollection, bonuses: GemCollection): boolean {
  let goldNeeded = 0;
  
  for (const gem of BASE_GEMS) {
    const gemCost = cost[gem];
    const available = tokens[gem] + bonuses[gem];
    const shortfall = gemCost - available;
    if (shortfall > 0) {
      goldNeeded += shortfall;
    }
  }
  
  return goldNeeded <= tokens.gold;
}

