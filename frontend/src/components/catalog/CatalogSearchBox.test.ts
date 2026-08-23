import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CatalogSearchBox from './CatalogSearchBox.vue'

const apiMocks = vi.hoisted(() => ({
  getSearchSuggestions: vi.fn(),
}))

vi.mock('../../api/catalog', () => apiMocks)

describe('CatalogSearchBox', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    apiMocks.getSearchSuggestions.mockResolvedValue([
      {
        kind: 'product',
        label: 'Morrow 手冲咖啡礼盒套装',
        value: 'Morrow 手冲咖啡礼盒套装',
        product_id: 1,
      },
    ])
  })

  afterEach(() => {
    localStorage.clear()
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('shows matching suggestions after the user pauses typing', async () => {
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')
    await wrapper.get('input[aria-label="商品关键词"]').setValue('父母礼物')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(apiMocks.getSearchSuggestions).toHaveBeenCalledWith('父母礼物', 8)
    expect(wrapper.get('[role="listbox"]').text()).toContain('Morrow 手冲咖啡礼盒套装')
  })

  it('selects a product suggestion without launching a second catalog search', async () => {
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')
    await wrapper.get('input[aria-label="商品关键词"]').setValue('父母礼物')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    await wrapper.get('[role="option"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([
      'Morrow 手冲咖啡礼盒套装',
    ])
    expect(wrapper.emitted('select')).toEqual([[expect.objectContaining({ product_id: 1 })]])
    expect(wrapper.emitted('search')).toBeUndefined()
  })

  it('shows recent searches when the empty input receives focus', async () => {
    localStorage.setItem(
      'catalog_recent_searches',
      JSON.stringify(['适合长时间办公', '父母礼物']),
    )
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')

    const listbox = wrapper.get('[role="listbox"]')
    expect(listbox.text()).toContain('最近搜索')
    expect(listbox.text()).toContain('适合长时间办公')
    expect(listbox.text()).toContain('父母礼物')
  })

  it('keeps the six newest unique submitted searches', async () => {
    async function submit(query: string) {
      const wrapper = mount(CatalogSearchBox, {
        props: { modelValue: query },
      })
      await wrapper.get('button[aria-label="搜索"]').trigger('click')
      wrapper.unmount()
    }

    for (const query of ['搜索1', '搜索2', '搜索3', '搜索4', '搜索5', '搜索6', '搜索7'])
      await submit(query)
    await submit('搜索4')

    expect(JSON.parse(localStorage.getItem('catalog_recent_searches') || '[]')).toEqual([
      '搜索4',
      '搜索7',
      '搜索6',
      '搜索5',
      '搜索3',
      '搜索2',
    ])
  })

  it('submits a recent search through the public component events', async () => {
    localStorage.setItem('catalog_recent_searches', JSON.stringify(['人体工学椅']))
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')
    await wrapper.get('[role="option"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['人体工学椅'])
    expect(wrapper.emitted('search')).toEqual([['人体工学椅']])
  })

  it('clears recent searches from the panel and local storage', async () => {
    localStorage.setItem('catalog_recent_searches', JSON.stringify(['人体工学椅']))
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')
    await wrapper.get('button[aria-label="清空最近搜索"]').trigger('click')

    expect(localStorage.getItem('catalog_recent_searches')).toBeNull()
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('replaces damaged history data when a new search is submitted', async () => {
    localStorage.setItem('catalog_recent_searches', '{broken-json')
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '办公椅' },
    })

    await wrapper.get('button[aria-label="搜索"]').trigger('click')

    expect(JSON.parse(localStorage.getItem('catalog_recent_searches') || '[]')).toEqual([
      '办公椅',
    ])
  })
})
