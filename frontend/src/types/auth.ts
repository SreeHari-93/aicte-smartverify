export type UserRole = 'INSTITUTE' | 'ADMIN' | 'REVIEWER';

export interface InstituteInfo {
  id: number;
  aicte_institute_id: string;
  name: string;
  state: string;
  status: string;
}

export interface User {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  institute?: InstituteInfo | null;
}

export interface CaptchaData {
  captcha_id: string;
  image_base64: string;
}

export interface LoginResponse {
  message: string;
  user: User;
  csrf_token: string;
}

export interface LockoutDetail {
  message: string;
  locked: boolean;
  remaining_seconds: number;
}

