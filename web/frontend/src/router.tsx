/**
 * TanStack Router configuration.
 */

import {
  createRouter,
  createRootRoute,
  createRoute,
  Outlet,
  redirect,
} from '@tanstack/react-router';
import { Lobby } from './pages/Lobby';
import { Game } from './pages/Game';
import { getStoredSession } from './api/client';

// Root route with layout
const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

// Home/Lobby route
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Lobby,
});

// Room route (waiting room / join)
const roomRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/room/$roomId',
  component: Lobby,
  beforeLoad: ({ params }) => {
    const session = getStoredSession();
    // If we have a session for this room, redirect to game
    if (session && session.roomId === params.roomId) {
      throw redirect({ to: '/game/$roomId', params: { roomId: params.roomId } });
    }
    return { joinRoomId: params.roomId };
  },
});

// Game route
const gameRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/game/$roomId',
  component: Game,
  beforeLoad: ({ params }) => {
    const session = getStoredSession();
    // If no session, redirect to room join page
    if (!session || session.roomId !== params.roomId) {
      throw redirect({ to: '/room/$roomId', params: { roomId: params.roomId } });
    }
    return { session };
  },
});

// Build route tree
const routeTree = rootRoute.addChildren([indexRoute, roomRoute, gameRoute]);

// Create router
export const router = createRouter({ routeTree });

// Type declaration for router
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

