# 技术研究：删除操作的级联删除实现

**日期**：2026-08-31

**相关文档**：[spec.md](spec.md) | [plan.md](plan.md)

## 决策1：应用层级联删除 vs 数据库外键 CASCADE

###选择：应用层级联删除

**理由**：
1. **外部服务清理**：需要清理 Qdrant 和 Neo4j，数据库外键无法触发应用逻辑
2. **差异化处理**：`upload_tasks` 需要保留记录但清空 `paper_id`，`superconductors` 需要保留，无法用统一的 CASCADE 规则
3. **审计需求**：未来可能需要记录删除日志，应用层实现更灵活
4. **错误处理**：可以捕获每个删除步骤的错误，提供详细的失败信息

**已拒绝方案**：
- **数据库 `ON DELETE CASCADE`**：无法执行自定义逻辑，无法区分保留和删除
- **存储过程**：Go + MySQL 环境下存储过程维护成本高，且无法调用外部 HTTP 服务

**权衡**：
- 优点：灵活、可控、可扩展
- 缺点：代码量较多，需要手动维护删除顺序

## 决策2：事务边界的划分

### 选择：MySQL 删除使用事务，外部清理在事务外异步执行

**理由**：
1. **数据一致性**：MySQL 删除必须原子性，避免部分删除导致孤儿数据
2. **失败恢复**：Qdrant/Neo4j 清理失败时，MySQL 数据已物理删除无法恢复，强制回滚会导致更严重的不一致
3. **性能考虑**：外部服务调用耗时较长，放入事务会长时间锁表
4. **最终一致性**：Qdrant/Neo4j 清理失败可以通过后台任务补偿，不影响核心删除功能

**实现方案**：
```go
func CascadeDeletePaper(paperID uint) error {
    // 阶段1：MySQL 删除（事务保证）
    err := database.DB.Transaction(func(tx *gorm.DB) error {
        // 删除所有关联表
        return cascadeDeleteInDB(tx, paperID)
    })
    if err != nil {
        return fmt.Errorf("数据库删除失败: %w", err)
    }
    
    // 阶段2：外部清理（best-effort，失败记录日志）
    if err := cleanQdrant(paperID); err != nil {
        log.Printf("警告: paper %d 的 Qdrant 清理失败: %v", paperID, err)
    }
    if err := cleanNeo4j(paperID); err != nil {
        log.Printf("警告: paper %d 的 Neo4j 清理失败: %v", paperID, err)
    }
    
    return nil
}
```

**已拒绝方案**：
- **全部放入分布式事务**：Go 生态缺乏成熟的分布式事务框架，Qdrant/Neo4j 不支持两阶段提交
- **先清理外部再删除 MySQL**：外部清理失败会阻塞删除，且 MySQL 数据仍存在时重复清理外部服务会混乱

**权衡**：
- 优点：实现简单，失败率低，性能好
- 缺点：可能出现短暂的不一致（MySQL 已删除但 Qdrant/Neo4j 仍有数据），需要补偿机制

## 决策3：删除顺序的确定

### 选择：按外键依赖的逆序删除

**依赖关系分析**（基于 GORM 模型）：
```text
papers (主表)
  ├── key_properties         (paper_id 外键)
  ├── material_states        (paper_id 外键)
  │   ├── tc_results         (material_state_id 外键)
  │   ├── calculation_contexts
  │   ├── experimental_contexts
  │   └── structures
  ├── paper_chunks           (paper_id 外键)
  ├── paper_evidences        (paper_id 外键)
  └── paper_review_events    (paper_id 外键)
```

**删除顺序**：
1. `paper_evidences`, `paper_chunks`, `paper_review_events`（叶子节点，无依赖）
2. `tc_results`, `calculation_contexts`, `experimental_contexts`（依赖 `material_states`）
3. `structures`（依赖 `material_states`）
4. `material_states`（依赖 `papers`）
5. `key_properties`（依赖 `papers`）
6. `papers`（最后删除）

**注意事项**：
- `superconductors` 不删除（可能被多篇论文引用）
- `upload_tasks` 不删除，只清空 `paper_id`

**验证方式**：
- 单元测试：创建完整的论文数据，执行删除，验证所有表记录数为 0
- 集成测试：使用真实数据库，验证外键约束不报错

## 决策4：批量删除的实现策略

### 选择：循环调用单个删除，捕获单个失败

**理由**：
1. **独立性**：每篇论文的删除独立，单个失败不应影响其他论文
2. **外部清理**：每篇论文需要独立调用 Qdrant/Neo4j 清理端点
3. **错误定位**：可以精确报告哪些论文删除失败

**实现方案**：
```go
func BatchDelete(c *gin.Context) {
    var body struct {
        PaperIDs []uint `json:"paper_ids"`
    }
    c.ShouldBindJSON(&body)
    
    failedIDs := []uint{}
    for _, id := range body.PaperIDs {
        if err := CascadeDeletePaper(id); err != nil {
            log.Printf("批量删除: paper %d 失败: %v", id, err)
            failedIDs = append(failedIDs, id)
        }
    }
    
    if len(failedIDs) > 0 {
        c.JSON(http.StatusPartialContent, gin.H{
            "message": "部分删除失败",
            "failed_ids": failedIDs,
        })
        return
    }
    
    cache.FlushPattern("chart:*")
    cache.FlushPattern("search:*")
    cache.FlushPattern("community:contributions:*")
    c.JSON(http.StatusOK, gin.H{"message": "批量删除完成"})
}
```

**已拒绝方案**：
- **单个批量 SQL**：无法为每篇论文独立清理外部服务，一个失败导致全部回滚
- **并发删除**：可能导致数据库锁竞争，且错误处理复杂

**权衡**：
- 优点：逻辑清晰，错误处理简单
- 缺点：性能较批量 SQL 慢（但删除操作频率低，可接受）

## 决策5：Python 内部端点的设计

### 选择：创建独立的内部管理端点，不复用公开 API

**理由**：
1. **权限隔离**：内部端点只接受来自 Go 服务的请求，不暴露给前端
2. **契约稳定**：公开 API 可能因前端需求变化，内部端点只服务于删除逻辑
3. **简化实现**：不需要复杂的权限检查和参数验证

**端点设计**：
- `DELETE /internal/papers/{paper_id}/vectors`：删除 Qdrant 向量
- `DELETE /internal/papers/{paper_id}/graph`：删除 Neo4j 节点

**安全措施**：
- 使用 JWT token 认证（Go 服务携带管理员 token）
- 仅在内部网络访问（Docker Compose 内部通信）
- 添加 IP 白名单检查（可选）

**已拒绝方案**：
- **复用现有 RAG 端点**：现有端点设计为用户操作，权限和参数校验不适合内部调用
- **直接暴露 Qdrant/Neo4j**：Go 需要引入 qdrant-client 和 neo4j-driver，增加依赖复杂度

## 决策6：错误处理策略

### 选择：区分可恢复错误和不可恢复错误

**错误分类**：
1. **可恢复错误**：论文不存在（404）、权限不足（403）
   - 处理：返回明确错误，不执行删除
   
2. **部分失败**：MySQL 删除成功但外部清理失败
   - 处理：返回成功但记录警告日志，前端显示提示
   
3. **完全失败**：MySQL 删除失败（事务回滚）
   - 处理：返回 500 错误，前端提示重试

**实现方案**：
```go
type DeletionError struct {
    Code    string `json:"code"`
    Message string `json:"message"`
    PaperID uint   `json:"paper_id,omitempty"`
}

func CascadeDeletePaper(paperID uint) *DeletionError {
    // 检查论文是否存在
    var paper models.Paper
    if err := database.DB.First(&paper, paperID).Error; err != nil {
        if errors.Is(err, gorm.ErrRecordNotFound) {
            return &DeletionError{Code: "paper_not_found", Message: "论文不存在", PaperID: paperID}
        }
        return &DeletionError{Code: "database_error", Message: err.Error(), PaperID: paperID}
    }
    
    // MySQL 删除
    if err := database.DB.Transaction(func(tx *gorm.DB) error {
        return cascadeDeleteInDB(tx, paperID)
    }); err != nil {
        return &DeletionError{Code: "deletion_failed", Message: err.Error(), PaperID: paperID}
    }
    
    // 外部清理（失败记录日志但不返回错误）
    cleanExternal(paperID)
    
    return nil
}
```

## 决策7：测试策略

### 选择：单元测试 + 集成测试 + 手动测试

**单元测试**（Go）：
- 测试 `cascadeDeleteInDB` 的删除顺序
- 测试事务回滚（模拟中途失败）
- 测试 `upload_tasks` 的 `paper_id` 清空逻辑
- 测试错误分类和返回值

**集成测试**（Go + Python + MySQL + Qdrant + Neo4j）：
- 测试完整删除流程：创建论文 → 删除 → 验证所有表为空
- 测试批量删除：创建多篇论文 → 批量删除 → 验证统计数据更新
- 测试外部清理：验证 Qdrant 和 Neo4j 数据被删除

**手动测试**：
- 前端删除操作，验证用户体验
- 删除已通过审核的论文，验证图表数据更新
- 删除多次上传的重复论文，验证贡献统计正确

**测试数据准备**：
- 使用 GORM 的 `Create` 方法创建完整的论文数据（包含材料状态、Tc 结果等）
- 使用 Python 脚本将论文同步到 Qdrant 和 Neo4j

## 技术风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 外键约束导致删除失败 | 无法删除论文 | 仔细分析外键依赖，按正确顺序删除；集成测试验证 |
| Qdrant/Neo4j 清理失败 | 孤儿数据残留 | 记录失败日志，提供后台补偿任务 |
| 大量论文批量删除超时 | 请求超时 | 限制批量删除数量（< 100），前端分批操作 |
| 事务长时间锁表 | 阻塞其他操作 | 只在 MySQL 删除时使用事务，外部清理异步执行 |
| 删除后贡献统计不更新 | 排行榜数据错误 | 删除后刷新 `community:contributions:*` 缓存 |

## 未来改进方向

1. **补偿任务**：定期扫描 MySQL 中已删除但 Qdrant/Neo4j 仍存在的数据，自动清理
2. **软删除选项**：为误删场景提供恢复机制（当前不实现）
3. **批量优化**：使用批量 SQL 提高删除性能（当删除频率上升时考虑）
4. **审计日志**：记录删除操作的执行人、时间和原因（当前不实现）
