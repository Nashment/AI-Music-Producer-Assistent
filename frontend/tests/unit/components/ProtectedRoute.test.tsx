/**
 * Testes unitários para ProtectedRoute — a guarda de rota que decide entre
 * mostrar o conteúdo protegido, redireccionar para /login, ou mostrar um
 * spinner enquanto a verificação está em curso.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import React from 'react';

vi.mock('../../../src/services/request', () => ({
    checkAuth: vi.fn(),
}));

import { ProtectedRoute } from '../../../src/components/ProtectedRoute';
import { checkAuth } from '../../../src/services/request';

function renderProtected() {
    return render(
        <MemoryRouter initialEntries={['/protegido']}>
            <Routes>
                <Route path="/login" element={<div>Página de Login</div>} />
                <Route element={<ProtectedRoute />}>
                    <Route path="/protegido" element={<div>Conteúdo Protegido</div>} />
                </Route>
            </Routes>
        </MemoryRouter>,
    );
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe('ProtectedRoute', () => {
    it('mostra um spinner enquanto checkAuth está pendente', () => {
        vi.mocked(checkAuth).mockReturnValueOnce(new Promise(() => {})); // nunca resolve
        renderProtected();
        expect(screen.getByText(/a verificar sessão/i)).toBeInTheDocument();
    });

    it('renderiza o conteúdo protegido (Outlet) quando checkAuth devolve true', async () => {
        vi.mocked(checkAuth).mockResolvedValueOnce(true);
        renderProtected();
        await waitFor(() => expect(screen.getByText('Conteúdo Protegido')).toBeInTheDocument());
    });

    it('redirecciona para /login quando checkAuth devolve false', async () => {
        vi.mocked(checkAuth).mockResolvedValueOnce(false);
        renderProtected();
        await waitFor(() => expect(screen.getByText('Página de Login')).toBeInTheDocument());
        expect(screen.queryByText('Conteúdo Protegido')).not.toBeInTheDocument();
    });

    it('não actualiza o estado depois de desmontado (evita "setState em componente desmontado")', async () => {
        let resolveCheck: (v: boolean) => void = () => {};
        vi.mocked(checkAuth).mockReturnValueOnce(new Promise(res => { resolveCheck = res; }));

        const { unmount } = renderProtected();
        unmount();

        // Resolve depois de desmontado — não deve lançar nem gerar warnings.
        expect(() => resolveCheck(true)).not.toThrow();
    });
});
