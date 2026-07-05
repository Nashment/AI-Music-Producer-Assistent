/**
 * Testes unitarios para AuthContext/AuthProvider.
 *
 * Cobre:
 *   - Estado inicial vem de getStoredUser() (localStorage)
 *   - refresh() nao chama a API quando nao ha token (isAuthenticated=false)
 *   - refresh() chama userService.getMe() quando ha token, actualiza user
 *     e persiste em localStorage
 *   - erro de refresh() define a mensagem de erro
 *   - logout() limpa o user e o localStorage
 *   - useAuthContext() fora de <AuthProvider> lanca erro
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';

vi.mock('../../../src/services/user/userService', () => ({
    userService: { getMe: vi.fn() },
}));

import { AuthProvider, useAuthContext } from '../../../src/context/AuthContext';
import { userService } from '../../../src/services/user/userService';
import { saveAuth, getStoredUser } from '../../../src/utils/auth';

function Consumer() {
    const { user, loading, error, logout } = useAuthContext();
    return (
        <div>
            <span data-testid="user">{user ? user.username : 'sem-user'}</span>
            <span data-testid="loading">{String(loading)}</span>
            <span data-testid="error">{error ?? 'sem-erro'}</span>
            <button onClick={logout}>Sair</button>
        </div>
    );
}

beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
});

describe('AuthProvider', () => {
    it('inicializa o user a partir do localStorage (getStoredUser)', async () => {
        saveAuth('token-x', { id: 'u1', username: 'nash' });
        vi.mocked(userService.getMe).mockResolvedValueOnce({ id: 'u1', username: 'nash' });
        render(
            <AuthProvider>
                <Consumer />
            </AuthProvider>,
        );
        expect(screen.getByTestId('user').textContent).toBe('nash');
        await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));
    });

    it('nao chama userService.getMe() quando nao ha token', async () => {
        render(
            <AuthProvider>
                <Consumer />
            </AuthProvider>,
        );
        await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));
        expect(userService.getMe).not.toHaveBeenCalled();
    });

    it('chama userService.getMe() quando ha token e actualiza o user', async () => {
        saveAuth('token-x', { id: 'u1', username: 'nome-antigo' });
        vi.mocked(userService.getMe).mockResolvedValueOnce({ id: 'u1', username: 'nome-actualizado' });

        render(
            <AuthProvider>
                <Consumer />
            </AuthProvider>,
        );

        await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('nome-actualizado'));
        expect(getStoredUser()).toEqual({ id: 'u1', username: 'nome-actualizado' });
    });

    it('define error quando userService.getMe() falha', async () => {
        saveAuth('token-x', { id: 'u1', username: 'nash' });
        vi.mocked(userService.getMe).mockRejectedValueOnce({ detail: 'Sessao expirada.' });

        render(
            <AuthProvider>
                <Consumer />
            </AuthProvider>,
        );

        await waitFor(() => expect(screen.getByTestId('error').textContent).toBe('Sessao expirada.'));
    });

    it('logout() limpa o user do estado e do localStorage', async () => {
        saveAuth('token-x', { id: 'u1', username: 'nash' });
        const { default: userEvent } = await import('@testing-library/user-event');
        const user = userEvent.setup();

        render(
            <AuthProvider>
                <Consumer />
            </AuthProvider>,
        );
        expect(screen.getByTestId('user').textContent).toBe('nash');

        await user.click(screen.getByText('Sair'));

        expect(screen.getByTestId('user').textContent).toBe('sem-user');
        expect(getStoredUser()).toBeNull();
    });
});

describe('useAuthContext', () => {
    it('lanca erro quando usado fora de AuthProvider', () => {
        const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
        expect(() => render(<Consumer />)).toThrow('useAuthContext deve ser usado dentro de <AuthProvider>');
        spy.mockRestore();
    });
});
