import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AssistantView from './AssistantView.vue'

const apiMocks = vi.hoisted(() => ({
  askProductQuestion: vi.fn(),
  getConversation: vi.fn(),
  getConversations: vi.fn(),
  getOrders: vi.fn(),
  getProducts: vi.fn(),
}))

vi.mock('../../api/ai', () => ({
  askProductQuestion: apiMocks.askProductQuestion,
  getConversation: apiMocks.getConversation,
  getConversations: apiMocks.getConversations,
}))
vi.mock('../../api/catalog', () => ({ getProducts: apiMocks.getProducts }))
vi.mock('../../api/trade', () => ({ getOrders: apiMocks.getOrders }))

const conversation = {
  id: 7,
  title: '适合长时间办公',
  scene: 'PRODUCT_QA',
  last_message_at: '2026-08-23T12:00:00Z',
  message_count: 2,
  created_at: '2026-08-23T12:00:00Z',
}

describe('AssistantView', () => {
  beforeEach(() => {
    apiMocks.getProducts.mockResolvedValue({
      items: [{ id: 42, name: '人体工学椅' }],
    })
    apiMocks.getOrders.mockResolvedValue({ items: [] })
    apiMocks.getConversations.mockResolvedValue({ items: [conversation] })
    apiMocks.getConversation.mockResolvedValue({
      ...conversation,
      messages: [
        {
          id: 1,
          role: 'USER',
          content: '适合长时间办公吗',
          question_type: 'PRICE_STOCK',
          metadata_json: { product_id: 42, order_no: null },
          created_at: '2026-08-23T12:00:00Z',
        },
        {
          id: 2,
          role: 'ASSISTANT',
          content: '**适合**。',
          question_type: 'PRICE_STOCK',
          metadata_json: null,
          created_at: '2026-08-23T12:00:01Z',
        },
      ],
    })
  })

  it('restores the selected product when reopening a historical consultation', async () => {
    const wrapper = mount(AssistantView, {
      global: {
        stubs: {
          ElButton: { template: '<button><slot /></button>' },
          ElEmpty: { template: '<div />' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInput: { template: '<textarea />' },
          ElOption: { template: '<span />' },
          ElSegmented: {
            props: ['modelValue'],
            template: '<div class="question-type">{{ modelValue }}</div>',
          },
          ElSelect: {
            props: ['modelValue', 'placeholder'],
            template: '<div class="select-value" :data-placeholder="placeholder">{{ modelValue }}</div>',
          },
        },
      },
    })
    await flushPromises()

    await wrapper.find('.history-panel > button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.question-type').text()).toBe('PRICE_STOCK')
    expect(wrapper.find('[data-placeholder="选择商品"]').text()).toBe('42')
  })

  it('renders historical AI Markdown instead of showing formatting symbols', async () => {
    const wrapper = mount(AssistantView, {
      global: {
        stubs: {
          ElButton: { template: '<button><slot /></button>' },
          ElEmpty: { template: '<div />' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInput: { template: '<textarea />' },
          ElOption: { template: '<span />' },
          ElSegmented: { template: '<div />' },
          ElSelect: { template: '<div><slot /></div>' },
        },
      },
    })
    await flushPromises()

    await wrapper.find('.history-panel > button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.message.assistant strong').text()).toBe('适合')
    expect(wrapper.find('.message.assistant').text()).not.toContain('**')
  })
})
