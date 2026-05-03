/**
 * Tipos de resposta do dominio "project" — espelham os DTOs em
 * backend/app/domain/dtos/endpoints/projects.py
 */

export type ProjectResponse = {
    id: string;        // uuid
    title: string;
    description: string;
    tempo: number;
    user_id: string;   // uuid
};

export type ProjectCreate = {
    title: string;
    description: string;
    tempo: number;
};

export type ProjectUpdate = {
    title?: string;
    description?: string;
    tempo?: number;
};
