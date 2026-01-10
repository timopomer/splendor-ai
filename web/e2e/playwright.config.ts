import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { randomUUID } from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Generate unique backend instance ID
const BACKEND_INSTANCE_ID = randomUUID();
console.log(`🔧 Playwright Backend Instance ID: ${BACKEND_INSTANCE_ID}`);

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // Must run serially since we share backend
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker since backend is shared
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'cd ../../ && uv run --extra web --extra rl -- python -m uvicorn web.backend.main:app --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      cwd: __dirname,
      env: {
        PYTHONPATH: '../../src',
        TEST_ROOMS: process.env.TEST_ROOMS || '',
        EXPECTED_INSTANCE_ID: BACKEND_INSTANCE_ID,
      },
    },
    {
      command: 'cd ../frontend && pnpm dev',
      port: 5173,
      reuseExistingServer: !process.env.CI,
      cwd: __dirname,
    },
  ],
});
