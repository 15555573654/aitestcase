import { requestJson } from '../../core/api'
import type { AgentChatMessage, AgentResponse, FilterOptions, FlashcardResource, FlashcardResourceTypeCount, PictureItem, QuestionDetail } from './types'

export interface BqSource {
  key: string
  label: string
  project_id: string
  dataset: string
  table: string
}

export const createBqApi = (baseUrl: string) => ({
  async getSources(): Promise<BqSource[]> {
    return requestJson<BqSource[]>(`${baseUrl}/api/bq/sources`, { method: 'GET' }, '获取数据源列表失败')
  },

  async getFields(sourceKey: string): Promise<{ name: string; type: string }[]> {
    return requestJson(`${baseUrl}/api/bq/${sourceKey}/fields`, { method: 'GET' }, '获取字段列表失败')
  },

  async getFilterOptions(sourceKey: string): Promise<FilterOptions> {
    return requestJson<FilterOptions>(`${baseUrl}/api/bq/${sourceKey}/options`, { method: 'GET' }, '获取过滤选项失败')
  },

  async searchPictures(sourceKey: string, params: {
    language?: string; subject?: string; task_type?: string
    start_date?: string; end_date?: string; limit?: number; offset?: number
  }): Promise<PictureItem[]> {
    return requestJson<PictureItem[]>(
      `${baseUrl}/api/bq/${sourceKey}/search/pictures`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) },
      '查询失败',
    )
  },

  async lookupQuestion(sourceKey: string, params: {
    question_id?: string; device_id?: string; limit?: number
  }): Promise<QuestionDetail[]> {
    return requestJson<QuestionDetail[]>(
      `${baseUrl}/api/bq/${sourceKey}/question/lookup`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) },
      '查询失败',
    )
  },

  async getFlashcardResourceTypes(): Promise<FlashcardResourceTypeCount[]> {
    return requestJson<FlashcardResourceTypeCount[]>(
      `${baseUrl}/api/bq/flashcards/resource-types`,
      { method: 'GET' },
      '获取资源类型失败',
    )
  },

  async searchFlashcards(params: {
    resource_type?: string
    uid?: string
    platform?: string
    status?: string
    start_date?: string
    end_date?: string
    include_deleted?: boolean
    limit?: number
    offset?: number
  }): Promise<FlashcardResource[]> {
    return requestJson<FlashcardResource[]>(
      `${baseUrl}/api/bq/flashcards/search`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) },
      '查询失败',
    )
  },

  async agentChat(sourceKey: string, message: string, history: AgentChatMessage[]): Promise<AgentResponse> {
    return requestJson<AgentResponse>(
      `${baseUrl}/api/bq/${sourceKey}/agent/chat`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, history }) },
      'Agent 调用失败',
    )
  },
})
