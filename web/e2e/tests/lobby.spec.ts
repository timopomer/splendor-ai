import { test, expect } from '@playwright/test';

test.describe('Lobby', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('shows main menu with create and join buttons', async ({ page }) => {
    await expect(page.getByText('SPLENDOR')).toBeVisible();
    await expect(page.getByTestId('create-room')).toBeVisible();
    await expect(page.getByTestId('join-room-btn')).toBeVisible();
  });

  test('create room and get shareable code', async ({ page }) => {
    // Click create room
    await page.getByTestId('create-room').click();
    
    // Fill in name
    await page.getByTestId('player-name').fill('TestPlayer');
    
    // Select 2 players (default)
    await expect(page.getByTestId('num-players-2')).toBeVisible();
    
    // Create room
    await page.getByTestId('start-room').click();
    
    // Verify room code is displayed
    await expect(page.getByTestId('room-code')).toBeVisible();
    const roomCode = await page.getByTestId('room-code').textContent();
    expect(roomCode).toMatch(/^[A-Z0-9]{6}$/);
  });

  test('can select different player counts', async ({ page }) => {
    await page.getByTestId('create-room').click();
    
    // Default is 2 players
    await expect(page.getByTestId('num-players-2')).toHaveClass(/bg-highlight/);
    
    // Select 3 players
    await page.getByTestId('num-players-3').click();
    await expect(page.getByTestId('num-players-3')).toHaveClass(/bg-highlight/);
    
    // Select 4 players
    await page.getByTestId('num-players-4').click();
    await expect(page.getByTestId('num-players-4')).toHaveClass(/bg-highlight/);
  });

  test('shows validation error without name', async ({ page }) => {
    await page.getByTestId('create-room').click();
    await page.getByTestId('start-room').click();
    
    // Should show error
    await expect(page.getByText('Please enter your name')).toBeVisible();
  });

  test('can navigate to join form', async ({ page }) => {
    await page.getByTestId('join-room-btn').click();
    
    await expect(page.getByTestId('join-form')).toBeVisible();
    await expect(page.getByTestId('join-code')).toBeVisible();
    await expect(page.getByTestId('player-name')).toBeVisible();
  });

  test('shows error for invalid room code', async ({ page }) => {
    await page.getByTestId('join-room-btn').click();
    
    await page.getByTestId('player-name').fill('TestPlayer');
    await page.getByTestId('join-code').fill('INVALID');
    await page.getByTestId('join-room').click();
    
    // Should show error (room not found)
    await expect(page.getByText(/not found|error/i)).toBeVisible({ timeout: 5000 });
  });

  test('host can add bot to empty seat', async ({ page }) => {
    // Create room
    await page.getByTestId('create-room').click();
    await page.getByTestId('player-name').fill('Host');
    await page.getByTestId('start-room').click();
    
    // Wait for waiting room
    await expect(page.getByTestId('room-code')).toBeVisible();
    
    // Add bot to seat 1
    await page.getByTestId('toggle-bot-1').click();
    
    // Verify bot is shown
    await expect(page.getByTestId('seat-1')).toContainText('Bot');
  });
});

