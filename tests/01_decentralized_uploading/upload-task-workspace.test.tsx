import React from 'react'
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

const authenticatedUser = {
  id: 7, email: 'user@example.com', username: 'tester', username_change_allowed: false,
  role: 'user', is_admin: false, is_superadmin: false, is_approved: true,
  is_email_verified: true, account_status: 'active',
  created_at: null, approved_at: null,
}

const seedAuthenticatedUser = () => {
  localStorage.setItem('auth_token', 'test-token')
  localStorage.setItem('auth_user', JSON.stringify(authenticatedUser))
}

describe('论文上传工作区', () => {
  it('只展示未提交任务，不请求或显示旧版 MySQL 上传记录', async () => {
    seedAuthenticatedUser()
    const requested: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      requested.push(url)
      const body = url === '/api/auth/me'
        ? { user: authenticatedUser }
        : url === '/api/upload-tasks'
        ? { ok: true, data: [] }
        : url.startsWith('/api/papers/my-uploads')
          ? {
              items: [{
                id: 19, title: null, source_file_path: 'upload/旧版失败论文.pdf',
                review_status: 'pending', key_properties: [], created_at: '2026-08-19T00:00:00Z',
              }],
              total: 1,
            }
          : { ok: true }
      return new Response(JSON.stringify(body), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<MemoryRouter><AuthProvider><UploadPage /></AuthProvider></MemoryRouter>)

    expect(await screen.findByText('暂无活动任务')).toBeVisible()
    expect(requested.some(url => url.startsWith('/api/papers/my-uploads'))).toBe(false)
    expect(screen.queryByText('上传记录')).not.toBeInTheDocument()
    expect(screen.queryByText('旧版失败论文.pdf')).not.toBeInTheDocument()
  })

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
            paper: {
              title: 'Hydride study', authors: [], research_materials: ['LaH10'],
              referenced_materials: ['H3S'],
            },
            key_properties: [], sc_type: 'hydride', classification_evidence: [], field_evidence: {},
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'d'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByRole('textbox', { name: '标题' })).toHaveValue('Hydride study')
    expect(screen.queryByRole('textbox', { name: '引用材料（每行一个）' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '提交审核' })).toBeVisible()
  })

  it('可编辑草稿中的长 AI 解释按字段宽度收起并可独立展开', async () => {
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function () {
      return this.textContent?.includes('CALYPSO群智能结构搜索') ? 240 : 48
    })
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const data = String(input).endsWith('/parsing')
        ? {
            status: 'ready', stage: 'ready', files: [], chunks: [],
            form_preview: { status: 'ready', read_only: false, groups: [] },
            summary: { status: 'completed', completed: 1, total: 1 }, next_poll_ms: null,
          }
        : {
            paper: {
              title: 'Hydride study', authors: [], research_materials: ['Li2MgH16'],
              methodology: ['CALYPSO群智能结构搜索'],
            },
            material_states: [], sc_type: 'hydride', classification_evidence: [],
            field_evidence: {
              methodology: [{
                section: 'Supplementary Material', page: 2,
                quote: 'The simulations were performed with several first-principles methods and detailed convergence checks.',
              }],
            },
            ai_original: {
              paper: {
                title: 'Short AI title',
                methodology: Array.from({ length: 20 }, (_, index) => `CALYPSO群智能结构搜索 ${index + 1}`),
              },
            },
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'m'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByText(/AI 建议：Short AI title/)).toBeVisible()
    expect(screen.queryByRole('button', { name: '展开 标题的 AI 解释' })).not.toBeInTheDocument()

    const expandButton = screen.getByRole('button', { name: '展开 研究方法（每行一项）的 AI 解释' })
    expect(expandButton).toHaveAttribute('aria-expanded', 'false')
    const explanation = document.getElementById(expandButton.getAttribute('aria-controls') || '')
    expect(explanation).toBeInTheDocument()
    expect(expandButton.parentElement?.parentElement).toHaveStyle({
      width: '100%', maxWidth: '100%', minWidth: '0',
    })

    fireEvent.click(expandButton)

    expect(screen.getByRole('button', { name: '收起 研究方法（每行一项）的 AI 解释' }))
      .toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/detailed convergence checks/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '收起 研究方法（每行一项）的 AI 解释' }))
    expect(screen.getByRole('button', { name: '展开 研究方法（每行一项）的 AI 解释' }))
      .toHaveAttribute('aria-expanded', 'false')
  })

  it('按材料状态显示压力、空间群和电子声子参数，并以新契约保存', async () => {
    const savedBodies: unknown[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (init?.method === 'PUT') {
        savedBodies.push(JSON.parse(String(init.body)))
        return new Response(JSON.stringify({ ok: true, data: JSON.parse(String(init.body)) }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        })
      }
      const data = url.endsWith('/parsing')
        ? {
            status: 'ready', stage: 'ready', files: [], chunks: [],
            form_preview: { status: 'ready', read_only: false, groups: [] },
            summary: { status: 'completed', completed: 1, total: 1 }, next_poll_ms: null,
          }
        : {
            paper: {
              title: 'Li2MgH16 study', authors: [], paper_type: 'theoretical',
              theoretical_subtype: 'calculation', research_materials: ['Li2MgH16'],
            },
            material_states: [{
              material: 'Li2MgH16',
              pressure_value_gpa: 300,
              pressure_raw: '300',
              pressure_unit_raw: 'GPa',
              state_kind: 'theoretical',
              reported_space_group_symbol: 'Fd-3m',
              reported_space_group_number: 227,
              calculation_context: {
                phonon_nuclear_treatment: 'unknown',
                lambda_ep: 3.35,
                omega_log_k: null,
              },
              experimental_context: null,
              tc_results: [],
              properties: [],
            }],
            sc_type: '高压氢化物', classification_evidence: [], field_evidence: {},
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'f'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByRole('textbox', { name: '材料' })).toHaveValue('Li2MgH16')
    expect(screen.getByRole('spinbutton', { name: '压力 (GPa)' })).toHaveValue(300)
    expect(screen.getByRole('textbox', { name: '空间群符号' })).toHaveValue('Fd-3m')
    expect(screen.getByRole('spinbutton', { name: '空间群号' })).toHaveValue(227)
    expect(screen.getByRole('spinbutton', { name: '电声耦合强度 λ' })).toHaveValue(3.35)
    expect(screen.getByRole('spinbutton', { name: '对数声子频率 ωlog (K)' })).toHaveValue(null)

    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))
    await waitFor(() => expect(savedBodies).toHaveLength(1))
    expect(savedBodies[0]).toMatchObject({
      material_states: [{
        material: 'Li2MgH16',
        pressure_value_gpa: 300,
        reported_space_group_symbol: 'Fd-3m',
        reported_space_group_number: 227,
        calculation_context: { lambda_ep: 3.35, omega_log_k: null },
      }],
    })
    expect(savedBodies[0]).not.toHaveProperty('key_properties')
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

  it('临时表单只收起真实溢出的字段卡片', async () => {
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function () {
      return (this.textContent?.split('\n').length || 0) >= 20 ? 240 : 80
    })
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        form_preview: {
          status: 'updating', read_only: true, groups: [{
            id: 'bibliography', label: '基本信息', fields: [
              {
                path: 'paper.doi', label: 'DOI', state: 'filled',
                candidates: [{ value: '10.1103/PhysRevLett.123.097001', sources: [] }],
              },
              {
                path: 'paper.authors', label: '作者', state: 'filled',
                candidates: [{ value: Array.from({ length: 20 }, (_, index) => `Author ${index + 1}`).join('\n'), sources: [] }],
              },
              {
                path: 'paper.abstract', label: '摘要', state: 'waiting', candidates: [],
              },
            ],
          }],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'g'.repeat(32)} />)

    expect(await screen.findByText('10.1103/PhysRevLett.123.097001')).toBeVisible()
    expect(screen.queryByRole('button', { name: '展开 DOI' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '展开 摘要' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '展开 作者' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText(/Author 20/)).toBeInTheDocument()
  })

  it('临时表单字段卡片可以独立展开和收起且正文点击不误触', async () => {
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(240)
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        form_preview: {
          status: 'updating', read_only: true, groups: [{
            id: 'bibliography', label: '基本信息',
            fields: ['作者', '期刊', '摘要'].map((label, index) => ({
              path: `paper.field_${index}`, label, state: 'filled',
              candidates: [{ value: `${label} line 1\n${label} line 20`, sources: [{ filename: `${label}.pdf`, file_role: 'main' }] }],
            })),
          }],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'h'.repeat(32)} />)

    const authorButton = await screen.findByRole('button', { name: '展开 作者' })
    const journalButton = screen.getByRole('button', { name: '展开 期刊' })
    const abstractButton = screen.getByRole('button', { name: '展开 摘要' })
    fireEvent.click(authorButton)
    fireEvent.click(journalButton)
    fireEvent.click(abstractButton)

    expect(screen.getByRole('button', { name: '收起 作者' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: '收起 期刊' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: '收起 摘要' })).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(screen.getByText(/期刊 line 20/))
    expect(screen.getByRole('button', { name: '收起 期刊' })).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(screen.getByRole('button', { name: '收起 期刊' }))
    expect(screen.getByRole('button', { name: '展开 期刊' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: '收起 作者' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: '收起 摘要' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('期刊.pdf · 正文')).toBeInTheDocument()
  })

  it('切换上传任务后重置字段展开状态并支持键盘操作', async () => {
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(240)
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const taskId = String(input).split('/').at(-2)
      return new Response(JSON.stringify({
        ok: true,
        data: {
          status: 'reading', stage: 'reading', files: [], chunks: [],
          form_preview: {
            status: 'updating', read_only: true, groups: [{
              id: 'bibliography', label: '基本信息', fields: [{
                path: 'paper.authors', label: '作者', state: 'filled',
                candidates: [{ value: 'Author 1\nAuthor 20', sources: [{ filename: `${taskId}.pdf`, file_role: 'main' }] }],
              }],
            }],
          },
          summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
        },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))
    const user = userEvent.setup()
    const firstTaskId = 'i'.repeat(32)
    const secondTaskId = 'j'.repeat(32)
    const { rerender } = render(<UploadParsingDetail taskId={firstTaskId} />)

    const firstButton = await screen.findByRole('button', { name: '展开 作者' })
    firstButton.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: '收起 作者' })).toHaveAttribute('aria-expanded', 'true')
    await user.keyboard(' ')
    expect(screen.getByRole('button', { name: '展开 作者' })).toHaveAttribute('aria-expanded', 'false')
    await user.keyboard(' ')
    expect(screen.getByRole('button', { name: '收起 作者' })).toHaveAttribute('aria-expanded', 'true')

    rerender(<UploadParsingDetail taskId={secondTaskId} />)

    expect(await screen.findByText(`${secondTaskId}.pdf · 正文`)).toBeVisible()
    const secondButton = screen.getByRole('button', { name: '展开 作者' })
    expect(secondButton).toHaveAttribute('aria-expanded', 'false')
    expect(document.getElementById(secondButton.getAttribute('aria-controls') || '')).toBeInTheDocument()
  })

  it('布局变化后重新判断字段卡片是否溢出', async () => {
    let measuredHeight = 80
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(() => measuredHeight)
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        form_preview: {
          status: 'updating', read_only: true, groups: [{
            id: 'bibliography', label: '基本信息', fields: [{
              path: 'paper.authors', label: '作者', state: 'filled',
              candidates: [{ value: 'Author 1\nAuthor 2', sources: [] }],
            }],
          }],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'k'.repeat(32)} />)

    expect(await screen.findByText(/Author 2/)).toBeVisible()
    expect(screen.queryByRole('button', { name: '展开 作者' })).not.toBeInTheDocument()

    measuredHeight = 240
    fireEvent(window, new Event('resize'))

    expect(await screen.findByRole('button', { name: '展开 作者' })).toHaveAttribute('aria-expanded', 'false')

    measuredHeight = 80
    fireEvent(window, new Event('resize'))

    await waitFor(() => expect(screen.queryByRole('button', { name: '展开 作者' })).not.toBeInTheDocument())
  })

  it('轮询追加字段内容时保持已展开状态', async () => {
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(240)
    let requestCount = 0
    vi.stubGlobal('fetch', vi.fn(async () => {
      requestCount += 1
      const authors = requestCount === 1
        ? ['Author 1', 'Author 2']
        : ['Author 1', 'Author 2', 'Author 21']
      return new Response(JSON.stringify({
        ok: true,
        data: {
          status: 'reading', stage: 'reading', files: [], chunks: [],
          form_preview: {
            status: 'updating', read_only: true, groups: [{
              id: 'bibliography', label: '基本信息', fields: [{
                path: 'paper.authors', label: '作者', state: 'filled',
                candidates: [{ value: authors, sources: [{ filename: 'main.pdf', file_role: 'main' }] }],
              }],
            }],
          },
          summary: { status: 'reading', completed: requestCount, total: 2 },
          next_poll_ms: requestCount === 1 ? 250 : null,
        },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))

    render(<UploadParsingDetail taskId={'l'.repeat(32)} />)

    fireEvent.click(await screen.findByRole('button', { name: '展开 作者' }))
    expect(screen.getByRole('button', { name: '收起 作者' })).toHaveAttribute('aria-expanded', 'true')

    expect(await screen.findByText(/Author 21/)).toBeVisible()
    expect(screen.getByRole('button', { name: '收起 作者' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('分类字段等待全文汇总且保留自由材料类型，元数据仍显示真实冲突', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        form_preview: {
          status: 'updating', read_only: true, groups: [
            {
              id: 'bibliography', label: '基本信息', fields: [{
                path: 'paper.title', label: '标题', state: 'conflict', candidates: [
                  { value: 'Main title', sources: [{ filename: 'paper.pdf', file_role: 'main' }] },
                  { value: 'Supplement title', sources: [{ filename: 'supp.pdf', file_role: 'supplementary' }] },
                ],
              }],
            },
            {
              id: 'classification', label: '分类判断', fields: [
                {
                  path: 'paper.paper_type', label: '论文类型', state: 'pending_summary',
                  candidates: [{ value: 'theoretical', sources: [{
                    filename: '2019 Li-Mg-H-孙莹.pdf', file_role: 'main', page_start: 2,
                    quote: 'The phase diagram is constructed through structure searching simulations.',
                  }] }],
                },
                {
                  path: 'sc_type', label: '超导材料类型', state: 'pending_summary',
                  candidates: [{ value: '高压三元氢化物超导体', sources: [{
                    filename: '2019 Li-Mg-H-孙莹.pdf', file_role: 'main', page_start: 1,
                    quote: 'ternary Li2MgH16',
                  }] }],
                },
              ],
            },
          ],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'f'.repeat(32)} />)

    expect((await screen.findAllByText('候选尚未汇总')).length).toBe(2)
    expect(screen.getByText('高压三元氢化物超导体')).toBeVisible()
    expect(screen.getByText('有冲突')).toBeVisible()
    expect(screen.getByText('Main title')).toBeVisible()
    expect(screen.getByText('Supplement title')).toBeVisible()
  })

  it('查看和切换解析任务时仍保留上传入口及其本地文件', async () => {
    const first = task('a'.repeat(32), '第一篇.pdf')
    const second = task('b'.repeat(32), '第二篇.pdf')
    seedAuthenticatedUser()
    localStorage.setItem('scwiki_active_upload_task:7', first.task_id)
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      let body: unknown = { ok: true }
      if (url === '/api/auth/me') body = { user: authenticatedUser }
      else if (url === '/api/upload-tasks') body = { ok: true, data: [first, second] }
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
    const stickyTaskActions = screen.getByRole('region', { name: '当前解析任务操作' })
    expect(stickyTaskActions).toHaveStyle({
      position: 'sticky',
      top: '80px',
    })
    expect(stickyTaskActions.closest('.MuiCard-root')).toHaveStyle({ overflow: 'visible' })

    fireEvent.click(screen.getByRole('button', { name: '收起当前解析详情' }))

    expect(await screen.findByRole('button', { name: '查看 第二篇.pdf 的解析详情' })).toBeVisible()
    expect(screen.getByText('待上传.pdf')).toBeVisible()
    expect(screen.queryByRole('region', { name: '当前解析任务操作' })).not.toBeInTheDocument()
  })
})
