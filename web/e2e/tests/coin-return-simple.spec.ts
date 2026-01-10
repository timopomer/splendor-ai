import { test as base, expect, Page } from '@playwright/test';

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

const KNOWN_TOKENS = {
  TEST8: 'test-token-8coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  TEST9: 'test-token-9coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  TEST10: 'test-token-10coins-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
};

// Extend the base test with environment setup
const test = base.extend({
  // This fixture runs before each test to set up the TEST_ROOMS env var
  testRooms: [async ({}, use, testInfo) => {
    // Set environment variable for this test suite
    process.env.TEST_ROOMS = JSON.stringify(TEST_ROOMS_CONFIG);
    await use(undefined);
    // Clean up after test
    delete process.env.TEST_ROOMS;
  }, { scope: 'worker', auto: true }],
});

async function verifyBackendInstance(): Promise<string> {
  const response = await fetch('http://localhost:8000/');
  const data = await response.json();
  console.log(`Backend instance: ${data.instance_id}`);
  return data.instance_id;
}

async function navigateToGame(page: Page, roomId: keyof typeof KNOWN_TOKENS) {
  const token = KNOWN_TOKENS[roomId];

  // Verify we're connected to the right backend instance
  const instanceId = await verifyBackendInstance();
  console.log(`Connected to backend instance: ${instanceId}`);

  // Navigate and set session
  await page.goto('/');
  await page.evaluate(
    ({ roomId, token }) => {
      localStorage.setItem(
        'splendor_session',
        JSON.stringify({ roomId, token, seat: 0 })
      );
    },
    { roomId, token }
  );

  // Go to game page
  await page.goto(`/game/${roomId}`);
  await expect(page.getByTestId('game-board')).toBeVisible({ timeout: 10000 });
}

test.describe('Coin Return', () => {
  test('8→11: select 3, return 1', async ({ page }) => {
    await navigateToGame(page, 'TEST8');

    // Select 3 gems
    await page.getByTestId('bank-diamond').click();
    await page.getByTestId('bank-ruby').click();
    await page.getByTestId('bank-emerald').click();

    // Return UI should appear
    await expect(page.getByTestId('return-gems-ui')).toBeVisible();
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 1');

    // Select 1 to return
    await page.getByTestId('return-gem-diamond').click();
    await expect(page.getByTestId('return-gems-count')).toContainText('1 / 1');

    // Submit
    await page.getByTestId('take-gems-btn').click();
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();
  });

  test('9→12: select 3, return 2', async ({ page }) => {
    await navigateToGame(page, 'TEST9');

    await page.getByTestId('bank-diamond').click();
    await page.getByTestId('bank-ruby').click();
    await page.getByTestId('bank-emerald').click();

    await expect(page.getByTestId('return-gems-ui')).toBeVisible();
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 2');

    await page.getByTestId('return-gem-diamond').click();
    await page.getByTestId('return-gem-ruby').click();
    await expect(page.getByTestId('return-gems-count')).toContainText('2 / 2');

    await page.getByTestId('take-gems-btn').click();
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();
  });

  test('10→13: select 3, return 3', async ({ page }) => {
    await navigateToGame(page, 'TEST10');

    await page.getByTestId('bank-diamond').click();
    await page.getByTestId('bank-ruby').click();
    await page.getByTestId('bank-emerald').click();

    await expect(page.getByTestId('return-gems-ui')).toBeVisible();
    await expect(page.getByTestId('return-gems-count')).toContainText('0 / 3');

    await page.getByTestId('return-gem-diamond').click();
    await page.getByTestId('return-gem-ruby').click();
    await page.getByTestId('return-gem-emerald').click();
    await expect(page.getByTestId('return-gems-count')).toContainText('3 / 3');

    await page.getByTestId('take-gems-btn').click();
    await expect(page.getByTestId('return-gems-ui')).not.toBeVisible();
  });
});
