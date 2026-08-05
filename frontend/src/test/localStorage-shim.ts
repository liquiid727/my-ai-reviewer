// Node 22+ 自带不完整的 localStorage 全局对象（无 --experimental-webstorage 时缺少
// getItem 等方法），会遮蔽 vitest jsdom 环境的实现，导致全部套件在初始化阶段报错。
// 这里在任何业务模块（如 i18n config）导入之前注入内存版 shim。
if (
  typeof localStorage === 'undefined' ||
  typeof localStorage.getItem !== 'function'
) {
  const store = new Map<string, string>()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
      setItem: (key: string, value: string) => {
        store.set(key, String(value))
      },
      removeItem: (key: string) => {
        store.delete(key)
      },
      clear: () => store.clear(),
      key: (index: number) => Array.from(store.keys())[index] ?? null,
      get length() {
        return store.size
      },
    },
  })
}

export {}
