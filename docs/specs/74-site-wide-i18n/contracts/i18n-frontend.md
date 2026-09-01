# 前端契约：语言上下文、文案字典与切换控件

**GitHub Issue**：[#74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74)

**日期**：2026-09-01

**Spec**：[../spec.md](../spec.md)　**决策依据**：[../research.md](../research.md)

本文件定义前端 i18n 基建的对内契约。Issue #75 与 #76 的新增文案依赖本契约，因此它在本 Feature 中必须先行稳定。

## F1：LanguageContext 对外接口

`frontend/src/context/LanguageContext.tsx`

```ts
export type Lang = 'zh' | 'en'

export interface LanguageState {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

export const useLanguage: () => LanguageState
export const LanguageProvider: React.FC<{ children: React.ReactNode }>
```

**Provider 位置**：`frontend/src/main.tsx` 中包在 `AuthProvider` 外层。理由是语言影响 `AuthDialog` 等认证界面的文案，而认证状态不影响语言。

```tsx
<ThemeProvider theme={theme}>
  <CssBaseline />
  <BrowserRouter>
    <LanguageProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </LanguageProvider>
  </BrowserRouter>
</ThemeProvider>
```

**默认值**：`lang` 初值为 `'zh'`（FR-003）。

## F2：`t()` 的解析规则

| 情形 | 行为 |
| --- | --- |
| 键存在于当前语言字典 | 返回对应文案 |
| 键缺失于当前语言但存在于中文字典 | 返回中文文案（保证界面不出现空白或裸键） |
| 键在两个字典都缺失 | 返回键名本身；静态字典缺键由 TypeScript 类型检查拦截 |
| 传入 `vars` | 按 `{name}` 占位符做字符串替换 |

**插值示例**：

```ts
// zh: { 'upload.limit': '每个最大 {size} MB · 同时上传最多 {count} 个' }
t('upload.limit', { size: 50, count: 3 })
// → '每个最大 50 MB · 同时上传最多 3 个'
```

**不支持**：复数规则、日期与数字本地化格式、富文本嵌套组件插值。需要在文案中嵌入组件时，把文案拆成多段分别取值（范围外事项已记录不做地区格式化）。

## F3：文案字典结构

```text
frontend/src/i18n/
├── index.ts          # 聚合导出、Lang 类型、字典类型定义
├── zh/
│   ├── common.ts     # 通用：确认、取消、保存、删除、加载中、暂无数据
│   ├── nav.ts        # 侧边导航与顶栏
│   ├── enums.ts      # 固定枚举标签（R2）
│   ├── account.ts    # 登录注册、账户中心
│   ├── upload.ts     # 上传页与校对编辑器
│   ├── admin.ts      # 管理员与超管工作台
│   ├── search.ts     # 探索页
│   ├── share.ts      # 社区页与图表
│   ├── news.ts       # 快讯
│   ├── paperDetail.ts# 论文详情
│   ├── rag.ts        # 对话
│   ├── kg.ts         # 脉络（知识图谱）
│   └── tcPredict.ts  # 预测
└── en/               # 与 zh 同名同结构
```

**分文件而非单文件**：约 2400 条文案集中在一个文件会使冲突与检索都困难；按功能域切分与 `frontend/src/pages/` 的模块边界对齐。

**键名约定**：`<域>.<语义>`，全小写点分，例如 `admin.review.submit`、`upload.dropzone.hint`。不使用中文原文作为键——中文文案修订时键名会跟着变，破坏稳定性。

**类型约束**：`index.ts` 以中文字典推导字典类型，英文字典声明为同一类型，使英文缺键在 `tsc -b` 阶段暴露（R1）。

## F4：枚举标签契约

`frontend/src/i18n/{zh,en}/enums.ts` 按 `value` 提供标签，覆盖七类枚举：

| 枚举 | 值来源 | 现有中文标签位置 |
| --- | --- | --- |
| 材料维度 | 后端 `material_dimensionalities[].value` | `frontend/src/lib/classifications.ts:36-44` |
| 晶系 | `CRYSTAL_SYSTEM_OPTIONS[].value` | `frontend/src/components/UploadTaskEditor.tsx:74-83` |
| Tc 方法 | `TC_METHOD_OPTIONS[].value` | `frontend/src/components/UploadTaskEditor.tsx:56-65` |
| 论文类型 | `PAPER_TYPE_OPTIONS[].value` | `frontend/src/components/UploadTaskEditor.tsx:44-49` |
| 超导类型 | `SUPERCONDUCTOR_KIND_OPTIONS[].value` | `frontend/src/components/UploadTaskEditor.tsx:51-54` |
| 审核状态 | `pending`/`approved`/`rejected`/`needs_revision` | `frontend/src/components/PaperEditView.tsx:16-18` |
| 用户角色 | `user`/`admin`/`superadmin` | `frontend/src/components/AppShell.tsx:18` |

**硬约束**：枚举的 `value` 是接口契约的一部分，只有标签跟随语言变化（FR-008）。

**后端返回的 `material_dimensionalities[].name` 被忽略**：该键仍是中文，前端改为按 `value` 查本地字典。这样避免后端承担语言协商（R2），也使该下拉在两种语言下都正确。

## F5：分类家族名的语言选取

材料家族与结构家族名不进文案字典（它们是数据而非界面文案），由统一取名函数处理：

```ts
// frontend/src/lib/classifications.ts
export function familyName(term: { name_zh?: string; name_en?: string; name?: string }, lang: Lang): string
```

| 语言 | 取值优先级 |
| --- | --- |
| `zh` | `name_zh` → `name` |
| `en` | `name_en`（非空）→ `name_zh` → `name` |

英文缺失回退中文名（FR-010），而非留空。`name` 作为末位兜底，兼容尚未升级的响应形态。

## F6：语言切换控件

**位置**：`frontend/src/components/AppShell.tsx` 顶栏，用户头像左侧（FR-001）。未登录状态下位于登录按钮左侧。

**形态**：两段式按钮组，`CH` 与 `EN` 并列，当前语言高亮。

**无障碍要求**：

- 控件容器 `role="group"`，带 `aria-label`（随语言变化）。
- 每个按钮 `aria-pressed={当前语言 === 该按钮语言}`，供读屏播报当前状态（FR-002）。
- 两个按钮均可键盘聚焦，具备可见焦点环。
- 仅靠颜色高亮不足以表达状态，`aria-pressed` 是必需项而非可选增强。

**与 Issue #73 的位置协调**：#73 的 AI 供应商切换控件位于本控件左侧，两者互不重叠（Spec 假设与依赖已记录）。

## F7：语言偏好持久化

| 项 | 值 |
| --- | --- |
| 存储 | `localStorage` |
| 键名 | `sc-wiki.language` |
| 值 | `'zh'` 或 `'en'` |

**读取失败或值非法**：回退 `'zh'`，不抛错（FR-006）。读写均包裹 try/catch——隐私模式或配额耗尽时 `localStorage` 存取会抛异常，未捕获会导致白屏。

**写入失败**：不阻断切换。`lang` 状态已更新使当前会话生效，仅跨会话不保持。

## F8：叙述字段不参与语言切换

六个叙述字段（`summary`、`keywords_tags`、`methodology`、`key_finding`、`research_motivation`、`knowledge_graph_title`）统一以英文存储，**不随 `lang` 变化**（FR-014）。

| 语言 | 渲染 |
| --- | --- |
| `zh` | 展示字段的英文内容，按既有空态规则处理 |
| `en` | 展示同一份英文内容 |

**展示层无语言分支**：这些字段不需要按 `lang` 取值，也没有回退规则——它们只有一份内容。组件沿用改动前的渲染路径即可。

**与 F5 家族名的差异**：分类家族名有中英两个名字，因此需要 `familyName(term, lang)` 按语言取值并在英文缺失时回退中文（FR-010）。叙述字段没有语言变体，不存在取值与回退问题。这是英文界面下唯一允许出现中文的情形（自建家族的中文名回退）。

**管理员编辑**：单栏编辑英文内容（FR-018）。界面文案跟随 `lang`，字段内容始终是英文。

## F9：测试目录登记

新增前端测试文件必须放入 `vitest.config.ts` 的 `include` 白名单已覆盖的目录，或同步向该白名单追加新目录。

**原因**：`include` 是逐目录白名单而非 `tests/**`。未登记目录下的 `.test.tsx` 会被静默跳过——不报错、不计数，从输出看不出漏测（`vitest.config.ts` 内注释已明确警告）。

**本 Feature 的测试落点**：语言切换与双语展示测试放入 `tests/02_identity_governance/`（顶栏与账户相关，目录已登记）与 `tests/03_data_search_and_database_discovery/`（论文详情展示，目录已登记），避免新建目录带来的漏测风险。
