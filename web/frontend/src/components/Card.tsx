import type { Card as CardType, GemCollection } from '../types/game';
import { GEM_COLORS, GEM_TEXT_COLORS, canAfford, BASE_GEMS } from '../types/game';

interface CardProps {
  card: CardType;
  selected?: boolean;
  playerTokens?: GemCollection;
  playerBonuses?: GemCollection;
  onClick?: () => void;
  testId?: string;
}

export function Card({
  card,
  selected = false,
  playerTokens,
  playerBonuses,
  onClick,
  testId,
}: CardProps) {
  const isAffordable = playerTokens && playerBonuses
    ? canAfford(card.cost, playerTokens, playerBonuses)
    : false;
  
  // Count how many gems in cost to size the card appropriately
  const gemCount = BASE_GEMS.filter(g => card.cost[g] > 0).length;
  
  return (
    <div
      onClick={onClick}
      className={`
        card w-32 h-40 flex flex-col cursor-pointer
        ${selected ? 'selected' : ''}
        ${isAffordable ? 'affordable' : ''}
      `}
      style={{
        backgroundColor: GEM_COLORS[card.bonus],
      }}
      data-testid={testId}
    >
      {/* Header with points and bonus */}
      <div className="flex justify-between items-start p-2">
        {card.points > 0 ? (
          <span
            className="text-2xl font-bold"
            style={{ color: GEM_TEXT_COLORS[card.bonus] }}
          >
            {card.points}
          </span>
        ) : (
          <span />
        )}
        <div
          className="w-7 h-7 rounded-md border-2 border-white/50"
          style={{ backgroundColor: GEM_COLORS[card.bonus] }}
        />
      </div>
      
      {/* Cost */}
      <div className="mt-auto p-2 bg-black/30 rounded-b-lg">
        <div className="flex gap-1 justify-center">
          {BASE_GEMS.map((gem) => {
            const cost = card.cost[gem];
            if (cost === 0) return null;
            
            return (
              <div
                key={gem}
                className="w-6 h-6 rounded-md flex items-center justify-center text-sm font-bold"
                style={{
                  backgroundColor: GEM_COLORS[gem],
                  color: GEM_TEXT_COLORS[gem],
                }}
              >
                {cost}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface CardBackProps {
  tier: 1 | 2 | 3;
  count: number;
  selected?: boolean;
  onClick?: () => void;
  testId?: string;
}

const TIER_COLORS = {
  1: '#2d5a4a',
  2: '#4a5a2d',
  3: '#5a2d4a',
};

export function CardBack({
  tier,
  count,
  selected = false,
  onClick,
  testId,
}: CardBackProps) {
  return (
    <div
      onClick={onClick}
      className={`
        card w-32 h-40 flex flex-col items-center justify-center cursor-pointer
        ${selected ? 'selected' : ''}
      `}
      style={{ backgroundColor: TIER_COLORS[tier] }}
      data-testid={testId || `deck-tier${tier}`}
    >
      <span className="text-3xl font-display font-bold text-white/80">
        {'•'.repeat(tier)}
      </span>
      <span className="text-sm text-white/60 mt-2">
        {count} cards
      </span>
    </div>
  );
}

interface HiddenReservedCardProps {
  tier: 1 | 2 | 3;
  testId?: string;
}

export function HiddenReservedCard({ tier, testId }: HiddenReservedCardProps) {
  return (
    <div
      className="card w-20 h-24 flex items-center justify-center face-down"
      style={{ backgroundColor: TIER_COLORS[tier] }}
      data-testid={testId}
    >
      <span className="text-xl font-display text-white/60">
        {'•'.repeat(tier)}
      </span>
    </div>
  );
}
