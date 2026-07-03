"""Mock backend — 返回假数据供 frontend_example 调试 UI。

启动: uvicorn server:app --port 8001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json, time, asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Mock data ──
PAPERS = {
    "1": {"title": "Superconductivity in LaH₁₀ under High Pressure",
          "doi": "10.1103/PhysRevLett.123.117001", "journal": "Physical Review Letters", "year": 2024},
    "2": {"title": "High-Tc Hydride Superconductors: A Review",
          "doi": "10.1093/nsr/nwae047", "journal": "National Science Review", "year": 2024},
    "3": {"title": "Ternary Clathrate Hydrides with Noninteger H/Metal Ratios",
          "doi": "10.1021/jacs.2c01234", "journal": "JACS", "year": 2022},
    "4": {"title": "Substitution Strategies in Binary Hydrides",
          "doi": "10.1103/PhysRevB.105.174501", "journal": "Physical Review B", "year": 2022},
    "5": {"title": "Machine Learning Search for Hydride Superconductors",
          "doi": "10.1038/s41524-022-00844", "journal": "npj Computational Materials", "year": 2022},
}

IDEAS = [
    {
        "title": "尺寸失配诱导的非整数比双笼超导体",
        "fragments": [
            {"paper_id": 3, "quoted_text": "We have found a series of ternary multicage clathrate hydrides with noninteger H/metal ratios by a design principle that emulates the clathrate structures of hydrates and group-14 element frameworks.", "section": "abstract"},
            {"paper_id": 4, "quoted_text": "a common strategy is to consider substitutions of a third element into a known binary hydride, exemplified by the mixed La/Y hydrides recently shown to form.", "section": "discussion"},
        ],
        "reasoning_chain": "利用Mg(小)与La(大)的半径差异，可在150-250 GPa下诱导出不同于二元体系的新笼拓扑。",
        "assumptions": ["Mg可部分取代La进入笼结构", "150-250 GPa压力窗口稳定"],
    }
]

REVIEWS = [
    {
        "flaws": [
            {"severity": "high", "description": "Mg可能优先与H反应形成MgH₂而无法进入笼结构"},
            {"severity": "medium", "description": "未给出具体合成压力窗口和氢源选择"},
        ],
        "feasibility_score": 4,
        "revised_idea": "...",
        "dimensions": {"theory": 4, "synthesis": 2, "measurement": 3},
    }
]

MOCK_ANSWER = """
基于数据库文献，我注意到三个趋势：

1. **三元氢化物数量快速增长**，但多为 DFT 预测，实验验证很少 [PID_1]。
2. **常压下亚稳氢化物的研究开始出现** [PID_2]，表明研究者正在尝试突破高压限制。
3. **机器学习辅助结构搜索**已应用到氢化物领域 [PID_5]，大幅加快了候选材料的发现速度。

你对哪个方向最感兴趣？
"""

EXPLORE_ANSWER = MOCK_ANSWER + """
\n\n基于笼状模板匹配思路，这里有一个具体的研究方案：

<!--IDEA_CARD
{
  "title": "尺寸失配诱导的非整数比双笼超导体",
  "fragments": [
    {"paper_id": 3, "quoted_text": "We have found a series of ternary multicage clathrate hydrides with noninteger H/metal ratios...", "section": "abstract"},
    {"paper_id": 4, "quoted_text": "a common strategy is to consider substitutions of a third element into a known binary hydride...", "section": "discussion"}
  ],
  "reasoning_chain": "利用Mg(小)与La(大)的半径差异，可在150-250 GPa下诱导出不同于二元体系的新笼拓扑。",
  "assumptions": ["Mg可部分取代La进入笼结构", "150-250 GPa压力窗口稳定"]
}
-->

可行性：理论★★★★☆ 合成★★☆☆☆ 测量★★★☆☆
风险：Mg可能优先与H反应形成MgH₂而无法进入笼结构
"""


# ── Routes ──

@app.get("/api/rag/health")
def health():
    return {"available": True, "message": "Mock server ready"}


@app.get("/api/papers/stats/chart-data")
def chart_data():
    return [
        {"x": 100, "y": 150, "type": "theoretical", "year": 2020, "label": "LaH₁₀", "sc_type": "h"},
        {"x": 150, "y": 200, "type": "theoretical", "year": 2021, "label": "YH₆", "sc_type": "h"},
        {"x": 170, "y": 250, "type": "theoretical", "year": 2024, "label": "LaH₁₀", "sc_type": "h"},
        {"x": 120, "y": 100, "type": "experimental", "year": 2022, "label": "H₃S", "sc_type": "h"},
        {"x": 180, "y": 180, "type": "experimental", "year": 2023, "label": "CaH₆", "sc_type": "h"},
    ]


@app.get("/api/papers/stats/user-ranking")
def user_ranking():
    return [{"username": "Alice", "count": 42}, {"username": "Bob", "count": 35}]


@app.get("/api/papers/stats/tc-year")
def tc_year():
    return chart_data()


@app.post("/api/rag/chat/stream")
async def chat_stream(request: dict):
    """模拟流式问答 + 探索模式"""
    question = request.get("question", "")
    explore = request.get("explore", False)

    async def generate():
        steps = [
            ("status", {"action": "routing", "message": "正在分析问题..."}),
            ("inspire_enter", {"session_id": "mock-session", "mode": "gap_detector", "mode_label": "文献缺口探测"}),
            ("inspire_mode", {"mode": "gap_detector", "label": "文献缺口探测", "rationale": "用户在探索新方向"}),
        ] if explore else [
            ("status", {"action": "searching", "message": "正在检索..."}),
        ]

        for event_type, data in steps:
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.3)

        # 流式输出答案
        answer = EXPLORE_ANSWER if explore else MOCK_ANSWER
        for char in answer:
            yield f"event: token\ndata: {json.dumps(char)}\n\n"
            await asyncio.sleep(0.01)

        # 文献卡片
        if explore:
            for idea in IDEAS:
                yield f"event: evidence_card\ndata: {json.dumps(idea, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.2)
            for review in REVIEWS:
                yield f"event: review_verdict\ndata: {json.dumps(review, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.2)

        done_data = {
            "papers": PAPERS,
            "answer": answer,
            "source": "inspire_gap_detector" if explore else "hybrid",
            "top10": [],
            "inspiration": {"current_mode": "gap_detector", "mode_label": "文献缺口探测", "collected_ideas": IDEAS} if explore else None,
        }
        yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
