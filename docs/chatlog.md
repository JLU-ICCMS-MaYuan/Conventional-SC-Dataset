data = {answer_rag("笼状氢化物有什么研究方向")}

//对话1.0，阶段1
[
    { "role": "system", "content": "（阶段1的system）," },
    { "role": "user", "content": "笼状氢化物有什么研究方向" + "数据库中关于"笼状氢化物有什么研究方向"的资料{data}"}
]


//对话2.0,阶段2
[
    { "role": "system", "content": "（阶段1的system）" },
    { "role": "user", "content": "笼状氢化物有什么研究方向" + "数据库中关于"笼状氢化物有什么研究方向"的资料{data}"}
    { "role": "assistant", "content": "（对话1.0的回复）" }
]

//对话2.1,阶段2
[
    { "role": "system", "content": "（阶段1的system）" },
    { "role": "user", "content": "笼状氢化物有什么研究方向" + "数据库中关于"笼状氢化物有什么研究方向"的资料{data}"}
    { "role": "assistant", "content": "（对话2.0的回复）" }
    { "role": "user", "content": "我选择 A" }
]

