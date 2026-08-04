export interface ApiResponse<T> {
  code: string
  message: string
  data: T
}

export interface PageData<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export interface User {
  id: number
  username: string
  email: string | null
  phone: string | null
  nickname: string | null
  avatar_url: string | null
  role: 'ADMIN' | 'USER'
  status: 'ACTIVE' | 'DISABLED'
  created_at: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: User
}

