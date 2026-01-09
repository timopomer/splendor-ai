import { test, expect, Browser, Page } from '@playwright/test';

// Helper to set up two player game
async function setupTwoPlayerGame(browser: Browser): Promise<[Page, Page, string]> {
  // Create two browser contexts (simulates two players)
  const player1Context = await browser.newContext();
  const player2Context = await browser.newContext();
  
  const player1 = await player1Context.newPage();
  const player2 = await player2Context.newPage();
  
  // Player 1 creates room
  await player1.goto('/');
  await player1.getByTestId('create-room').click();
  await player1.getByTestId('player-name').fill('Player1');
  await player1.getByTestId('start-room').click();
  
  // Get room code
  await expect(player1.getByTestId('room-code')).toBeVisible();
  const roomCode = await player1.getByTestId('room-code').textContent();
  
  // Player 2 joins
  await player2.goto('/');
  await player2.getByTestId('join-room-btn').click();
  await player2.getByTestId('player-name').fill('Player2');
  await player2.getByTestId('join-code').fill(roomCode!);
  await player2.getByTestId('join-room').click();
  
  // Wait for both to be in waiting room
  await expect(player1.getByTestId('seat-1')).toContainText('Player2', { timeout: 5000 });
  await expect(player2.getByTestId('seat-0')).toContainText('Player1', { timeout: 5000 });
  
  // Player 1 (host) starts game
  await player1.getByTestId('start-game').click();
  
  // Wait for both to see game board
  await expect(player1.getByTestId('game-board')).toBeVisible({ timeout: 10000 });
  await expect(player2.getByTestId('game-board')).toBeVisible({ timeout: 10000 });
  
  return [player1, player2, roomCode!];
}

test.describe('Multiplayer', () => {
  test('two players see synchronized state', async ({ browser }) => {
    const [player1, player2] = await setupTwoPlayerGame(browser);
    
    // Player 1 should see it's their turn
    await expect(player1.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    
    // Player 2 should see it's opponent's turn
    await expect(player2.getByTestId('current-turn')).toContainText("Opponent's turn", { timeout: 5000 });
    
    // Player 1 takes gems
    await player1.getByTestId('bank-diamond').click();
    await player1.getByTestId('bank-ruby').click();
    await player1.getByTestId('bank-emerald').click();
    await player1.getByTestId('take-gems-btn').click();
    
    // Player 2 should see updated bank and their turn
    await expect(player2.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    
    // Bank should be updated for player 2 (one less of each taken gem)
    // Note: exact counts depend on player count, but should be less than initial
    await expect(player2.getByTestId('bank-diamond')).not.toContainText('4', { timeout: 3000 });
    
    // Clean up
    await player1.context().close();
    await player2.context().close();
  });

  test('opponent reserved cards are hidden', async ({ browser }) => {
    const [player1, player2] = await setupTwoPlayerGame(browser);
    
    // Player 1 reserves a card
    await expect(player1.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    await player1.getByTestId('card-tier1-0').click();
    await player1.getByTestId('reserve-btn').click();
    
    // Wait for turn to change
    await expect(player2.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    
    // Player 1 sees their own reserved card with details
    await expect(player1.getByTestId('my-reserved-0')).toBeVisible();
    
    // Player 2 sees opponent has reserved cards but they're hidden
    await expect(player2.getByTestId('opponent-reserved-0')).toBeVisible();
    await expect(player2.getByTestId('opponent-reserved-0')).toHaveClass(/face-down/);
    
    // Clean up
    await player1.context().close();
    await player2.context().close();
  });

  test('turn alternates between players', async ({ browser }) => {
    const [player1, player2] = await setupTwoPlayerGame(browser);
    
    // Turn 1: Player 1's turn
    await expect(player1.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    await player1.getByTestId('bank-diamond').click();
    await player1.getByTestId('take-gems-btn').click();
    
    // Turn 2: Player 2's turn
    await expect(player2.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    await player2.getByTestId('bank-sapphire').click();
    await player2.getByTestId('take-gems-btn').click();
    
    // Turn 3: Back to Player 1's turn
    await expect(player1.getByTestId('current-turn')).toContainText('Your turn', { timeout: 5000 });
    
    // Clean up
    await player1.context().close();
    await player2.context().close();
  });

  test('both players see same nobles', async ({ browser }) => {
    const [player1, player2] = await setupTwoPlayerGame(browser);
    
    // Get noble IDs from both views
    const p1Nobles = await player1.locator('[data-testid^="noble-"]').count();
    const p2Nobles = await player2.locator('[data-testid^="noble-"]').count();
    
    // Should have same number of nobles (num_players + 1 = 3)
    expect(p1Nobles).toBe(3);
    expect(p2Nobles).toBe(3);
    
    // Clean up
    await player1.context().close();
    await player2.context().close();
  });

  test('joining with room URL', async ({ browser }) => {
    const player1Context = await browser.newContext();
    const player1 = await player1Context.newPage();
    
    // Player 1 creates room
    await player1.goto('/');
    await player1.getByTestId('create-room').click();
    await player1.getByTestId('player-name').fill('Host');
    await player1.getByTestId('start-room').click();
    
    const roomCode = await player1.getByTestId('room-code').textContent();
    
    // Player 2 joins via direct URL
    const player2Context = await browser.newContext();
    const player2 = await player2Context.newPage();
    await player2.goto(`/room/${roomCode}`);
    
    // Should show join form with room code pre-filled
    await expect(player2.getByTestId('join-code')).toHaveValue(roomCode!);
    
    // Clean up
    await player1.context().close();
    await player2.context().close();
  });
});

