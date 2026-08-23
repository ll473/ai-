import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MarkdownText from './MarkdownText.vue'

describe('MarkdownText', () => {
  it('removes executable HTML from AI-generated Markdown', () => {
    const wrapper = mount(MarkdownText, {
      props: {
        content: '<img src="x" onerror="alert(1)"><script>alert(2)</script>安全内容',
      },
    })

    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').attributes('onerror')).toBeUndefined()
    expect(wrapper.text()).toContain('安全内容')
  })
})
