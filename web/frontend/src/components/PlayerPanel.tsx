import type { Player, Card as CardType, ReservedCard, GemType } from '../types/game';
import { BASE_GEMS, ALL_GEMS, GEM_COLORS, GEM_TEXT_COLORS, isHiddenCard, totalTokens } from '../types/game';
import { Card, HiddenReservedCard } from './Card';
import { Noble } from './Noble';

interface PlayerPanelProps {
  player: Player;
  isCurrentTurn: boolean;
  isSelf: boolean;
  selectedReservedId: string | null;
  onReservedClick?: (card: CardType) => void;
  testId?: string;
}

export function PlayerPanel({
  player,
  isCurrentTurn,
  isSelf,
  selectedReservedId,
  onReservedClick,
  testId,
}: PlayerPanelProps) {
  return (
    <div
      className={`
        rounded-xl p-4 transition-all
        ${isSelf ? 'bg-panel border-2 border-highlight/30' : 'bg-board/50'}
        ${isCurrentTurn ? 'your-turn' : ''}
      `}
      data-testid={testId || (isSelf ? 'player-self' : `player-${player.id}`)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
              isSelf ? 'bg-highlight text-board' : 'bg-gray-600 text-white'
            }`}
          >
            {player.id + 1}
          </div>
          <span className="font-medium">
            {isSelf ? 'You' : `Player ${player.id + 1}`}
          </span>
          {isCurrentTurn && (
            <span className="text-xs bg-highlight/20 text-highlight px-2 py-0.5 rounded-full">
              Current Turn
            </span>
          )}
        </div>
        <div className="text-2xl font-display font-bold text-highlight">
          {player.points} pts
        </div>
      </div>

      {/* Tokens */}
      <div className="flex gap-2 mb-3">
        {ALL_GEMS.map((gem) => {
          const count = player.tokens[gem];
          if (gem === 'gold' && count === 0) return null;
          
          return (
            <div
              key={gem}
              className="flex items-center gap-1"
              data-testid={`player-${gem}`}
            >
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                style={{
                  backgroundColor: GEM_COLORS[gem],
                  color: GEM_TEXT_COLORS[gem],
                }}
              >
                {count}
              </div>
            </div>
          );
        })}
        <span className="text-xs text-gray-400 ml-1">
          ({totalTokens(player.tokens)}/10)
        </span>
      </div>

      {/* Bonuses */}
      <div className="flex gap-2 mb-3">
        <span className="text-xs text-gray-400">Bonuses:</span>
        {BASE_GEMS.map((gem) => {
          const count = player.bonuses[gem];
          if (count === 0) return null;
          
          return (
            <div
              key={gem}
              className="flex items-center gap-1"
            >
              <div
                className="w-5 h-5 rounded flex items-center justify-center text-xs font-bold"
                style={{
                  backgroundColor: GEM_COLORS[gem],
                  color: GEM_TEXT_COLORS[gem],
                }}
              >
                {count}
              </div>
            </div>
          );
        })}
        <span className="text-xs text-gray-400">
          ({player.card_count} cards)
        </span>
      </div>

      {/* Reserved cards */}
      {player.reserved.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-400 block mb-1">
            Reserved ({player.reserved.length}/3):
          </span>
          <div className="flex gap-2" data-testid="reserved-cards">
            {player.reserved.map((card, idx) => {
              if (isHiddenCard(card)) {
                return (
                  <HiddenReservedCard
                    key={idx}
                    tier={card.tier}
                    testId={`opponent-reserved-${idx}`}
                  />
                );
              }
              
              return (
                <div
                  key={card.id}
                  onClick={isSelf && onReservedClick ? () => onReservedClick(card) : undefined}
                  className={`cursor-pointer ${
                    selectedReservedId === card.id ? 'ring-2 ring-highlight' : ''
                  }`}
                  data-testid={`my-reserved-${idx}`}
                >
                  <Card
                    card={card}
                    selected={selectedReservedId === card.id}
                    playerTokens={player.tokens}
                    playerBonuses={player.bonuses}
                  />
                </div>
              );
            })}
          </div>
          {!isSelf && (
            <span
              className="text-xs text-gray-500"
              data-testid="opponent-reserved-count"
            >
              {player.reserved.length} reserved
            </span>
          )}
        </div>
      )}

      {/* Nobles */}
      {player.nobles.length > 0 && (
        <div>
          <span className="text-xs text-gray-400 block mb-1">Nobles:</span>
          <div className="flex gap-2">
            {player.nobles.map((noble) => (
              <Noble key={noble.id} noble={noble} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

