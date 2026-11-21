// TypeScript interfaces for VisionVault

export interface User {
  id: number
  email: string
  role: string
  created_at: string
}

export interface Category {
  id: number
  name: string
  parent_id: number | null
  created_at: string
  image_count?: number
  children?: Category[]
}

export interface ImageData {
  id: number
  filename: string
  thumbnail_url: string | null
  image_url: string | null
  category_id: number | null
  category_name: string | null
  source_type: string
  parent_image_id: number | null
  width: number | null
  height: number | null
  file_size: number | null
  created_at: string
  is_indexed: boolean
}

export interface SearchResult {
  image_id: number
  distance: number
  rank: number
  image: ImageData
  same_category?: boolean
}

export interface FeedbackIteration {
  id: number
  session_id: number
  iteration_number: number
  relevant_image_ids: number[] | null
  non_relevant_image_ids: number[] | null
  weights: number[] | null
  result_image_ids: number[] | null
  precision_at_k: number | null
  recall_at_k: number | null
  created_at: string
}

export interface SearchSession {
  id: number
  user_id: number
  query_image_id: number | null
  created_at: string
  iterations?: FeedbackIteration[]
}

export interface ColorMomentDetail {
  mean: number
  std: number
  skewness: number
}

export interface DominantColor {
  rgb: number[]
  hex: string
  percentage: number
}

export interface GLCMDetails {
  contrast: number
  correlation: number
  energy: number
  homogeneity: number
  dissimilarity: number
  asm: number
}

export interface FeatureDetails {
  vector: number[]
  color_histogram: {
    histogram: number[]
    h_hist: number[]
    s_hist: number[]
    v_hist: number[]
    params: { h_bins: number; s_bins: number; v_bins: number }
  }
  color_moments: {
    moments: number[]
    details: { H: ColorMomentDetail; S: ColorMomentDetail; V: ColorMomentDetail }
  }
  dominant_colors: {
    colors: DominantColor[]
    feature_vector: number[]
  }
  glcm: {
    features: number[]
    details: GLCMDetails
    params: { distances: number[]; angles: number; levels: number }
  }
  lbp: {
    histogram: number[]
    params: { P: number; R: number; method: string; n_bins: number }
  }
}

export interface AnalyticsOverview {
  total_images: number
  categories: number
  user_uploads: number
  searches: number
  index_status: { total: number; indexed: number }
  category_distribution: { category_id: number; category_name: string; image_count: number }[]
  recent_activity: { id: number; search_type: string; result_count: number; duration_ms: number; created_at: string }[]
}

export interface WeightGroup {
  mean: number
  values: number[]
}

export interface PaginatedResponse<T> {
  images: T[]
  total: number
  page: number
  per_page: number
  pages: number
}
