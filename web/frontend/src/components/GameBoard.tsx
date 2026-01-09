import type { GameState, Card as CardType, GemType } from '../types/game';
import { NobleRow } from './Noble';
import { CardRow } from './CardRow';
import { GemBank } from './GemBank';
import { PlayerPanel } from './PlayerPanel';
import { ActionButtons } from './ActionButtons';

interface GameBoardProps {
  state: GameState;
  
  // Selection state
  selectedGems: GemType[];
  selectedCard: CardType | null;
  selectedDeckTier: number | null;
  selectedReservedCard: CardType | null;
  
  // Selection handlers
  onGemClick: (gem: GemType) => void;
  onCardClick: (card: CardType) => void;
  onDeckClick: (tier: 1 | 2 | 3) => void;
  onReservedClick: (card: CardType) => void;
  
  // Action handlers
  onTakeGems: () => void;
  onBuyCard: () => void;
  onReserveCard: () => void;
  onCancel: () => void;
  
  // Action validity
  canTakeGems: boolean;
  canBuyCard: boolean;
  canReserve: boolean;
  
  // UI state
  loading?: boolean;
  error?: string | null;
}

export function GameBoard({
  state,
  selectedGems,
  selectedCard,
  selectedDeckTier,
  selectedReservedCard,
  onGemClick,
  onCardClick,
  onDeckClick,
  onReservedClick,
  onTakeGems,
  onBuyCard,
  onReserveCard,
  onCancel,
  canTakeGems,
  canBuyCard,
  canReserve,
  loading,
  error,
}: GameBoardProps) {
  const currentPlayer = state.players[0]; // Always you (rotated)
  const isYourTurn = state.is_your_turn;
  
  return (
    <div className="flex flex-col gap-4 p-4 max-w-6xl mx-auto" data-testid="game-board">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold">
            Room: <span className="text-highlight">{state.room_id}</span>
          </h1>
          <div className="text-sm text-gray-400" data-testid="current-turn">
            Turn {state.turn_number + 1} • {isYourTurn ? "Your turn" : "Opponent's turn"}
            {state.is_final_round && (
              <span className="text-yellow-400 ml-2">Final Round!</span>
            )}
          </div>
        </div>
        
        {state.game_over && (
          <div className="bg-highlight/20 text-highlight px-4 py-2 rounded-lg font-bold">
            Game Over! {state.winner === state.your_seat ? 'You Win! 🎉' : `Player ${(state.winner ?? 0) + 1} Wins`}
          </div>
        )}
      </div>

      {/* Nobles */}
      <NobleRow nobles={state.nobles} />

      {/* Card rows (tier 3, 2, 1 from top to bottom) */}
      <div className="flex flex-col gap-3">
        {([3, 2, 1] as const).map((tier) => (
          <CardRow
            key={tier}
            tier={tier}
            cards={state.visible_cards[String(tier)] || []}
            deckCount={state.deck_counts[String(tier)] || 0}
            selectedCardId={selectedCard?.id || null}
            selectedDeckTier={selectedDeckTier}
            playerTokens={currentPlayer.tokens}
            playerBonuses={currentPlayer.bonuses}
            onCardClick={onCardClick}
            onDeckClick={onDeckClick}
            disabled={!isYourTurn || state.game_over}
          />
        ))}
      </div>

      {/* Gem bank */}
      <GemBank
        bank={state.bank}
        selectedGems={selectedGems}
        onGemClick={onGemClick}
        disabled={!isYourTurn || state.game_over}
      />

      {/* Action buttons */}
      {!state.game_over && (
        <ActionButtons
          selectedGems={selectedGems}
          selectedCard={selectedCard}
          selectedDeckTier={selectedDeckTier}
          selectedReservedCard={selectedReservedCard}
          canTakeGems={canTakeGems}
          canBuyCard={canBuyCard}
          canReserve={canReserve}
          onTakeGems={onTakeGems}
          onBuyCard={onBuyCard}
          onReserveCard={onReserveCard}
          onCancel={onCancel}
          isYourTurn={isYourTurn}
          loading={loading}
          error={error}
        />
      )}

      {/* Player panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {state.players.map((player, idx) => (
          <PlayerPanel
            key={player.id}
            player={player}
            isCurrentTurn={state.current_player_idx === idx}
            isSelf={idx === 0}
            selectedReservedId={selectedReservedCard?.id || null}
            onReservedClick={idx === 0 ? onReservedClick : undefined}
          />
        ))}
      </div>
    </div>
  );
}

