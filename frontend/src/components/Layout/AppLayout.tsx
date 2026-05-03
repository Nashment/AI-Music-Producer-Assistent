import { Outlet } from 'react-router-dom';
import AppHeader from './AppHeader';

/**
 * Layout para todas as paginas autenticadas: header fixo + conteudo
 * principal com largura maxima e padding consistente.
 */
export function AppLayout() {
    return (
        <div className="app-shell">
            <AppHeader />
            <main className="app-main">
                <Outlet />
            </main>
        </div>
    );
}

export default AppLayout;
