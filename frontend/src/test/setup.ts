import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// 必须在业务模块（如 i18n config）之前注入 localStorage shim（Node 22+ 自带不完整实现）
import './localStorage-shim'
import '@/i18n/config'

afterEach(() => {
  cleanup()
})
