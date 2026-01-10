import { test as base, Page } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import { randomUUID } from 'crypto';
import * as net from 'net';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Find an available port in the given range
 */
async function findAvailablePort(startPort: number, endPort: number): Promise<number> {
  for (let port = startPort; port <= endPort; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available ports in range ${startPort}-${endPort}`);
}

/**
 * Check if a port is available
 */
function isPortAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close();
      resolve(true);
    });
    server.listen(port);
  });
}

/**
 * Wait for a port to be listening
 */
async function waitForPort(port: number, timeout = 30000): Promise<void> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(`http://localhost:${port}/`);
      if (response.ok) {
        return;
      }
    } catch {
      // Port not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Port ${port} did not become available within ${timeout}ms`);
}

export interface BackendFixture {
  backendPort: number;
  backendUrl: string;
  instanceId: string;
}

type TestFixtures = {
  backend: BackendFixture;
  page: Page;
};

/**
 * Setup request interception to route API calls to the worker-specific backend
 */
async function setupApiRouting(page: Page, backendPort: number) {
  // Only intercept requests that start with /api/ (not src/api/ or other paths containing /api/)
  await page.route(/^http:\/\/[^/]+\/api\//, async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    // Replace /api prefix with direct backend URL
    const backendPath = url.pathname.replace('/api', '');
    const backendUrl = `http://localhost:${backendPort}${backendPath}${url.search}`;

    try {
      // Fetch from the worker-specific backend
      const response = await fetch(backendUrl, {
        method: request.method(),
        headers: request.headers(),
        body: request.postDataBuffer() || undefined,
      });

      // Get response body
      const body = await response.arrayBuffer();

      // Forward the response back to the browser
      await route.fulfill({
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        body: Buffer.from(body),
      });
    } catch (error) {
      // If fetch fails, return 503
      await route.fulfill({
        status: 503,
        body: JSON.stringify({ error: 'Backend unavailable' }),
        headers: { 'content-type': 'application/json' },
      });
    }
  });
}

/**
 * Extended test with backend fixture that spawns an isolated backend per worker
 */
export const test = base.extend<TestFixtures>({
  backend: [
    async ({}, use, workerInfo) => {
      // Allocate a unique port for this worker (8000-8099 range)
      const basePort = 8000;
      const port = await findAvailablePort(basePort + workerInfo.workerIndex, basePort + 100);
      const instanceId = randomUUID();

      console.log(`🔧 Worker ${workerInfo.workerIndex}: Starting backend on port ${port} (instance: ${instanceId})`);

      // Spawn backend process
      const backendProcess: ChildProcess = spawn(
        'uv',
        [
          'run',
          '--extra', 'web',
          '--extra', 'rl',
          '--',
          'python', '-m', 'uvicorn',
          'web.backend.main:app',
          '--port', String(port),
          '--host', '127.0.0.1',
        ],
        {
          cwd: path.resolve(__dirname, '../../../'),
          env: {
            ...process.env,
            PYTHONPATH: path.resolve(__dirname, '../../../src'),
            EXPECTED_INSTANCE_ID: instanceId,
            TEST_ROOMS: process.env.TEST_ROOMS || '',
          },
          stdio: ['ignore', 'pipe', 'pipe'],
        }
      );

      // Log backend output for debugging
      backendProcess.stdout?.on('data', (data) => {
        const output = data.toString().trim();
        if (output) {
          console.log(`[Backend ${port}] ${output}`);
        }
      });

      backendProcess.stderr?.on('data', (data) => {
        const output = data.toString().trim();
        if (output && !output.includes('WARNING')) {
          console.error(`[Backend ${port}] ERROR: ${output}`);
        }
      });

      backendProcess.on('error', (error) => {
        console.error(`[Backend ${port}] Process error:`, error);
      });

      backendProcess.on('exit', (code, signal) => {
        if (code !== 0 && code !== null) {
          console.error(`[Backend ${port}] Exited with code ${code}, signal ${signal}`);
        }
      });

      try {
        // Wait for backend to be ready
        await waitForPort(port);
        console.log(`✓ Worker ${workerInfo.workerIndex}: Backend ready on port ${port}`);

        // Verify instance ID matches
        const response = await fetch(`http://localhost:${port}/`);
        const data = await response.json();
        if (data.instance_id !== instanceId) {
          throw new Error(`Backend instance ID mismatch: expected ${instanceId}, got ${data.instance_id}`);
        }

        // Provide the backend info to tests
        await use({
          backendPort: port,
          backendUrl: `http://localhost:${port}`,
          instanceId,
        });
      } finally {
        // Clean up: kill the backend process
        console.log(`🛑 Worker ${workerInfo.workerIndex}: Stopping backend on port ${port}`);
        backendProcess.kill('SIGTERM');

        // Give it a moment to gracefully shutdown
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Force kill if still running
        if (!backendProcess.killed) {
          backendProcess.kill('SIGKILL');
        }
      }
    },
    { scope: 'worker', auto: true },
  ],

  // Override the page fixture to automatically set up API routing
  page: async ({ page: basePage, backend }, use) => {
    await setupApiRouting(basePage, backend.backendPort);
    await use(basePage);
  },
});

export { expect } from '@playwright/test';
