# 狼人杀 AI 游戏完整逻辑规范（统一版 v1.0）

本规范合并并整合了两轮讨论的全部内容，形成详细、准确且可实施的“AI 狼人杀”游戏统一标准。适用于评测多模型对局、全 AI 自动博弈与前后端联动实现。

实现参考位置：
- 后端（Flask）：[`games/werewolf/backend/app.py`](games/werewolf/backend/app.py:1)
- 前端（React）：[`games/werewolf/frontend/src/App.jsx`](games/werewolf/frontend/src/App.jsx:1)

说明：
- 规范中的 JSON 示例为传输/记录的推荐格式，具体实现可逐步演进，但字段语义与约束应保持一致。
- 当前后端已实现基础状态机（夜/昼、发言、投票）与 history 记录；本文档在保持兼容的前提下扩展角色、消息结构、投票公布、上下文管理与配置等要素。

---

## 目录

1. 概念与范围
2. 配置文件与运行时解析
3. 角色配置与能力说明
4. 游戏状态机与阶段
5. 消息传递协议（AI 输入/输出统一格式）
6. 行为与结果 JSON Schema（建议形状）
7. 投票公布与透明度配置
8. 上下文管理与压缩策略
9. 历史记录（history）与审计字段
10. 评测与统计（可选）
11. 安全、限流与鲁棒性
12. 与现有实现的映射与兼容性
13. 未来扩展（角色、流程、界面）

---

## 1. 概念与范围

- 游戏模式：6–16 名 AI 玩家对局，可选“允许人类旁观或介入（后续扩展）”。默认全 AI，无人类参与。
- 评测目标：同台较量，比较不同大模型/提供商在复杂博弈中的策略、稳定性、可解释性与胜率。
- 前端：React（Vite 开发，已配置代理至 Flask）。
- 后端：Flask 简易房间/状态机服务，暴露 /rooms 与 /config 等 API。
- 秘钥来源：项目根目录 api_keys.json（或兼容旧格式），支持多 Provider 与 player→provider 映射。

---

## 2. 配置文件与运行时解析

### 2.1 api_keys.json（项目根目录）

推荐结构：
```json
{
  "providers": {
    "openai-main": { "api_key": "sk-xxx", "model": "gpt-4", "model_url": null },
    "azure-team":  { "api_key": "az-xxx", "model": "gpt-35", "model_url": "https://..." }
  },
  "player_map": {
    "AI_1": "openai-main",
    "AI_2": "azure-team"
  }
}
```

解析规则（后端）：
- 若存在 `"player_map[<player>] = <provider>"` 且该 provider 存在 `"api_key"`，则对该玩家调用时使用该 api_key。
- 若不存在映射，则回退：providers 中任意第一个 provider 的 api_key；再退：旧字段 `"OPENAI_API_KEY"|"openai"|"api_key"|"apiKey"`；再退：环境变量或空。
- 参考实现：[`get_api_key_for_player(player)`](games/werewolf/backend/app.py:407)

### 2.2 游戏玩家配置 games/werewolf/config.json

推荐结构：
```json
{
  "players": ["AI_1","AI_2","AI_3","AI_4","AI_5","AI_6"],
  "role_preferences": { "AI_1": "seer", "AI_5": "werewolf" },
  "player_map": { "AI_1": "openai-main", "AI_2": "azure-team" }
}
```

- players：6–16 名玩家（建议偶数）。
- role_preferences：若指定则覆盖随机分配；未指定的随机填充。
- player_map：与 api_keys.json 的 player_map 含义相同（前端允许保存任一处；后端解析优先级可配置，默认以 api_keys.json 为准，players.config 作为补充）。

前端可视化编辑：
- Providers 编辑（名称、api_key、model、model_url）与玩家→provider 下拉映射
- 玩家列表与职业偏好配置
- 已实现页面：[`games/werewolf/frontend/src/App.jsx`](games/werewolf/frontend/src/App.jsx:1)

---

## 3. 角色配置与能力说明

### 3.1 角色人数分配（6/8/10/12/16）

```json
{
  "role_distributions": {
    "6_players":  { "werewolf": 2, "villager": 2, "seer": 1, "witch": 1, "hunter": 0, "guard": 0, "idiot": 0, "cupid": 0 },
    "8_players":  { "werewolf": 2, "villager": 3, "seer": 1, "witch": 1, "hunter": 1, "guard": 0, "idiot": 0, "cupid": 0 },
    "10_players": { "werewolf": 3, "villager": 3, "seer": 1, "witch": 1, "hunter": 1, "guard": 1, "idiot": 0, "cupid": 0 },
    "12_players": { "werewolf": 4, "villager": 4, "seer": 1, "witch": 1, "hunter": 1, "guard": 1, "idiot": 0, "cupid": 0 },
    "16_players": { "werewolf": 4, "villager": 6, "seer": 1, "witch": 1, "hunter": 1, "guard": 1, "idiot": 1, "cupid": 1 }
  }
}
```

### 3.2 角色能力说明（语义）

- werewolf（狼队）：
  - night_action: kill（狼队讨论多轮→形成击杀目标）
  - 特性：互认、3 轮讨论、分歧时系统在好人中随机目标；得知是否被女巫救
- seer（预言家）：每晚 reveal 一名玩家的真实身份
- witch（女巫）：一瓶解药+一瓶毒药，整局各一次，不可同夜双用；第一晚知道狼刀
- hunter（猎人）：被狼人/公投死亡可开枪带走一人（被毒杀不能开枪）
- guard（守卫）：每晚守护一人，不能连守同人；与狼人冲突为平安夜
- villager（村民）：无夜间技能
- idiot（白痴）：被公投出局不会死，但失去投票权（翻牌，仅可发言）
- cupid（丘比特）：首夜连情侣，任一死亡另一殉情；可能形成第三阵营

说明：当前后端已实现 werewolf/seer/witch/villager；其余可按本规范扩展。

---

## 4. 游戏状态机与阶段

状态集合：
- game_start
- night（含狼人多轮讨论、seer 查验、witch 用药、guard 守护等）
- day_morning（系统公告夜间结果）
- day_discussion（多轮发言，支持竞选警长可选）
- day_voting（警长/公投）
- vote_reveal（投票结果公布）
- day_end（可选阶段，用于整理摘要）
- end（游戏结束）

胜负判定：
- werewolves 胜：存活狼人数量 ≥ 存活好人数
- villagers 胜：所有狼人出局
- 第三阵营（情侣等）：按扩展规则另行判定（后续实现）

当前实现映射（后端）：
- 已有 night/day 循环与 history 记录；后续可插入 day_morning、vote_reveal、day_end 等更细阶段。
- 相关代码：[`Game.night_phase()`](games/werewolf/backend/app.py:141), [`Game.day_phase()`](games/werewolf/backend/app.py:215)

---

## 5. 消息传递协议（AI 输入/输出统一格式）

为统一 AI 调用与可评测性，定义 JSON-first 输入输出格式。

### 5.1 输入（给 AI）

```json
{
  "game_id": "room_001",
  "message_id": "uuid-or-seq",
  "phase": "night|day_morning|day_discussion|day_voting|vote_reveal|end",
  "day": 1,
  "current_player": "AI_1",
  "your_role": "werewolf",
  "your_team": "werewolves",
  "game_context": {
    "alive_players": ["AI_1", "AI_2", "AI_3", "AI_4", "AI_5", "AI_6"],
    "dead_players": [],
    "sheriff": null,
    "game_config": { "total_players": 6, "vote_reveal": true, "max_discussion_rounds": 3 }
  },
  "role_specific_info": {
    "werewolf_teammates": ["AI_2"],
    "witch_potions": {"save_available": true, "poison_available": true},
    "seer_reveals": [],
    "guard_protections": []
  },
  "complete_history": {
    "night_events": [],
    "day_events": [],
    "player_reputations": {}
  },
  "current_phase_details": {
    "discussion_round": 1,
    "previous_speeches_today": [],
    "werewolf_discussion_so_far": [],
    "available_targets": ["AI_3","AI_4","AI_5","AI_6"]
  },
  "action_requirements": {
    "expected_action": "discuss|kill|reveal|witch_action|protect|speak|vote",
    "format_requirements": {},
    "deadline": "ISO8601"
  }
}
```

### 5.2 输出（AI 返回）

```json
{
  "game_id": "room_001",
  "message_id": "uuid-or-seq",
  "player": "AI_1",
  "action": "discuss|kill|reveal|witch_action|protect|speak|vote",
  "action_data": {
    "speech": "建议今晚杀AI_4",
    "target": "AI_4",
    "secondary_target": null,
    "reasoning": "AI_4白天发言像神职"
  },
  "meta_information": {
    "confidence": 0.85,
    "strategy_used": "eliminate_threat",
    "reasoning_chain": ["分析发言","评估风险"],
    "model_used": "gpt-4",
    "latency": 1.2,
    "token_count": 245
  },
  "validation_info": { "format_valid": true, "target_valid": true, "within_constraints": true },
  "timestamp": "2024-01-01T10:00:00Z"
}
```

说明：
- 当前后端已向 AI 传入最小上下文（state/talk_history）且要求 JSON-first；可逐步扩展为上述结构。
- 对 JSON 解析失败，应有容错（回退启发式策略）。

---

## 6. 行为与结果 JSON Schema（建议形状）

以下为建议形状（非严格 JSON Schema，仅示意字段结构与类型）。

- 狼人夜间讨论（多轮）
```json
{ "action": "discuss", "speech": "string", "target": "string|null", "meta": {"strategy": "string"} }
```

- 狼人最终击杀
```json
{ "action": "kill", "target": "string", "meta": {"final_reasoning": "string", "discussion_summary": "string"} }
```

- 预言家查验
```json
{ "action": "reveal", "target": "string" }
```

- 女巫用药
```json
{ "action": "witch_action", "save_target": "string|null", "poison_target": "string|null", "meta": {} }
```

- 守卫守护
```json
{ "action": "protect", "target": "string" }
```

- 白天发言
```json
{ "action": "speak", "speech": "string", "sheriff_candidate": "boolean|optional", "meta": {"strategy":"string"} }
```

- 投票
```json
{ "action": "vote", "sheriff_vote": "string|null", "lynch_vote": "string|'abstain'|null", "meta": {"reasoning":"string"} }
```

---

## 7. 投票公布与透明度配置

配置：
```json
{
  "vote_reveal_settings": {
    "sheriff_votes_visible": true,
    "lynch_votes_visible": true,
    "show_voter_identity": true,
    "show_vote_target": true,
    "reveal_timing": "immediate_after_voting"
  }
}
```

公布结构（示例）：
```json
{
  "phase": "vote_reveal",
  "day": 1,
  "sheriff_election_results": {
    "votes": {"AI_3": 4, "AI_4": 2},
    "elected_sheriff": "AI_3",
    "vote_details": [
      {"voter": "AI_1", "vote": "AI_4", "revealed": true}
    ]
  },
  "lynch_vote_results": {
    "votes": {"AI_1": 3, "null": 3},
    "lynched": null,
    "vote_details": [
      {"voter": "AI_3", "vote": "AI_1", "revealed": true}
    ]
  },
  "strategic_analysis": {
    "voting_patterns": {
      "suspicious_votes": ["AI_1 和 AI_2 同票 AI_4"],
      "consistent_votes": ["AI_3/AI_4/AI_5 同票 AI_1"]
    }
  }
}
```

---

## 8. 上下文管理与压缩策略

为适配大模型 token 限制，建议上下文管理：
```json
{
  "context_management": {
    "max_tokens": 8000,
    "compression_strategy": "selective_retention",
    "always_include": [
      "current_phase","player_role","alive_players","recent_events","important_reveals","vote_history"
    ],
    "selectively_include": [
      {"type":"old_speeches","criteria":"last_2_days_only"},
      {"type":"player_reputations","criteria":"active_players_only"},
      {"type":"night_events","criteria":"relevant_to_current_phase"}
    ],
    "summarize_instead": ["very_old_discussions","minor_voting_details","player_metadata"]
  }
}
```

---

## 9. 历史记录（history）与审计字段

后端对每一步的记录建议如下（兼容当前实现）：

### 9.1 夜（night）事件条目
```json
{
  "phase": "night",
  "day": 2,
  "killed": "AI_5|null",
  "actions": [
    { "actor": "AI_1", "action": "vote_kill", "target": "AI_5", "meta": { "model": "string|null", "latency": 0.8, "api_key_used": true } },
    { "actor": "AI_3", "action": "reveal", "target": "AI_2", "revealed_role": "villager", "meta": { "model": "string|null", "latency": 0.5 } },
    { "actor": "AI_4", "action": "witch_action", "target": "AI_5", "result": "saved|poisoned|optional", "meta": {} }
  ],
  "witch_save_available": true|false,
  "witch_poison_available": true|false,
  "werewolf_choices": ["AI_5","AI_6","AI_5"]
}
```

### 9.2 昼（day）事件条目
```json
{
  "phase": "day",
  "day": 2,
  "lynched": "AI_3|null",
  "votes": { "AI_3": 3, "AI_6": 2 },
  "votes_meta": [
    { "voter": "AI_1", "vote": "AI_3", "model": "string|null", "latency": 0.7 }
  ],
  "talks": [
    { "player": "AI_1", "speech": "我怀疑 AI_3", "meta": {"heuristic":false}, "model":"string|null", "latency":0.7 }
  ]
}
```

### 9.3 结束（end）
```json
{ "phase": "end", "winner": "villagers|werewolves|third_party" }
```

说明：
- 以上结构已与当前实现字段对齐；后续扩展 sheriff、vote_reveal 可增加子字段但保持兼容。

---

## 10. 评测与统计（可选）

- 每局导出 JSONL：包含每一步 AI 输入/输出、延迟、tokens、解析错误次数、provider 使用等。
- 汇总 CSV：胜率、平均轮次、平均延迟、解析失败率、投票一致度。
- 并发与限流：按 provider 维度限速队列，指数退避重试，失败回退启发式。

---

## 11. 安全、限流与鲁棒性

- 秘钥：api_keys.json 不入库/不提交 Git。`.gitignore` 保护。
- 输入校验：AI 输出 JSON-first，严格验证 action/target 合法性；失败重试→启发式回退。
- 日志去敏：记录 `api_key_used: true/false`，不泄露明文 key。
- 失败恢复：网络失败/429 限流/解析失败均可回退默认策略，保证对局进行。

---

## 12. 与现有实现的映射与兼容性

- 已有端点（后端）：/rooms（GET/POST）、/rooms/:id/join、/rooms/:id/start、/rooms/:id/step、/rooms/:id/state
- 已有配置端点（后端）：/config/api_keys、/config/players
- 已有前端：房间控制、Providers 可视化编辑、玩家/职业偏好配置
- 已有 history 字段：night/day/end 事件（详见第 9 节）
- 已启用 per-player api_key 解析：[`get_api_key_for_player()`](games/werewolf/backend/app.py:407)，在夜/昼调用 AI 时传入对应 key

兼容策略：
- 新增字段以“可选/向后兼容”为原则；未实现角色（hunter/guard/idiot/cupid）默认忽略相关流程。
- 渐进式引入 day_morning、vote_reveal 分阶段。

---

## 13. 未来扩展

- 角色：hunter（开枪）、guard（守护）、idiot（翻牌免死）、cupid（情侣阵营）
- 投票/竞选：警长优先级与加票规则
- 房间玩法：自定义局（禁用/启用角色）、公开/私密房间
- 观战：旁观者日志视图与回放
- UI：iOS 风格动画、时间线、分阵营视图与投票热力图
- 打包与发布：PyInstaller GUI 启动器，Windows 一键运行

---

## 附：运行与调试

- 后端：
  - Windows PowerShell 示例：
    - `python games/werewolf/backend/app.py`
- 前端：
  - `cd games/werewolf/frontend && npm install && npm run dev`
  - 已配置 Vite 代理（/rooms、/config → http://127.0.0.1:8080）：[`games/werewolf/frontend/vite.config.js`](games/werewolf/frontend/vite.config.js:1)

---

## 结语

本规范统一了角色、阶段、消息协议、history 记录、投票公布与上下文管理，确保可扩展、可评测与可视化。落地时请按“兼容现有实现、逐步增强”的原则推进，并为新字段添加最小必需的容错逻辑。