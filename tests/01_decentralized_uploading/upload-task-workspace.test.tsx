import React from 'react'
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import MultiFileUploadPanel from '../../frontend/src/components/MultiFileUploadPanel'
import UploadParsingDetail from '../../frontend/src/components/UploadParsingDetail'
import UploadPage from '../../frontend/src/pages/UploadPage'
import { AuthProvider } from '../../frontend/src/context/AuthContext'

vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: ({ data, format }: { data: string; format: string }) => (
    <div data-testid="structure-viewer" data-format={format}>{data}</div>
  ),
}))

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

  it('把 .vasp 结构文件作为 POSCAR 附件接受', () => {
    render(<MultiFileUploadPanel onCreated={vi.fn()} />)

    const main = new File(['paper'], 'paper.pdf', { type: 'application/pdf' })
    const structure = new File(['POSCAR'], 'Li2MgH16.vasp', { type: 'text/plain' })
    fireEvent.drop(screen.getByLabelText('拖拽或选择论文文件'), {
      dataTransfer: { files: [main, structure] },
    })

    expect(screen.getByText('Li2MgH16.vasp')).toBeVisible()
    expect(screen.queryByText(/Li2MgH16\.vasp：仅支持/)).not.toBeInTheDocument()
  })

  it('分段尚未生成时仍显示临时表单和解析证据入口', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'extracting',
        stage: 'extracting',
        files: [{ file_id: 'main', role: 'main', original_filename: 'paper.pdf', extraction_status: 'processing' }],
        chunks: [],
        summary: { status: 'extracting', completed: 0, total: 0 },
        next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'c'.repeat(32)} />)

    expect(await screen.findByRole('tab', { name: 'AI 临时表单' })).toBeVisible()
    expect(screen.getByRole('tab', { name: '分段解析与证据' })).toBeVisible()
    expect(await screen.findByText('只读预览')).toBeVisible()
    expect(screen.getByText('正在提取论文正文，完成后逐段解析。')).toBeVisible()
    expect(screen.queryByRole('button', { name: '提交审核' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: '分段解析与证据' }))
    expect(screen.getByText('尚未生成分段，正在等待正文提取完成。')).toBeVisible()
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

  it('作者保持单行并可标记通讯作者和共同第一作者', async () => {
    const savedBodies: any[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        const body = JSON.parse(String(init.body))
        savedBodies.push(body)
        return new Response(JSON.stringify({ ok: true, data: body }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        })
      }
      const data = String(input).endsWith('/parsing')
        ? {
            status: 'ready', stage: 'ready', files: [], chunks: [],
            form_preview: { status: 'ready', read_only: false, groups: [] },
            summary: { status: 'completed', completed: 1, total: 1 }, next_poll_ms: null,
          }
        : {
            paper: {
              title: 'Hydride study', authors: ['Ying Sun', 'Jian Lv', 'Hanyu Liu'],
              corresponding_authors: ['Hanyu Liu'], co_first_authors: ['Ying Sun', 'Jian Lv'],
              paper_type: 'review', research_materials: [],
            },
            material_states: [], classification_evidence: [], field_evidence: {},
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'n'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByRole('combobox', { name: '作者' })).toBeInstanceOf(HTMLInputElement)
    expect(screen.getByText('Ying Sun · 共同第一作者')).toBeVisible()
    expect(screen.getByText('Jian Lv · 共同第一作者')).toBeVisible()
    fireEvent.click(screen.getByText('Hanyu Liu · 通讯作者'))
    fireEvent.click(screen.getByRole('menuitem', { name: '共同第一作者' }))
    fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' })
    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))

    await waitFor(() => expect(savedBodies).toHaveLength(1))
    expect(savedBodies[0].paper).toMatchObject({
      authors: ['Ying Sun', 'Jian Lv', 'Hanyu Liu'],
      corresponding_authors: ['Hanyu Liu'],
      co_first_authors: ['Ying Sun', 'Jian Lv', 'Hanyu Liu'],
    })
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

  it('按材料状态显示压强与空间群，并以新契约保存', async () => {
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
    expect(screen.queryByRole('textbox', { name: '物相' })).not.toBeInTheDocument()
    expect(screen.getByRole('spinbutton', { name: '压强 (GPa)' })).toHaveValue(300)
    expect(screen.getByRole('combobox', { name: '空间群符号' })).toHaveValue('Fd-3m')
    expect(screen.getByRole('spinbutton', { name: '空间群号' })).toHaveValue(227)
    expect(screen.queryByRole('spinbutton', { name: '电声耦合强度 λ' })).not.toBeInTheDocument()
    expect(screen.queryByRole('spinbutton', { name: '对数声子频率 ωlog (K)' })).not.toBeInTheDocument()
    expect(document.querySelector('input[type="file"]')?.getAttribute('accept')).toContain('.vasp')

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
    expect(savedBodies[0]).not.toHaveProperty('material_states.0.phase_label')
  })

  // 重度交互用例：并行下实测约 4.4s，默认 5s 上限余量不足
  it('晶体结构只在所属材料状态内显示且材料状态列表占满页面', { timeout: 15000 }, async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const data = String(input).endsWith('/parsing')
        ? {
            status: 'ready', stage: 'ready', files: [], chunks: [],
            form_preview: { status: 'ready', read_only: false, groups: [] },
            summary: { status: 'completed', completed: 1, total: 1 }, next_poll_ms: null,
          }
        : {
            paper: {
              title: 'Two-state hydride study', authors: [], paper_type: 'theoretical',
              theoretical_subtype: 'calculation', research_materials: ['Li2MgH16'],
            },
            material_states: [
              {
                material: 'Li2MgH16', pressure_value_gpa: 300, state_kind: 'theoretical',
                calculation_context: {}, tc_results: [], properties: [],
              },
              {
                material: 'Li2MgH16', pressure_value_gpa: 250, state_kind: 'theoretical',
                calculation_context: {}, tc_results: [], properties: [],
              },
            ],
            structure_candidates: [{
              candidate_id: 'structure-state-1', material_state_ref: 'material_states[0]',
              status: 'valid', confirmation: 'unreviewed',
              sources: [{ filename: 'Li2MgH16.vasp' }],
              validation: { atom_count: 2, elements: ['Li', 'H'], volume: 20 },
              representations: {
                conventional: {
                  cif: { text: 'data_conventional' },
                  poscar: { text: 'conventional POSCAR' },
                },
                primitive: {
                  cif: { text: 'data_primitive' },
                  poscar: { text: 'primitive POSCAR' },
                },
              },
            }],
            classification_evidence: [], field_evidence: {},
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'o'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByText('材料状态 #1')).toBeVisible()
    expect(screen.getByText('材料状态 #2')).toBeVisible()
    expect(screen.getAllByTestId('structure-viewer')).toHaveLength(1)
    expect(screen.getByTestId('structure-viewer')).toHaveTextContent('data_conventional')
    expect(screen.getByTestId('material-states-list')).toHaveStyle({ width: '100%' })
    expect(screen.queryByRole('heading', { name: '晶体结构' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下载结构' })).toBeVisible()
    expect(screen.getByText('当前显示：惯用胞 · CIF')).toBeVisible()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '晶胞表示' }))
    fireEvent.click(screen.getByRole('option', { name: '原胞' }))
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '结构格式' }))
    fireEvent.click(screen.getByRole('option', { name: 'POSCAR' }))

    expect(screen.getByTestId('structure-viewer')).toHaveTextContent('primitive POSCAR')
    expect(screen.getByTestId('structure-viewer')).toHaveAttribute('data-format', 'vasp')
    expect(screen.getByText('当前显示：原胞 · POSCAR')).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: '采用此结构' }))
    expect(screen.getByText('已采用'))
    fireEvent.click(screen.getByRole('button', { name: '恢复为待确认' }))
    expect(screen.getByText('待确认')).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: '不采用' }))
    expect(screen.getByText('已不采用')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: '恢复为待确认' }))
    expect(screen.getByRole('button', { name: '采用此结构' })).toBeVisible()
    expect(screen.getByRole('button', { name: '不采用' })).toBeVisible()
  })

  it('分段解析页签并列显示各分段来源与解析结果', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [
          {
            chunk_id: 'main:0', filename: 'paper.pdf', file_role: 'main', section: 'Title',
            page_start: 1, page_end: 1, status: 'completed', result: { metadata: { title: 'Main title' } },
          },
          {
            chunk_id: 'supp:0', filename: 'supp.pdf', file_role: 'supplementary', section: 'Cover',
            page_start: 2, page_end: 2, status: 'completed', result: { metadata: { title: 'Supplement title' } },
          },
        ],
        summary: { status: 'reading', completed: 2, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'e'.repeat(32)} />)

    expect(await screen.findByText('只读预览')).toBeVisible()
    expect(screen.queryByText('有冲突')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: '分段解析与证据' }))
    expect(screen.getByText('分段进度 · 2/2')).toBeVisible()
    expect(screen.getByText('paper.pdf · Title')).toBeVisible()
    expect(screen.getByText('supp.pdf · Cover')).toBeVisible()
    expect(screen.getByText('第 1 页')).toBeVisible()
    expect(screen.getByText('第 2 页')).toBeVisible()

    fireEvent.click(screen.getByText('paper.pdf · Title'))
    expect(await screen.findByText(/Main title/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('supp.pdf · Cover'))
    expect(await screen.findByText(/Supplement title/)).toBeInTheDocument()
  })

  it('只读预览展示局部草稿字段但不提供编辑操作', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        partial_draft: {
          paper: { title: 'Li2MgH16 study', authors: ['Ying Sun'], paper_type: 'theoretical' },
          material_states: [{ material: 'Li2MgH16', tc_results: [], properties: [] }],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'g'.repeat(32)} />)

    expect(await screen.findByText('只读预览')).toBeVisible()
    expect(screen.getByText('AI 分段阅读中 1/2，字段随分段完成逐步点亮。')).toBeVisible()
    expect(screen.getByLabelText('标题')).toHaveValue('Li2MgH16 study')
    expect(screen.getByText('Ying Sun')).toBeVisible()
    expect(screen.getByText('材料状态 #1')).toBeVisible()
    expect(screen.getByLabelText('材料')).toHaveValue('Li2MgH16')
    expect(screen.queryByRole('button', { name: '提交审核' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '立即保存' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '展开 作者' })).not.toBeInTheDocument()
  })

  it('只读预览中字段内容可见且点击不改变', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        partial_draft: {
          paper: { title: 'Draft title', authors: [], keywords_tags: ['超导', '高压'] },
          material_states: [],
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'h'.repeat(32)} />)

    expect(await screen.findByText('只读预览')).toBeVisible()
    expect(screen.getByLabelText('标题')).toHaveValue('Draft title')
    expect(screen.getByLabelText('关键词（每行一个）')).toHaveValue('超导\n高压')

    fireEvent.click(screen.getByLabelText('关键词（每行一个）'))
    fireEvent.click(screen.getByLabelText('标题'))

    expect(screen.getByLabelText('关键词（每行一个）')).toHaveValue('超导\n高压')
    expect(screen.getByLabelText('标题')).toHaveValue('Draft title')
    expect(screen.queryByRole('button', { name: '提交审核' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '展开 作者' })).not.toBeInTheDocument()
  })

  it('切换上传任务后只读预览重置为新任务的局部草稿', async () => {
    const firstTaskId = 'i'.repeat(32)
    const secondTaskId = 'j'.repeat(32)
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (!url.endsWith('/parsing')) {
        return new Response(JSON.stringify({ ok: true }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        })
      }
      const taskId = url.split('/').at(-2)
      return new Response(JSON.stringify({
        ok: true,
        data: {
          status: 'reading', stage: 'reading', files: [], chunks: [],
          partial_draft: {
            paper: { title: taskId === firstTaskId ? '第一篇草稿标题' : '第二篇草稿标题', authors: [] },
            material_states: [],
          },
          summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
        },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))

    const { rerender } = render(<UploadParsingDetail taskId={firstTaskId} />)

    expect(await screen.findByLabelText('标题')).toHaveValue('第一篇草稿标题')
    expect(screen.getByText('只读预览')).toBeVisible()

    rerender(<UploadParsingDetail taskId={secondTaskId} />)

    await waitFor(() => expect(screen.getByLabelText('标题')).toHaveValue('第二篇草稿标题'))
    expect(screen.getByText('只读预览')).toBeVisible()
  })

  it('布局变化后重新判断 AI 解释是否溢出', async () => {
    let measuredHeight = 80
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(() => measuredHeight)
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const data = String(input).endsWith('/parsing')
        ? {
            status: 'ready', stage: 'ready', files: [], chunks: [],
            summary: { status: 'completed', completed: 1, total: 1 }, next_poll_ms: null,
          }
        : {
            paper: {
              title: 'Hydride study', authors: [], paper_type: 'review',
              methodology: ['CALYPSO群智能结构搜索'],
            },
            material_states: [], classification_evidence: [],
            field_evidence: {
              methodology: [{
                section: 'Supplementary Material', page: 2,
                quote: 'The simulations were performed with several first-principles methods.',
              }],
            },
            ai_original: {
              paper: {
                methodology: Array.from({ length: 20 }, (_, index) => `CALYPSO群智能结构搜索 ${index + 1}`),
              },
            },
          }
      return new Response(JSON.stringify({ ok: true, data }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    }))

    render(<UploadParsingDetail taskId={'k'.repeat(32)} onSubmitted={vi.fn()} />)

    expect(await screen.findByText(/AI 建议：CALYPSO群智能结构搜索/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '展开 研究方法（每行一项）的 AI 解释' })).not.toBeInTheDocument()

    measuredHeight = 240
    await waitFor(() => {
      fireEvent(window, new Event('resize'))
      expect(screen.getByRole('button', { name: '展开 研究方法（每行一项）的 AI 解释' })).toBeInTheDocument()
    })

    measuredHeight = 80
    await waitFor(() => {
      fireEvent(window, new Event('resize'))
      expect(screen.queryByRole('button', { name: '展开 研究方法（每行一项）的 AI 解释' })).not.toBeInTheDocument()
    })
  })

  it('轮询更新局部草稿时只读预览实时刷新内容', async () => {
    let parsingRequests = 0
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (!url.endsWith('/parsing')) {
        return new Response(JSON.stringify({ ok: true }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        })
      }
      parsingRequests += 1
      const paper = parsingRequests === 1
        ? { title: 'First title', authors: [] }
        : { title: 'First title', authors: [], keywords_tags: ['超导'] }
      return new Response(JSON.stringify({
        ok: true,
        data: {
          status: 'reading', stage: 'reading', files: [], chunks: [],
          partial_draft: { paper, material_states: [] },
          summary: { status: 'reading', completed: Math.min(parsingRequests, 2), total: 2 },
          next_poll_ms: parsingRequests === 1 ? 250 : null,
        },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))

    render(<UploadParsingDetail taskId={'l'.repeat(32)} />)

    expect(await screen.findByLabelText('标题')).toHaveValue('First title')
    expect(screen.getByText('只读预览')).toBeVisible()

    await waitFor(
      () => expect(screen.getByLabelText('关键词（每行一个）')).toHaveValue('超导'),
      { timeout: 3000 },
    )
    expect(screen.getByText('只读预览')).toBeVisible()
    expect(screen.getByText('AI 分段阅读中 2/2，字段随分段完成逐步点亮。')).toBeVisible()
  })

  it('分段阅读中的只读预览展示局部草稿的分类与材料状态', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      data: {
        status: 'reading', stage: 'reading', files: [], chunks: [],
        partial_draft: {
          paper: { title: 'Main title', authors: [], paper_type: 'unknown' },
          material_states: [{
            material: 'Li2MgH16',
            material_family: { id: null, name: '高压三元氢化物超导体', status: 'pending' },
            tc_results: [], properties: [],
          }],
          research_motivation: '',
        },
        summary: { status: 'reading', completed: 1, total: 2 }, next_poll_ms: null,
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(<UploadParsingDetail taskId={'f'.repeat(32)} />)

    expect(await screen.findByText('只读预览')).toBeVisible()
    expect(screen.queryByText('候选尚未汇总')).not.toBeInTheDocument()
    expect(screen.getByText('暂不确定')).toBeInTheDocument()
    expect(screen.getByDisplayValue('高压三元氢化物超导体')).toBeInTheDocument()
    expect(screen.getByText('新名称，将在论文审核通过时创建')).toBeInTheDocument()
    expect(screen.getByLabelText('材料')).toHaveValue('Li2MgH16')
    expect(screen.getByLabelText('标题')).toHaveValue('Main title')
    expect(screen.getByLabelText('研究驱动力')).toHaveValue('')
    expect(screen.queryByRole('button', { name: '提交审核' })).not.toBeInTheDocument()
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
