import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { userService } from '../services/user/userService';

/**
 * Pagina /logout. Limpa o JWT local e redirecciona para /login.
 */
function LogoutPage() {
    const navigate = useNavigate();

    useEffect(() => {
        userService.logout();
        navigate('/login', { replace: true });
    }, [navigate]);

    return <div className="page-loading">A terminar sessao…</div>;
}

export default LogoutPage;
