import { useState, useMemo } from 'react';
import { useParams, useNavigate } from '@tanstack/react-router';
import {
  getStoredSession,
  clearSession,
  useGameState,
  useSubmitAction,
} from '../api/client';
import { GameBoard } from '../components/GameBoard';
import type { Card, GemType, GameAction } from '../types/game';
import { canAfford, totalTokens } from '../types/game';

export function Game() {
  const params = useParams({ from: '/game/$roomId' });
  const navigate = useNavigate();
  const session = getStoredSession();
  
  // Selection state
  const [selectedGems, setSelectedGems] = useState<GemType[]>([]);
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const [selectedDeckTier, setSelectedDeckTier] = useState<number | null>(null);
  const [selectedReservedCard, setSelectedReservedCard] = useState<Card | null>(null);
  const [returnGems, setReturnGems] = useState<GemType[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  
  // Redirect if no session
  if (!session || session.roomId !== params.roomId) {
    console.log('Redirect logic:', { session, paramsRoomId: params.roomId, match: session?.roomId === params.roomId });
    navigate({ to: '/room/$roomId', params: { roomId: params.roomId } });
    return null;
  }
  
  const { data: state, isLoading, error: queryError } = useGameState(
    session.roomId,
    session.token,
    true
  );
  
  const submitAction = useSubmitAction(session.roomId, session.token);
  
  // Clear selection helper
  const clearSelection = () => {
    setSelectedGems([]);
    setSelectedCard(null);
    setSelectedDeckTier(null);
    setSelectedReservedCard(null);
    setReturnGems([]);
    setActionError(null);
  };
  
  // Handle gem click
  const handleGemClick = (gem: GemType) => {
    if (!state?.is_your_turn) return;

    // Clear card selections when selecting gems
    setSelectedCard(null);
    setSelectedDeckTier(null);
    setSelectedReservedCard(null);
    setReturnGems([]);
    setActionError(null);

    setSelectedGems((prev) => {
      const count = prev.filter((g) => g === gem).length;
      const bank = state.bank;

      // If already selected twice, or clicking would make invalid, remove
      if (count >= 2) {
        return prev.filter((g) => g !== gem);
      }

      // If clicking same gem that's selected once
      if (count === 1) {
        // Can only take 2 same if it's our only selection and bank has 4+
        if (prev.length === 1 && bank[gem] >= 4) {
          return [...prev, gem];
        }
        // Otherwise deselect
        return prev.filter((g) => g !== gem);
      }

      // Adding new gem
      if (prev.length >= 3) return prev;

      // If we have 2 same selected, clear and start fresh
      if (prev.length === 2 && prev[0] === prev[1]) {
        return [gem];
      }

      return [...prev, gem];
    });
  };
  
  // Handle card click
  const handleCardClick = (card: Card) => {
    if (!state?.is_your_turn) return;
    
    setSelectedGems([]);
    setSelectedDeckTier(null);
    setSelectedReservedCard(null);
    setReturnGems([]);
    setActionError(null);
    
    setSelectedCard((prev) => prev?.id === card.id ? null : card);
  };
  
  // Handle deck click
  const handleDeckClick = (tier: 1 | 2 | 3) => {
    if (!state?.is_your_turn) return;
    
    setSelectedGems([]);
    setSelectedCard(null);
    setSelectedReservedCard(null);
    setReturnGems([]);
    setActionError(null);
    
    setSelectedDeckTier((prev) => prev === tier ? null : tier);
  };
  
  // Handle reserved card click
  const handleReservedClick = (card: Card) => {
    if (!state?.is_your_turn) return;
    
    setSelectedGems([]);
    setSelectedCard(null);
    setSelectedDeckTier(null);
    setReturnGems([]);
    setActionError(null);
    
    setSelectedReservedCard((prev) => prev?.id === card.id ? null : card);
  };
  
  // Validation
  const canTakeGems = (() => {
    if (selectedGems.length === 0) return false;
    if (!state) return false;
    
    const bank = state.bank;
    
    // Check all gems are available
    for (const gem of selectedGems) {
      if (bank[gem] <= 0) return false;
    }
    
    // Valid take 3 different
    const unique = new Set(selectedGems);
    if (selectedGems.length <= 3 && unique.size === selectedGems.length) {
      return true;
    }
    
    // Valid take 2 same
    if (selectedGems.length === 2 && selectedGems[0] === selectedGems[1]) {
      return bank[selectedGems[0]] >= 4;
    }
    
    return false;
  })();
  
  const canBuyCard = (() => {
    if (!state) return false;
    const player = state.players[0];
    
    if (selectedCard) {
      return canAfford(selectedCard.cost, player.tokens, player.bonuses);
    }
    if (selectedReservedCard) {
      return canAfford(selectedReservedCard.cost, player.tokens, player.bonuses);
    }
    return false;
  })();
  
  const canReserve = (() => {
    if (!state) return false;
    const player = state.players[0];
    const reservedCount = player.reserved.length;
    
    if (reservedCount >= 3) return false;
    return selectedCard !== null || selectedDeckTier !== null;
  })();

  // Calculate if we need to return gems
  const needsReturnGems = useMemo(() => {
    if (!state || !state.is_your_turn) return false;
    const player = state.players[0];
    const currentTokens = totalTokens(player.tokens);
    
    // Check for taking gems
    if (selectedGems.length > 0) {
      const tokensAfterTake = currentTokens + selectedGems.length;
      const needsReturn = tokensAfterTake > 10;
      return needsReturn;
    }
    
    // Check for reserving (might get gold)
    if ((selectedCard || selectedDeckTier) && canReserve) {
      const goldAvailable = state.bank.gold > 0;
      const tokensAfterReserve = currentTokens + (goldAvailable ? 1 : 0);
      return tokensAfterReserve > 10;
    }
    
    return false;
  }, [state, selectedGems.length, selectedCard, selectedDeckTier, canReserve]);

  const requiredReturnCount = useMemo(() => {
    if (!state || !needsReturnGems) return 0;
    const player = state.players[0];
    const currentTokens = totalTokens(player.tokens);
    
    if (selectedGems.length > 0) {
      return currentTokens + selectedGems.length - 10;
    }
    
    if ((selectedCard || selectedDeckTier) && canReserve) {
      const goldAvailable = state.bank.gold > 0;
      const tokensAfterReserve = currentTokens + (goldAvailable ? 1 : 0);
      return tokensAfterReserve - 10;
    }
    
    return 0;
  }, [state, needsReturnGems, selectedGems.length, selectedCard, selectedDeckTier, canReserve]);

  // Handle return gem click
  const handleReturnGemClick = (gem: GemType) => {
    if (!state) return;
    const player = state.players[0];

    setReturnGems((prev) => {
      const count = prev.filter((g) => g === gem).length;
      const playerCount = player.tokens[gem];
      const takingCount = selectedGems.filter((g) => g === gem).length;
      const totalAvailable = playerCount + takingCount;

      // If already selected as many as we'll have total, toggle off (remove all of this gem)
      if (count >= totalAvailable) {
        return prev.filter((g) => g !== gem);
      }

      // If clicking when already at required count, replace with this gem type
      if (prev.length >= requiredReturnCount) {
        // If we already have some of this gem type selected, add one more (replacing another gem)
        const otherGems = prev.filter((g) => g !== gem);
        if (otherGems.length < requiredReturnCount && count < totalAvailable) {
          return [...otherGems, gem];
        }
        return prev;
      }

      return [...prev, gem];
    });
  };
  
  // Action handlers
  const executeAction = (action: GameAction) => {
    setActionError(null);
    submitAction.mutate(action, {
      onSuccess: (response) => {
        if (!response.success) {
          setActionError(response.error || 'Action failed');
        } else {
          clearSelection();
        }
      },
      onError: (err) => {
        setActionError(err instanceof Error ? err.message : 'Action failed');
      },
    });
  };
  
  const handleTakeGems = () => {
    if (!canTakeGems) return;
    
    // Check if we need to return gems
    if (needsReturnGems && returnGems.length !== requiredReturnCount) {
      setActionError(`Please select ${requiredReturnCount} gem(s) to return`);
      return;
    }
    
    const unique = new Set(selectedGems);
    const returnGemsArray = needsReturnGems ? returnGems : undefined;
    
    if (selectedGems.length === 2 && selectedGems[0] === selectedGems[1]) {
      executeAction({
        type: 'take_two_same',
        gem: selectedGems[0],
        return_gems: returnGemsArray,
      });
    } else {
      executeAction({
        type: 'take_three_different',
        gems: Array.from(unique),
        return_gems: returnGemsArray,
      });
    }
  };
  
  const handleBuyCard = () => {
    if (selectedCard) {
      executeAction({
        type: 'purchase_visible',
        card_id: selectedCard.id,
      });
    } else if (selectedReservedCard) {
      executeAction({
        type: 'purchase_reserved',
        card_id: selectedReservedCard.id,
      });
    }
  };
  
  const handleReserveCard = () => {
    // Check if we need to return gems
    if (needsReturnGems && returnGems.length !== requiredReturnCount) {
      setActionError(`Please select ${requiredReturnCount} gem(s) to return`);
      return;
    }
    
    const returnGemsArray = needsReturnGems ? returnGems : undefined;
    
    if (selectedCard) {
      executeAction({
        type: 'reserve_visible',
        card_id: selectedCard.id,
        return_gems: returnGemsArray,
      });
    } else if (selectedDeckTier) {
      executeAction({
        type: 'reserve_from_deck',
        tier: selectedDeckTier as 1 | 2 | 3,
        return_gems: returnGemsArray,
      });
    }
  };
  
  const handleLeaveGame = () => {
    clearSession();
    navigate({ to: '/' });
  };
  
  // Loading/error states
  if (isLoading && !state) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-400 animate-pulse">Loading game...</div>
      </div>
    );
  }
  
  if (queryError) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-4">
        <div className="text-xl text-red-400">Error loading game</div>
        <p className="text-gray-400">{queryError.message}</p>
        <button onClick={handleLeaveGame} className="btn btn-primary">
          Return to Lobby
        </button>
      </div>
    );
  }
  
  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-400">Game not found</div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen">
      <GameBoard
        state={state}
        selectedGems={selectedGems}
        selectedCard={selectedCard}
        selectedDeckTier={selectedDeckTier}
        selectedReservedCard={selectedReservedCard}
        returnGems={returnGems}
        needsReturnGems={needsReturnGems}
        requiredReturnCount={requiredReturnCount}
        onGemClick={handleGemClick}
        onCardClick={handleCardClick}
        onDeckClick={handleDeckClick}
        onReservedClick={handleReservedClick}
        onReturnGemClick={handleReturnGemClick}
        onTakeGems={handleTakeGems}
        onBuyCard={handleBuyCard}
        onReserveCard={handleReserveCard}
        onCancel={clearSelection}
        canTakeGems={canTakeGems}
        canBuyCard={canBuyCard}
        canReserve={canReserve}
        loading={submitAction.isPending}
        error={actionError}
      />
      
      {/* Leave game button */}
      <div className="fixed top-4 right-4">
        <button
          onClick={handleLeaveGame}
          className="btn btn-secondary text-sm"
          data-testid="leave-game"
        >
          Leave Game
        </button>
      </div>
    </div>
  );
}

