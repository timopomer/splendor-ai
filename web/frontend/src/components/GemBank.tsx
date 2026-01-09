import type { GemCollection, GemType } from '../types/game';
import { BASE_GEMS } from '../types/game';
import { GemToken } from './GemToken';

interface GemBankProps {
  bank: GemCollection;
  selectedGems: GemType[];
  onGemClick: (gem: GemType) => void;
  disabled?: boolean;
}

export function GemBank({
  bank,
  selectedGems,
  onGemClick,
  disabled = false,
}: GemBankProps) {
  return (
    <div className="flex gap-4 items-center">
      <span className="text-sm text-gray-400 font-medium w-14">Bank</span>
      <div className="flex gap-4">
        {BASE_GEMS.map((gem) => {
          const count = bank[gem];
          const isSelected = selectedGems.includes(gem);
          const selectedCount = selectedGems.filter((g) => g === gem).length;
          
          return (
            <div key={gem} className="flex flex-col items-center gap-1">
              <GemToken
                gem={gem}
                count={count}
                size="lg"
                selected={isSelected}
                disabled={disabled || count === 0}
                onClick={() => onGemClick(gem)}
                testId={`bank-${gem}`}
              />
              {selectedCount > 0 && (
                <span className="text-xs text-highlight font-bold">
                  +{selectedCount}
                </span>
              )}
            </div>
          );
        })}
        
        {/* Gold token (not clickable) */}
        <div className="flex flex-col items-center gap-1">
          <GemToken
            gem="gold"
            count={bank.gold}
            size="lg"
            disabled={true}
            testId="bank-gold"
          />
        </div>
      </div>
    </div>
  );
}

