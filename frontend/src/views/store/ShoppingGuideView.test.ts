import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AgentRun } from '../../types/ai'
import ShoppingGuideView from './ShoppingGuideView.vue'

const apiMocks = vi.hoisted(() => ({
  getShoppingGuideRuns: vi.fn(),
  runShoppingGuide: vi.fn(),
}))

vi.mock('../../api/ai', () => apiMocks)
vi.mock('../../api/trade', () => ({ addCartItem: vi.fn() }))

const markdownRun: AgentRun = {
  id: 1,
  run_no: 'AR-MARKDOWN',
  conversation_id: 1,
  status: 'SUCCEEDED',
  request_text: '适合长时间办公吗',
  final_answer: '具备以下特点：\n\n1. **动态支撑**：降低腰背压力。',
  error_message: null,
  actual_steps: 1,
  max_steps: 6,
  total_duration_ms: 100,
  started_at: '2026-08-23T12:00:00Z',
  finished_at: '2026-08-23T12:00:00Z',
  recommendation: null,
}

describe('ShoppingGuideView', () => {
  beforeEach(() => {
    apiMocks.getShoppingGuideRuns.mockResolvedValue({ items: [markdownRun] })
    vi.stubGlobal('scrollTo', vi.fn())
  })

  it('renders AI Markdown emphasis instead of showing asterisks', async () => {
    const wrapper = mount(ShoppingGuideView, {
      global: {
        stubs: {
          ElButton: { template: '<button><slot /></button>' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInput: { template: '<textarea />' },
          ElSkeleton: { template: '<div />' },
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()
    await wrapper.find('.history-panel > button').trigger('click')

    expect(wrapper.find('.answer-copy strong').text()).toBe('动态支撑')
    expect(wrapper.find('.answer-copy').text()).not.toContain('**')
  })
})
