/**
 * Authentication Service
 * Handles user registration, login, logout, and session management
 */

export type { User } from '../../../types';

const API_BASE_URL = 'http://localhost:8080';

export interface LoginCredentials {
    username: string;
    password: string;
}

export interface RegisterCredentials {
    username: string;
    password: string;
}

export interface AuthResponse {
    status: string;
    username?: string;
    user_id?: number;
}

/**
 * Register a new user
 */
export const register = async (credentials: RegisterCredentials): Promise<AuthResponse> => {
    const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Important for session cookies
        body: JSON.stringify(credentials),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
    }

    return response.json();
};

/**
 * Login user
 */
export const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Important for session cookies
        body: JSON.stringify(credentials),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
    }

    return response.json();
};

/**
 * Logout user
 */
export const logout = async (): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/logout`, {
        method: 'POST',
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error('Logout failed');
    }
};

export interface ChangePasswordCredentials {
    current_password: string;
    new_password: string;
}

export interface ChangePasswordResponse {
    status: string;
    message: string;
}

/**
 * Change user password
 */
export const changePassword = async (credentials: ChangePasswordCredentials): Promise<ChangePasswordResponse> => {
    const response = await fetch(`${API_BASE_URL}/change_password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(credentials),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to change password');
    }

    return response.json();
};

/**
 * Check if user is authenticated by attempting to access a protected endpoint
 */
export const checkAuth = async (): Promise<boolean> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/files`, {
            credentials: 'include',
        });
        return response.ok;
    } catch {
        return false;
    }
};
