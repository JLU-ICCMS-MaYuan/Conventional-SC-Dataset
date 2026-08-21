import React from 'react'
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import MultiFileUploadPanel from '../../frontend/src/components/MultiFileUploadPanel'
import UploadParsingDetail from '../../frontend/src/components/UploadParsingDetail'
import UploadPage from '../../frontend/src/pages/UploadPage'
import { AuthProvider } from '../../frontend/src/context/AuthContext'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

const task = (id: string, filename: string) => ({
  task_id: id,
  filename,
  status: 'reading',
  stage: 'reading',
  stage_index: 3,
  stage_total: 5,
  processing_status: 'processing',
  completed_chunks: 2,
  total_chunks: 8,
  files: [],
})

describe('论文上传工作区', () => {
  it('把一次拖入的多个文件保留在同一个可清空的任务草稿中', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<MultiFileUploadPanel onCreated={vi.fn()} />)

    const main = new File(['paper'], 'paper.pdf', { type: 'application/pdf' })
    const supplement = new File(['notes'], 'notes.md', { type: 'text/markdown' })
    fireEvent.drop(screen.getByLabelText('拖拽或选择论文文件'), {
      dataTransfer: { files: [main, supplement] },
    })

    expect(screen.getByText('paper.pdf')).toBeVisible()
    expect(screen.getByText('notes.md')).toBeVisible()
    expect(screen.getAllByRole('combobox')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', { name: '清空' }))

    expect(screen.queryByText('paper.pdf')).not.toBeInTheDocument()
    expect(screen.queryByText('notes.md')).not.toBeInTheDocument()
  })

  it('分段尚未生成时仍显示临时表单和解析证据入口', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'extracting',
        stage: 'extracting',
        files: [{ file_id: 'main', role: 'main', original_filename: 'paper.pdf', extraction_status: 'processing' }],
        chunks: [],
        form_preview: { status: 'waiting', read_only: true, groups: [] },
        summary: { status: 'extracting', completed: 0, total: 0 },
        next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'c'.repeat(32)} />)

    expect(await screen.findByRole('tab', { name: 'AI 临时表单' })).toBeVisible()
    expect(screen.getByRole('tab', { name: '分段解析与证据' })).toBeVisible()
    expect(screen.getByText('正在提取正文，完成后会在这里逐段显示解析结果。')).toBeVisible()
  })

  it('解析完成后在临时表单页签原地切换为可编辑草稿', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const data = url.endsWith('/parsing')
        ? {
            status: 'ready', stage: 'ready', files: [], chunks: [],
            form_preview: { status: 'ready', read_only: false, groups: [] },
            summary: { status: 'completed', completed: 1, total: 1 }, next_poll_ms: null,
          }
        : {
            paper: { title: 'Hydride study', authors: [], research_materials: ['LaH10'] },
            key_properties: [], sc_type: 'hydride', classification_evidence: [], field_evidence: {},
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'d'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByRole('textbox', { name: '标题' })).toHaveValue('Hydride study')
    expect(screen.getByRole('button', { name: '提交审核' })).toBeVisible()
  })

  it('临时表单并列显示冲突候选及其文件来源', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [{
          chunk_id: 'main:0', filename: 'paper.pdf', file_role: 'main', section: 'Title',
          page_start: 1, page_end: 1, status: 'completed', result: { metadata: { title: 'Main title' } },
        }],
        form_preview: {
          status: 'updating', read_only: true, groups: [{
            id: 'bibliography', label: '基本信息', fields: [{
              path: 'paper.title', label: '标题', state: 'conflict', candidates: [
                { value: 'Main title', sources: [{ filename: 'paper.pdf', file_role: 'main', section: 'Title', page_start: 1, quote: 'Main title' }] },
                { value: 'Supplement title', sources: [{ filename: 'supp.pdf', file_role: 'supplementary', section: 'Cover', page_start: 2, quote: 'Supplement title' }] },
              ],
            }],
          }],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'e'.repeat(32)} />)

    expect(await screen.findByText('有冲突')).toBeVisible()
    expect(screen.getByText('Main title')).toBeVisible()
    expect(screen.getByText('Supplement title')).toBeVisible()
    expect(screen.getByText('paper.pdf · 正文 · Title · 第 1 页')).toBeVisible()
    expect(screen.getByText('supp.pdf · 补充材料 · Cover · 第 2 页')).toBeVisible()
  })

  it('查看和切换解析任务时仍保留上传入口及其本地文件', async () => {
    const first = task('a'.repeat(32), '第一篇.pdf')
    const second = task('b'.repeat(32), '第二篇.pdf')
    localStorage.setItem('auth_token', 'test-token')
    localStorage.setItem('auth_user', JSON.stringify({
      id: 7, email: 'user@example.com', username: 'tester', username_change_allowed: false,
      role: 'user', is_admin: false, is_superadmin: false, is_approved: true,
      created_at: null, approved_at: null,
    }))
    localStorage.setItem('scwiki_active_upload_task:7', first.task_id)
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      let body: unknown = { ok: true }
      if (url === '/api/upload-tasks') body = { ok: true, data: [first, second] }
      else if (url === `/api/upload-tasks/${first.task_id}`) body = { ok: true, data: first }
      else if (url === `/api/upload-tasks/${second.task_id}`) body = { ok: true, data: second }
      else if (url.endsWith('/parsing')) body = {
        ok: true, data: { status: 'reading', stage: 'reading', files: [], chunks: [], summary: { status: 'reading', completed: 2, total: 8 }, next_poll_ms: null },
      }
      else if (url.startsWith('/api/papers/my-uploads')) body = { items: [], total: 0 }
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))

    render(<MemoryRouter><AuthProvider><UploadPage /></AuthProvider></MemoryRouter>)

    const dropArea = await screen.findByLabelText('拖拽或选择论文文件')
    fireEvent.drop(dropArea, {
      dataTransfer: { files: [new File(['draft'], '待上传.pdf', { type: 'application/pdf' })] },
    })
    expect(screen.getByText('待上传.pdf')).toBeVisible()

    fireEvent.click(await screen.findByRole('button', { name: '查看 第二篇.pdf 的解析详情' }))

    await waitFor(() => expect(screen.getByText('待上传.pdf')).toBeVisible())
    expect(screen.getByLabelText('拖拽或选择论文文件')).toBeVisible()
    expect(screen.getByRole('button', { name: '收起 第二篇.pdf 的解析详情' })).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: '收起 第二篇.pdf 的解析详情' }))

    expect(await screen.findByRole('button', { name: '查看 第二篇.pdf 的解析详情' })).toBeVisible()
  })
})
