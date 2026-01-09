import type { Card as CardType, GemCollection } from '../types/game';
import { Card, CardBack } from './Card';

interface CardRowProps {
  tier: 1 | 2 | 3;
  cards: CardType[];
  deckCount: number;
  selectedCardId: string | null;
  selectedDeckTier: number | null;
  playerTokens?: GemCollection;
  playerBonuses?: GemCollection;
  onCardClick: (card: CardType) => void;
  onDeckClick: (tier: 1 | 2 | 3) => void;
  disabled?: boolean;
}

export function CardRow({
  tier,
  cards,
  deckCount,
  selectedCardId,
  selectedDeckTier,
  playerTokens,
  playerBonuses,
  onCardClick,
  onDeckClick,
  disabled = false,
}: CardRowProps) {
  return (
    <div className="flex gap-4 items-center">
      <span className="text-sm text-gray-400 font-medium w-14">
        Tier {tier}
      </span>
      
      {/* Visible cards */}
      <div className="flex gap-3">
        {cards.map((card, idx) => (
          <Card
            key={card.id}
            card={card}
            selected={selectedCardId === card.id}
            playerTokens={playerTokens}
            playerBonuses={playerBonuses}
            onClick={disabled ? undefined : () => onCardClick(card)}
            testId={`card-tier${tier}-${idx}`}
          />
        ))}
        
        {/* Empty slots */}
        {Array.from({ length: 4 - cards.length }).map((_, idx) => (
          <div
            key={`empty-${idx}`}
            className="w-32 h-40 rounded-lg border-2 border-dashed border-gray-600 opacity-30"
          />
        ))}
      </div>
      
      {/* Deck */}
      <CardBack
        tier={tier}
        count={deckCount}
        selected={selectedDeckTier === tier}
        onClick={disabled || deckCount === 0 ? undefined : () => onDeckClick(tier)}
        testId={`deck-tier${tier}`}
      />
    </div>
  );
}
