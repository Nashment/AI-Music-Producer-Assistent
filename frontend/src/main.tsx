import * as React from 'react';
import * as ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import type { JSX } from 'react';

import AuthenticationPage from './pages/authentication';
import OAuthCallbackPage from './pages/oauthCallback';
import LogoutPage from './pages/logout';

import HomePage from './pages/HomePage';
import ProfilePage from './pages/profile';

import ProjectsPage from './pages/projects';
import ProjectDetailPage from './pages/projectDetail';

import AudioDetailPage from './pages/audioDetail';

import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/Layout/AppLayout';
import { ToastProvider } from './components/Layout/Toast';

type Page = {
    path: string;
    element: JSX.Element;
};

// Rotas autenticadas. Sao envolvidas no <AppLayout> que adiciona header
// global e padding da pagina.
const authRoutes: Page[] = [
    { path: '/home', element: <HomePage /> },
    { path: '/profile', element: <ProfilePage /> },

    { path: '/projects', element: <ProjectsPage /> },
    { path: '/projects/:projectId', element: <ProjectDetailPage /> },
    { path: '/projects/:projectId/audio/:audioId', element: <AudioDetailPage /> },

    // NOTA: as rotas de geracao (/projects/:id/audio/:id/generate) ficam
    // intencionalmente fora deste scaffold ate o fluxo de generation ser
    // integrado. O service/hook/page do dominio existe no repo, basta
    // re-introduzir a rota quando estiver pronto.

    { path: '/logout', element: <LogoutPage /> },
];

// Rotas publicas (sem token).
const publicRoutes: Page[] = [
    { path: '/', element: <AuthenticationPage /> },
    { path: '/login', element: <AuthenticationPage /> },
    { path: '/auth/callback', element: <OAuthCallbackPage /> },
];

const router = createBrowserRouter([
    ...publicRoutes,
    {
        element: <ProtectedRoute />,
        children: [
            {
                element: <AppLayout />,
                children: authRoutes,
            },
        ],
    },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <ToastProvider>
            <RouterProvider router={router} />
        </ToastProvider>
    </React.StrictMode>,
);
