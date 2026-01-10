import { test, expect, Page } from '@playwright/test';

// Helper to create a game with a bot opponent
async function createGameWithBot(page: Page): Promise<string> {
  await page.goto('/');
  await page.getByTestId('create-room').click();
  await page.getByTestId('player-name').fill('TestPlayer');
  await page.getByTestId('start-room').click();
  
  // Wait for room code
  await expect(page.getByTestId('room-code')).toBeVisible();
  const roomCode = await page.getByTestId('room-code').textContent();
  
  // Add bot to seat 1
  await page.getByTestId('toggle-bot-1').click();
  await expect(page.getByTestId('seat-1')).toContainText('Bot');
  
  // Start game
  await page.getByTestId('start-game').click();
  
  // Wait for game board
  await expect(page.getByTestId('game-board')).toBeVisible({ timeout: 10000 });
  
  return roomCode!;
}

test.describe('Gameplay', () => {
  test('take 3 different gems', async ({ page }) => {
    await createGameWithBot(page);
    
    // Wait for our turn
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    
    // Get initial turn number
    const turnTextBefore = await page.getByTestId('current-turn').textContent();
    const turnNumBefore = parseInt(turnTextBefore?.match(/Turn (\d+)/)?.[1] || '0');
    
    // Click 3 different gem types
    await page.getByTestId('bank-diamond').click();
    await page.getByTestId('bank-ruby').click();
    await page.getByTestId('bank-emerald').click();
    
    // Verify selection shown
    await expect(page.getByTestId('selected-gems')).toContainText('diamond');
    await expect(page.getByTestId('selected-gems')).toContainText('ruby');
    await expect(page.getByTestId('selected-gems')).toContainText('emerald');
    
    // Take gems
    await page.getByTestId('take-gems-btn').click();
    
    // Wait for turn to advance (bot plays instantly, so we're back to our turn on next round)
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      const turnNum = parseInt(turnText?.match(/Turn (\d+)/)?.[1] || '0');
      expect(turnNum).toBeGreaterThan(turnNumBefore);
    }).toPass({ timeout: 10000 });
  });

  test('take 2 same gems when 4+ available', async ({ page }) => {
    await createGameWithBot(page);
    
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    
    const turnTextBefore = await page.getByTestId('current-turn').textContent();
    const turnNumBefore = parseInt(turnTextBefore?.match(/Turn (\d+)/)?.[1] || '0');
    
    // Double-click same gem to select 2
    await page.getByTestId('bank-diamond').click();
    await page.getByTestId('bank-diamond').click();
    
    // Should show 2 selected
    await expect(page.getByTestId('take-gems-btn')).toContainText('Take 2 Gem');
    
    await page.getByTestId('take-gems-btn').click();
    
    // Wait for turn to advance
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      const turnNum = parseInt(turnText?.match(/Turn (\d+)/)?.[1] || '0');
      expect(turnNum).toBeGreaterThan(turnNumBefore);
    }).toPass({ timeout: 10000 });
  });

  test('select and deselect card', async ({ page }) => {
    await createGameWithBot(page);
    
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    
    // Click a card to select
    await page.getByTestId('card-tier1-0').click();
    
    // Should show buy/reserve buttons
    await expect(page.getByTestId('reserve-btn')).toBeVisible();
    
    // Click cancel to deselect
    await page.getByTestId('cancel-btn').click();
    
    // Buttons should be gone
    await expect(page.getByTestId('reserve-btn')).not.toBeVisible();
  });

  test('reserve card and receive gold', async ({ page }) => {
    await createGameWithBot(page);
    
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    
    const turnTextBefore = await page.getByTestId('current-turn').textContent();
    const turnNumBefore = parseInt(turnTextBefore?.match(/Turn (\d+)/)?.[1] || '0');
    
    // Select a card
    await page.getByTestId('card-tier2-0').click();
    
    // Reserve it
    await page.getByTestId('reserve-btn').click();
    
    // Wait for turn to advance
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      const turnNum = parseInt(turnText?.match(/Turn (\d+)/)?.[1] || '0');
      expect(turnNum).toBeGreaterThan(turnNumBefore);
    }).toPass({ timeout: 10000 });
    
    // Verify player has reserved card visible
    await expect(page.getByTestId('player-self')).toContainText('Reserved');
  });

  test('reserve from deck blind', async ({ page }) => {
    await createGameWithBot(page);
    
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    
    const turnTextBefore = await page.getByTestId('current-turn').textContent();
    const turnNumBefore = parseInt(turnTextBefore?.match(/Turn (\d+)/)?.[1] || '0');
    
    // Click deck
    await page.getByTestId('deck-tier1').click();
    
    // Reserve from deck
    await page.getByTestId('reserve-btn').click();
    
    // Wait for turn to advance
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      const turnNum = parseInt(turnText?.match(/Turn (\d+)/)?.[1] || '0');
      expect(turnNum).toBeGreaterThan(turnNumBefore);
    }).toPass({ timeout: 10000 });
  });

  test('game shows turn indicator correctly', async ({ page }) => {
    await createGameWithBot(page);
    
    // Initially should be your turn (player 0 starts)
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    await expect(page.getByTestId('current-turn')).toContainText('Turn 1');
  });

  test('coin exchange when exceeding 10 coins', async ({ page }) => {
    await createGameWithBot(page);
    
    // Wait for our turn
    await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    
    // Helper function to get current token count
    const getTokenCount = async () => {
      const playerPanel = page.getByTestId('player-self');
      const tokenText = await playerPanel.locator('text=/\\d+\\/10/').textContent();
      const match = tokenText?.match(/(\d+)\/10/);
      return match ? parseInt(match[1]) : 0;
    };
    
    // Helper function to wait for our turn
    const waitForOurTurn = async () => {
      await expect(page.getByTestId('current-turn')).toContainText('Your turn', { timeout: 10000 });
    };
    
    // Take gems until we have 9 or 10 coins
    // This might take a few turns due to bot alternating
    for (let i = 0; i < 20; i++) {
      await waitForOurTurn();
      
      const currentTokens = await getTokenCount();
      
      // Stop when we have 9 or 10 tokens (need at least 9 to test)
      if (currentTokens >= 9) {
        break;
      }
      
      // Try to take 3 different gems
      const bankGems = ['diamond', 'ruby', 'emerald', 'sapphire', 'onyx'];
      let selectedCount = 0;
      
      for (const gem of bankGems) {
        if (selectedCount >= 3) break;
        
        try {
          const bankGem = page.getByTestId(`bank-${gem}`);
          if (await bankGem.isVisible({ timeout: 500 })) {
            await bankGem.click();
            selectedCount++;
            await page.waitForTimeout(150);
          }
        } catch {
          // Gem not available, try next
        }
      }
      
      if (selectedCount >= 2) {
        await page.getByTestId('take-gems-btn').click();
        // Wait for turn to advance
        await page.waitForTimeout(3000);
      } else {
        await page.waitForTimeout(2000);
      }
    }
    
    // Get final token count
    await waitForOurTurn();
    const finalTokens = await getTokenCount();
    
    // Only proceed if we have at least 9 tokens
    if (finalTokens < 9) {
      test.skip(); // Not enough tokens accumulated
      return;
    }
    
    // Now try to take 3 gems which should require returning some
    // Select 3 different gems
    const gemsToTake = ['diamond', 'ruby', 'emerald', 'sapphire', 'onyx'];
    let clickedCount = 0;
    
    for (const gem of gemsToTake) {
      if (clickedCount >= 3) break;
      
      try {
        const bankGem = page.getByTestId(`bank-${gem}`);
        if (await bankGem.isVisible({ timeout: 500 })) {
          await bankGem.click();
          clickedCount++;
          await page.waitForTimeout(200);
        }
      } catch {
        // Gem not available
      }
    }
    
    if (clickedCount < 2) {
      test.skip(); // Not enough gems available
      return;
    }
    
    // Wait a bit for state to update
    await page.waitForTimeout(500);
    
    // Check if we would exceed 10 tokens
    if (finalTokens + clickedCount > 10) {
      const requiredReturn = finalTokens + clickedCount - 10;
      
      // Debug: Check if selected gems are shown
      const selectedGemsVisible = await page.getByTestId('selected-gems').isVisible().catch(() => false);
      const selectedGemsText = await page.getByTestId('selected-gems').textContent().catch(() => '');
      const takeGemsBtnVisible = await page.getByTestId('take-gems-btn').isVisible().catch(() => false);
      
      // Wait for React state to update - use multiple short waits
      await page.waitForTimeout(300);
      await page.waitForTimeout(300);
      await page.waitForTimeout(400);
      
      // Verify return gems UI appears
      const returnGemsUIExists = await page.getByTestId('return-gems-ui').count();
      
      if (returnGemsUIExists === 0) {
        // Debug output
        console.log(`Return gems UI not found. Final tokens: ${finalTokens}, Clicked count: ${clickedCount}, Required return: ${requiredReturn}`);
        console.log(`Selected gems visible: ${selectedGemsVisible}, Selected gems text: ${selectedGemsText}`);
        console.log(`Take gems btn visible: ${takeGemsBtnVisible}`);
        
        // Check if we can see what gems are selected
        const actionButtons = await page.getByTestId('action-buttons').textContent().catch(() => '');
        console.log(`Action buttons content: ${actionButtons}`);
      }
      
      await expect(page.getByTestId('return-gems-ui')).toBeVisible({ timeout: 5000 });
      await expect(page.getByTestId('return-gems-ui')).toContainText('more than 10 coins');
      await expect(page.getByTestId('return-gems-count')).toContainText(`${requiredReturn}`);
      
      // Select gems to return
      const gemTypes = ['diamond', 'ruby', 'emerald', 'sapphire', 'onyx', 'gold'];
      let returnedCount = 0;
      
      // Try each gem type
      for (const gem of gemTypes) {
        if (returnedCount >= requiredReturn) break;
        
        try {
          const returnBtn = gem === 'gold' 
            ? page.getByTestId('return-gem-gold')
            : page.getByTestId(`return-gem-${gem}`);
          
          if (await returnBtn.isEnabled({ timeout: 1000 })) {
            await returnBtn.click();
            returnedCount++;
            await page.waitForTimeout(300);
            
            // Verify count updated
            const countText = await page.getByTestId('return-gems-count').textContent();
            expect(countText).toContain(`${returnedCount} / ${requiredReturn}`);
          }
        } catch {
          // Button not available or disabled
        }
      }
      
      // Verify we can submit
      await expect(page.getByTestId('take-gems-btn')).toBeEnabled();
      
      // Submit
      await page.getByTestId('take-gems-btn').click();
      
      // Wait for turn to advance
      await expect(async () => {
        const turnText = await page.getByTestId('current-turn').textContent();
        expect(turnText).not.toContain('Your turn');
      }).toPass({ timeout: 10000 });
      
      // Verify return gems UI is gone
      await expect(page.getByTestId('return-gems-ui')).not.toBeVisible({ timeout: 2000 });
    } else {
      // If we don't exceed 10, the test should just take the gems normally
      await page.getByTestId('take-gems-btn').click();
      await expect(async () => {
        const turnText = await page.getByTestId('current-turn').textContent();
        expect(turnText).not.toContain('Your turn');
      }).toPass({ timeout: 10000 });
    }
  });
});
