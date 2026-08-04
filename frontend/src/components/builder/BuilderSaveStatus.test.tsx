import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { BuilderSaveStatus } from '@/components/builder/BuilderSaveStatus'
import { renderWithProviders, screen } from '@/test/utils'

describe('BuilderSaveStatus', () => {
  it('shows saved label on successful save path', () => {
    renderWithProviders(<BuilderSaveStatus status="saved" />)
    expect(screen.getByTestId('builder-save-label')).toHaveTextContent('Saved')
    expect(screen.queryByTestId('builder-save-conflict')).not.toBeInTheDocument()
  })

  it('shows generic error label', () => {
    renderWithProviders(<BuilderSaveStatus status="error" />)
    expect(screen.getByTestId('builder-save-label')).toHaveTextContent('Failed to save')
  })

  it('shows revision conflict banner and reload action', async () => {
    const user = userEvent.setup()
    const onReload = vi.fn()
    renderWithProviders(
      <BuilderSaveStatus
        status="conflict"
        conflictMessage="base_revision mismatch"
        onReload={onReload}
      />,
    )
    expect(screen.getByTestId('builder-save-conflict')).toBeInTheDocument()
    expect(screen.getByText('Changes need reconciliation')).toBeInTheDocument()
    expect(screen.getByText('base_revision mismatch')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reload server version' }))
    expect(onReload).toHaveBeenCalledTimes(1)
  })

  it('shows saving label while request is in flight', () => {
    renderWithProviders(<BuilderSaveStatus status="saving" />)
    expect(screen.getByTestId('builder-save-label')).toHaveTextContent('Saving...')
  })
})
