import { defineConfig } from 'vite';
// @ts-ignore
import react from '@vitejs/plugin-react';

// O backend FastAPI corre por defeito em http://localhost:8000 e expoe o
// prefixo /api/v1. Aqui mantemos a chamada a partir do frontend como /api/...
// e o proxy do Vite reescreve para /api/v1/... no servidor.
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
            },
        },
    },
});
