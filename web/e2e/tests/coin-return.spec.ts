import { test as base, expect } from '../fixtures/backend';
import { Page } from '@playwright/test';

// Define test rooms configuration inline
const TEST_ROOMS_CONFIG = {
  rooms: [
    {
      room_id: 'TEST8',
      player_name: 'TestPlayer',
      player_emoji: '🧪',
      player_tokens: 8,
      token: 'test-token-8coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    },
    {
      room_id: 'TEST9',
      player_name: 'TestPlayer',
      player_emoji: '🧪',
      player_tokens: 9,
      token: 'test-token-9coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    },
    {
      room_id: 'TEST10',
      player_name: 'TestPlayer',
      player_emoji: '🧪',
      player_tokens: 10,
      token: 'test-token-10coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    },
  ],
};

// Extend the test with TEST_ROOMS configuration
const test = base.extend({
  // This fixture runs before each worker to set up the TEST_ROOMS env var
  testRooms: [async ({}, use) => {
    // Set environment variable for this test suite - the backend fixture will pick it up
    process.env.TEST_ROOMS = JSON.stringify(TEST_ROOMS_CONFIG);
    await use(undefined);
    // Clean up after test
    delete process.env.TEST_ROOMS;
  }, { scope: 'worker', auto: true }],
});

const KNOWN_TOKENS: Record<string, string> = {
  TEST8: 'test-token-8coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  TEST9: 'test-token-9coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  TEST10: 'test-token-10coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
};

interface TestGameSetup {
  roomId: string;
  token: string;
  playerTokens: number;
}

/**
 * Get test game setup for a specific token count
 */
function getTestGame(playerTokens: number): TestGameSetup {
  const roomId = `TEST${playerTokens}`;
  const token = KNOWN_TOKENS[roomId];

  if (!token) {
    throw new Error(`No test room configured for ${playerTokens} tokens`);
  }

  return { roomId, token, playerTokens };
}

/**
 * Navigate to test game
 */
async function navigateToTestGame(page: Page, setup: TestGameSetup) {
  // Listen for console messages
  page.on('console', msg => console.log(`BROWSER: ${msg.text()}`));

  // First navigate to a page to set localStorage
  await page.goto('/');

  // Store session in localStorage
  await page.evaluate(
    ({ roomId, token }) => {
      console.log(`Setting session: roomId=${roomId}, token=${token.substring(0, 10)}...`);
      localStorage.setItem(
        'splendor_session',
        JSON.stringify({ roomId, token, seat: 0 })
      );
    },
    { roomId: setup.roomId, token: setup.token }
  );

  // Navigate to game page
  await page.goto(`/game/${setup.roomId}`);

  // Debug: wait a moment and check current URL and localStorage
  await page.waitForTimeout(2000);
  const currentUrl = page.url();
  const storedSession = await page.evaluate(() => {
    const stored = localStorage.getItem('splendor_session');
    return stored ? JSON.parse(stored) : null;
  });
  console.log(`Current URL: ${currentUrl}`);
  console.log(`Stored session: ${JSON.stringify(storedSession)}`);

  // Wait for game board to load
  await expect(page.getByTestId('game-board')).toBeVisible({ timeout: 15000 });

  // Wait for our turn
  await expect(page.getByTestId('current-turn')).toContainText('Your turn', {
    timeout: 15000,
  });
}

/**
 * Get current token count from UI
 */
async function getTokenCount(page: Page): Promise<number> {
  const playerPanel = page.getByTestId('player-self');
  const tokenText = await playerPanel.locator('text=/\\d+\\/10/').textContent();
  const match = tokenText?.match(/(\d+)\/10/);
  return match ? parseInt(match[1]) : 0;
}

/**
 * Select gems from bank
 */
async function selectGems(
  page: Page,
  gems: string[]
): Promise<{ selected: number; failed: string[] }> {
  let selected = 0;
  const failed: string[] = [];

  for (const gem of gems) {
    try {
      const bankGem = page.getByTestId(`bank-${gem}`);
      if (await bankGem.isVisible({ timeout: 500 })) {
        await bankGem.click();
        selected++;
        await page.waitForTimeout(150);
      } else {
        failed.push(gem);
      }
    } catch {
      failed.push(gem);
    }
  }

  return { selected, failed };
}

/**
 * Click gems to return from the return UI
 */
async function selectGemsToReturn(
  page: Page,
  gems: string[],
  requiredCount: number
): Promise<number> {
  let returnedCount = 0;

  for (const gem of gems) {
    if (returnedCount >= requiredCount) break;

    try {
      const returnBtn =
        gem === 'gold'
          ? page.getByTestId('return-gem-gold')
          : page.getByTestId(`return-gem-${gem}`);

      if (await returnBtn.isEnabled({ timeout: 1000 })) {
        await returnBtn.click();
        returnedCount++;
        await page.waitForTimeout(200);

        // Verify count updated
        const countText = await page
          .getByTestId('return-gems-count')
          .textContent();
        expect(countText).toContain(`${returnedCount} / ${requiredCount}`);
      }
    } catch {
      // Button not available or disabled
    }
  }

  return returnedCount;
}

test.describe('Coin Return Flow', () => {
  test('8 tokens → select 3 gems → return 1 (8+3=11)', async ({ page }) => {
    // Get test game with 8 tokens
    const setup = getTestGame(8);
    await navigateToTestGame(page, setup);

    // Verify starting tokens
    const startTokens = await getTokenCount(page);
    expect(startTokens).toBe(8);

    // Select 3 different gems
    const gemsToTake = ['diamond', 'ruby', 'emerald'];
    const { selected } = await selectGems(page, gemsToTake);
    expect(selected).toBe(3);

    // Verify selection shown
    await expect(page.getByTestId('selected-gems')).toContainText('diamond');
    await expect(page.getByTestId('selected-gems')).toContainText('ruby');
    await expect(page.getByTestId('selected-gems')).toContainText('emerald');

    // Wait for state to update
    await page.waitForTimeout(500);

    // Verify return gems UI appears (8 + 3 = 11 > 10)
    await expect(page.getByTestId('return-gems-ui')).toBeVisible({
      timeout: 2000,
    });
    await expect(page.getByTestId('return-gems-ui')).toContainText(
      'more than 10 coins'
    );
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 1');

    // Select 1 gem to return
    const returnedCount = await selectGemsToReturn(
      page,
      ['diamond', 'ruby', 'emerald', 'sapphire', 'onyx'],
      1
    );
    expect(returnedCount).toBe(1);

    // Verify we can submit
    await expect(page.getByTestId('take-gems-btn')).toBeEnabled();

    // Submit action
    await page.getByTestId('take-gems-btn').click();

    // Wait for turn to advance
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      expect(turnText).not.toContain('Your turn');
    }).toPass({ timeout: 10000 });

    // Verify return gems UI is gone
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();
  });

  test('9 tokens → select 3 gems → return 2 (9+3=12)', async ({ page }) => {
    // Get test game with 9 tokens
    const setup = getTestGame(9);
    await navigateToTestGame(page, setup);

    // Verify starting tokens
    const startTokens = await getTokenCount(page);
    expect(startTokens).toBe(9);

    // Select 3 different gems
    const gemsToTake = ['diamond', 'ruby', 'emerald'];
    const { selected } = await selectGems(page, gemsToTake);
    expect(selected).toBe(3);

    // Wait for state to update
    await page.waitForTimeout(500);

    // Verify return gems UI appears (9 + 3 = 12 > 10)
    await expect(page.getByTestId('return-gems-ui')).toBeVisible({
      timeout: 2000,
    });
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 2');

    // Select 2 gems to return
    const returnedCount = await selectGemsToReturn(
      page,
      ['diamond', 'ruby', 'emerald', 'sapphire', 'onyx'],
      2
    );
    expect(returnedCount).toBe(2);

    // Verify we can submit
    await expect(page.getByTestId('take-gems-btn')).toBeEnabled();

    // Submit action
    await page.getByTestId('take-gems-btn').click();

    // Wait for turn to advance
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      expect(turnText).not.toContain('Your turn');
    }).toPass({ timeout: 10000 });

    // Verify return gems UI is gone
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();
  });

  test('10 tokens → select 3 gems → return 3 (10+3=13)', async ({ page }) => {
    // Get test game with 10 tokens
    const setup = getTestGame(10);
    await navigateToTestGame(page, setup);

    // Verify starting tokens
    const startTokens = await getTokenCount(page);
    expect(startTokens).toBe(10);

    // Select 3 different gems
    const gemsToTake = ['diamond', 'ruby', 'emerald'];
    const { selected } = await selectGems(page, gemsToTake);
    expect(selected).toBe(3);

    // Wait for state to update
    await page.waitForTimeout(500);

    // Verify return gems UI appears (10 + 3 = 13 > 10)
    await expect(page.getByTestId('return-gems-ui')).toBeVisible({
      timeout: 2000,
    });
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 3');

    // Select 3 gems to return
    const returnedCount = await selectGemsToReturn(
      page,
      ['diamond', 'ruby', 'emerald', 'sapphire', 'onyx'],
      3
    );
    expect(returnedCount).toBe(3);

    // Verify we can submit
    await expect(page.getByTestId('take-gems-btn')).toBeEnabled();

    // Submit action
    await page.getByTestId('take-gems-btn').click();

    // Wait for turn to advance
    await expect(async () => {
      const turnText = await page.getByTestId('current-turn').textContent();
      expect(turnText).not.toContain('Your turn');
    }).toPass({ timeout: 10000 });

    // Verify return gems UI is gone
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();
  });

  test('can cancel and reselect different gems', async ({ page }) => {
    // Get test game with 9 tokens
    const setup = getTestGame(9);
    await navigateToTestGame(page, setup);

    // Select 3 gems
    await selectGems(page, ['diamond', 'ruby', 'emerald']);
    await page.waitForTimeout(500);

    // Return UI should appear
    await expect(page.getByTestId('return-gems-ui')).toBeVisible();

    // Click Cancel
    await page.getByTestId('cancel-btn').click();

    // Return UI should be gone
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();

    // Select different gems
    await selectGems(page, ['sapphire', 'onyx']);
    await page.waitForTimeout(500);

    // No return UI should appear (9 + 2 = 11, so only need to return 1)
    await expect(page.getByTestId('return-gems-ui')).toBeVisible();
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 1');
  });

  test('warning message appears when over limit', async ({ page }) => {
    // Get test game with 10 tokens
    const setup = getTestGame(10);
    await navigateToTestGame(page, setup);

    // Select 3 gems
    await selectGems(page, ['diamond', 'ruby', 'emerald']);
    await page.waitForTimeout(500);

    // Verify warning message appears
    await expect(page.locator('text=Too many coins!')).toBeVisible();
    await expect(
      page.locator('text=/Select gems to return below/i')
    ).toBeVisible();
  });
});
