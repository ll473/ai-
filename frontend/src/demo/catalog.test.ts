import { describe, expect, it } from 'vitest'

import { getDemoProductComparison } from './catalog'

describe('getDemoProductComparison', () => {
  it('maps demo SKUs to the public comparison-safe shape', () => {
    const result = getDemoProductComparison([2, 3])
    const sku = result.items[0].skus[0]

    expect(Object.keys(sku).sort()).toEqual([
      'attributes',
      'available_stock',
      'name',
      'price',
    ])
    expect(sku).not.toHaveProperty('sku_no')
    expect(sku).not.toHaveProperty('stock')
    expect(sku).not.toHaveProperty('locked_stock')
    expect(sku).not.toHaveProperty('created_at')
  })
})
