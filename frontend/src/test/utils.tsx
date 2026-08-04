import { createElement, type ReactElement, type ReactNode } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { I18nextProvider } from 'react-i18next'
import i18n from '@/i18n/config'

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      I18nextProvider,
      { i18n },
      createElement(MemoryRouter, null, children),
    )
  return render(ui, { wrapper, ...options })
}

export { screen, waitFor, within, act, cleanup, fireEvent } from '@testing-library/react'
