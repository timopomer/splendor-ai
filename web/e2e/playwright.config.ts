import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
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
