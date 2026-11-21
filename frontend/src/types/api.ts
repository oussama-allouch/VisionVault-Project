export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: { id: number; email: string; role: string };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UploadResponse {
  id: number;
  filename: string;
  thumbnail_url: string;
  image_url: string;
}

export interface SearchRequest {
  image_id?: number;
  top_k?: number;
}

export interface FeedbackRequest {
  session_id: number;
  relevant_ids: number[];
  non_relevant_ids: number[];
}

export interface TransformRequest {
  operation: string;
  parameters: Record<string, unknown>;
}
