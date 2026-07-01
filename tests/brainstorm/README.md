# 头脑风暴独立测试

不经过普通问答管线，直接测试 5 阶段流程。

## 运行

```bash
# 交互式
python -m tests.brainstorm.test_flow

# 直接指定研究方向
python -m tests.brainstorm.test_flow "我想研究笼状氢化物"
```

## 文件

- `test_flow.py` - 完整 5 阶段交互测试
- 每个阶段打印 LLM 回复 → 等待用户输入 → 推进下一阶段
- 输入「退出」随时终止
