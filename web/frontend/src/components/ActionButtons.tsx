import type { GemType, Card } from '../types/game';

interface ActionButtonsProps {
  // Selection state
  selectedGems: GemType[];
  selectedCard: Card | null;
  selectedDeckTier: number | null;
  selectedReservedCard: Card | null;
  
  // Validity checks
  canTakeGems: boolean;
  canBuyCard: boolean;
  canReserve: boolean;
  
  // Actions
  onTakeGems: () => void;
  onBuyCard: () => void;
  onReserveCard: () => void;
  onCancel: () => void;
  
  // State
  isYourTurn: boolean;
  loading?: boolean;
  error?: string | null;
}

export function ActionButtons({
  selectedGems,
  selectedCard,
  selectedDeckTier,
  selectedReservedCard,
  canTakeGems,
  canBuyCard,
  canReserve,
  onTakeGems,
  onBuyCard,
  onReserveCard,
  onCancel,
  isYourTurn,
  loading = false,
  error,
}: ActionButtonsProps) {
  const hasSelection = selectedGems.length > 0 || selectedCard || selectedDeckTier || selectedReservedCard;
  
  if (!isYourTurn) {
    return (
      <div className="flex items-center justify-center gap-2 py-4">
        <div className="animate-pulse text-gray-400">
          Waiting for other player...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3" data-testid="action-buttons">
        {/* Take Gems button */}
        {selectedGems.length > 0 && (
          <button
            onClick={onTakeGems}
            disabled={!canTakeGems || loading}
            className="btn btn-primary"
            data-testid="take-gems-btn"
          >
            Take {selectedGems.length} Gem{selectedGems.length !== 1 ? 's' : ''}
          </button>
        )}
        
        {/* Buy button */}
        {(selectedCard || selectedReservedCard) && (
          <button
            onClick={onBuyCard}
            disabled={!canBuyCard || loading}
            className="btn btn-primary"
            data-testid="buy-btn"
          >
            Buy Card
          </button>
        )}
        
        {/* Reserve button */}
        {(selectedCard || selectedDeckTier) && (
          <button
            onClick={onReserveCard}
            disabled={!canReserve || loading}
            className="btn btn-secondary"
            data-testid="reserve-btn"
          >
            Reserve
          </button>
        )}
        
        {/* Cancel button */}
        {hasSelection && (
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn btn-secondary"
            data-testid="cancel-btn"
          >
            Cancel
          </button>
        )}
        
        {/* No selection hint */}
        {!hasSelection && (
          <div className="text-gray-400 text-sm">
            Select gems to take, or click a card to buy/reserve
          </div>
        )}
        
        {loading && (
          <div className="text-gray-400 text-sm animate-pulse">
            Processing...
          </div>
        )}
      </div>
      
      {/* Selection summary */}
      {hasSelection && (
        <div className="text-sm text-gray-400" data-testid="selected-gems">
          {selectedGems.length > 0 && (
            <span>Selected gems: {selectedGems.join(', ')}</span>
          )}
          {selectedCard && (
            <span>Selected card: {selectedCard.bonus} ({selectedCard.points} pts)</span>
          )}
          {selectedDeckTier && (
            <span>Selected: Tier {selectedDeckTier} deck</span>
          )}
          {selectedReservedCard && (
            <span>Selected reserved: {selectedReservedCard.bonus} ({selectedReservedCard.points} pts)</span>
          )}
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="text-red-400 text-sm" data-testid="action-error">
          {error}
        </div>
      )}
    </div>
  );
}

