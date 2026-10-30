import { apiClient } from './client';
import { CaptchaData, LoginResponse, User } from '../types/auth';

export interface LoginPayload {
  role: 'INSTITUTE' | 'ADMIN';
  institute_name?: string;
  institute_id?: string;
  identifier?: string;
  password?: string;
  captcha_id: string;
  captcha_text: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  role: 'INSTITUTE' | 'ADMIN';
  aicte_institute_id?: string;
  institute_name?: string;
  state?: string;
}

export const authApi = {
  getCaptcha: async (): Promise<CaptchaData> => {
    const response = await apiClient.get<CaptchaData>('/api/auth/captcha');
    return response.data;
  },

  login: async (payload: LoginPayload): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/auth/login', payload);
    return response.data;
  },

  logout: async (): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/api/auth/logout');
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/auth/me');
    return response.data;
  },

  refreshToken: async (): Promise<{ message: string; csrf_token: string }> => {
    const response = await apiClient.post<{ message: string; csrf_token: string }>('/api/auth/refresh');
    return response.data;
  },

  register: async (payload: RegisterPayload): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/api/auth/register', payload);
    return response.data;
  },
};

