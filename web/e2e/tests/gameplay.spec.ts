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
});
