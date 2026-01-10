import type { GemType, Card, GemCollection } from '../types/game';
import { GEM_COLORS, GEM_TEXT_COLORS, BASE_GEMS } from '../types/game';

interface ActionButtonsProps {
  // Selection state
  selectedGems: GemType[];
  selectedCard: Card | null;
  selectedDeckTier: number | null;
  selectedReservedCard: Card | null;
  returnGems: GemType[];
  needsReturnGems: boolean;
  requiredReturnCount: number;
  playerTokens: GemCollection;
  
  // Validity checks
  canTakeGems: boolean;
  canBuyCard: boolean;
  canReserve: boolean;
  
  // Actions
  onTakeGems: () => void;
  onBuyCard: () => void;
  onReserveCard: () => void;
  onReturnGemClick: (gem: GemType) => void;
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
  returnGems,
  needsReturnGems,
  requiredReturnCount,
  playerTokens,
  canTakeGems,
  canBuyCard,
  canReserve,
  onTakeGems,
  onBuyCard,
  onReserveCard,
  onReturnGemClick,
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
      
      {/* Return gems selection */}
      {needsReturnGems && (
        <div className="bg-yellow-900/30 border-2 border-yellow-600/50 rounded-lg p-4" data-testid="return-gems-ui">
          <div className="text-sm font-medium text-yellow-300 mb-2">
            You will have more than 10 coins. Select {requiredReturnCount} gem(s) to return
            {returnGems.length === 0 && (
              <span className="text-yellow-400"> (click gem colors in bank above or your tokens below)</span>
            )}:
          </div>
          <div className="flex gap-2 flex-wrap">
            {BASE_GEMS.map((gem) => {
              const playerCount = playerTokens[gem];
              if (playerCount === 0) return null;
              
              const returnCount = returnGems.filter((g) => g === gem).length;
              const remaining = playerCount - returnCount;
              
              return (
                <div key={gem} className="flex flex-col items-center gap-1">
                  <button
                    onClick={() => onReturnGemClick(gem)}
                    disabled={loading || remaining === 0 || returnGems.length >= requiredReturnCount}
                    className={`
                      w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold
                      transition-all
                      ${returnCount > 0 
                        ? 'ring-2 ring-yellow-400 ring-offset-2 ring-offset-yellow-900/30' 
                        : ''}
                      ${remaining === 0 || returnGems.length >= requiredReturnCount ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:scale-110'}
                    `}
                    style={{
                      backgroundColor: GEM_COLORS[gem],
                      color: GEM_TEXT_COLORS[gem],
                    }}
                    title={`You have ${playerCount}, returning ${returnCount}, ${remaining} remaining`}
                    data-testid={`return-gem-${gem}`}
                  >
                    {remaining}
                  </button>
                  {returnCount > 0 && (
                    <div className="text-xs text-yellow-300">
                      -{returnCount}
                    </div>
                  )}
                </div>
              );
            })}
            {/* Gold */}
            {playerTokens.gold > 0 && (() => {
              const goldReturnCount = returnGems.filter((g) => g === 'gold').length;
              const goldRemaining = playerTokens.gold - goldReturnCount;
              return (
                <div className="flex flex-col items-center gap-1">
                  <button
                    onClick={() => onReturnGemClick('gold')}
                    disabled={loading || goldRemaining === 0 || returnGems.length >= requiredReturnCount}
                    className={`
                      w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold
                      transition-all
                      ${goldReturnCount > 0 
                        ? 'ring-2 ring-yellow-400 ring-offset-2 ring-offset-yellow-900/30' 
                        : ''}
                      ${goldRemaining === 0 || returnGems.length >= requiredReturnCount
                        ? 'opacity-50 cursor-not-allowed' 
                        : 'cursor-pointer hover:scale-110'}
                    `}
                    style={{
                      backgroundColor: GEM_COLORS.gold,
                      color: GEM_TEXT_COLORS.gold,
                    }}
                    title={`You have ${playerTokens.gold}, returning ${goldReturnCount}, ${goldRemaining} remaining`}
                    data-testid="return-gem-gold"
                  >
                    {goldRemaining}
                  </button>
                  {goldReturnCount > 0 && (
                    <div className="text-xs text-yellow-300">
                      -{goldReturnCount}
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
          <div className="text-xs text-gray-400 mt-2" data-testid="return-gems-count">
            Selected: {returnGems.length} / {requiredReturnCount}
          </div>
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

