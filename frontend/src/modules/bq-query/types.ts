export interface PictureItem {
  question_id: string | null
  picture_key: string | null
  subject: string | null
  language: string | null
  task_type: string | null
  create_time: string | null
  image_url: string | null
}

export interface QuestionDetail {
  question_id: string | null
  device_id: string | null
  subject: string | null
  language: string | null
  task_type: string | null
  question_text: string | null
  answer: string | null
  picture_key: string | null
  create_time: string | null
  image_url: string | null
}

export interface FilterOptions {
  languages: string[]
  subjects: string[]
  task_types: string[]
}

export interface FlashcardResource {
  uid: string | null
  deck_id: string | null
  name: string | null
  resource_type: string | null
  origin_url: string | null
  parsed_url: string | null
  selected_page_index: string | null
  platform: string | null
  create_at: string | null
  update_at: string | null
  deleted_at: string | null
  source: string | null
  status: string | null
}

export interface FlashcardResourceTypeCount {
  resource_type: string
  count: number
}

export interface AgentChatMessage {
  role: 'user' | 'model'
  content: string
}

export interface AgentResponse {
  reply: string
  results: any[] | null
  sql_executed: string | null
  result_type: 'pictures' | 'questions' | 'text' | null
}
