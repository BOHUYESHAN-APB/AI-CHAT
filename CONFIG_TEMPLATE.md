# YAML配置文件模板

## 配置文件结构说明

### 主配置文件 (config.yaml)

```yaml
# AI游戏测试平台配置文件
version: "1.0.0"

# AI服务提供商配置
ai_providers:
  - name: "GPT-4"
    provider: "openai"
    api_key: "your-openai-api-key-here"
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 1000
    enabled: true
    
  - name: "Claude-3"
    provider: "anthropic"
    api_key: "your-claude-api-key-here"
    model: "claude-3-sonnet-20240229"
    temperature: 0.7
    max_tokens: 1000
    enabled: true
    
  - name: "Gemini-Pro"
    provider: "google"
    api_key: "your-gemini-api-key-here"
    model: "gemini-pro"
    temperature: 0.7
    max_tokens: 1000
    enabled: true

# 游戏通用设置
game_settings:
  # 界面显示设置
  display:
    theme: "dark"  # light/dark/system
    language: "zh-CN"  # 界面语言
    font_size: 12
    chat_style: "bubble"  # bubble/list
    layout: "circular"  # circular/grid/linear
    
  # 聊天显示设置
  chat:
    show_timestamps: true
    show_avatars: true
    avatar_size: 40
    bubble_max_width: 300
    animation_enabled: true
    
  # 身份牌显示
  identity_cards:
    visible: false  # 默认隐藏身份
    reveal_on_death: true  # 死亡时揭示身份
    style: "modern"  # classic/modern

# 狼人杀游戏特定设置
werewolf_game:
  # 默认游戏设置
  default_settings:
    player_count: 8
    roles:
      werewolf: 2
      villager: 4
      prophet: 1
      witch: 1
      hunter: 0
      idiot: 0
    
  # 游戏流程设置
  game_flow:
    day_time_limit: 120  # 白天讨论时间(秒)
    night_time_limit: 60  # 夜晚行动时间(秒)
    voting_time_limit: 30  # 投票时间(秒)
    auto_proceed: false  # 自动进入下一阶段
    
  # AI行为设置
  ai_behavior:
    conversation_style: "strategic"  # strategic/random/roleplay
    min_response_length: 20
    max_response_length: 200
    include_emotions: true
    use_strategy: true

# 日志和记录设置
logging:
  level: "INFO"  # DEBUG/INFO/WARNING/ERROR
  file_enabled: true
  file_path: "logs/game.log"
  max_file_size: 10485760  # 10MB
  backup_count: 5
  
  # 数据记录设置
  data_recording:
    enabled: true
    record_chat: true
    record_actions: true
    record_decisions: true
    output_format: "json"  # json/csv

# 高级设置
advanced:
  # API调用设置
  api:
    timeout: 30  # API调用超时时间(秒)
    retry_attempts: 3
    retry_delay: 2
    
  # 性能设置
  performance:
    cache_enabled: true
    cache_size: 1000
    preload_models: false
    
  # 网络设置
  network:
    proxy_enabled: false
    proxy_url: ""
    verify_ssl: true

# 用户界面快捷键
shortcuts:
  new_game: "Ctrl+N"
  open_config: "Ctrl+O"
  save_game: "Ctrl+S"
  next_phase: "Space"
  toggle_chat: "Ctrl+T"
  show_roles: "Ctrl+R"
```

### 角色定义文件 (roles.yaml)

```yaml
# 狼人杀角色定义
roles:
  # 狼人阵营
  werewolf:
    name: "狼人"
    team: "werewolf"
    description: "夜晚可以杀死一名玩家"
    night_action: true
    priority: 10
    win_condition: "消灭所有村民或神职角色"
    
  # 村民阵营 - 普通村民
  villager:
    name: "村民"
    team: "villager"
    description: "没有特殊能力，依靠投票找出狼人"
    night_action: false
    priority: 100
    win_condition: "找出并投票处决所有狼人"
    
  # 神职角色 - 预言家
  prophet:
    name: "预言家"
    team: "villager"
    description: "每晚可以查验一名玩家的真实身份"
    night_action: true
    priority: 20
    win_condition: "帮助村民找出狼人"
    action_description: "查验一名玩家的身份"
    
  # 神职角色 - 女巫
  witch:
    name: "女巫"
    team: "villager"
    description: "拥有一瓶解药和一瓶毒药，每晚只能使用一瓶"
    night_action: true
    priority: 30
    win_condition: "帮助村民找出狼人"
    action_description: "选择使用解药救人或毒药杀人"
    
  # 神职角色 - 猎人
  hunter:
    name: "猎人"
    team: "villager"
    description: "被狼人杀死或投票处决时，可以开枪带走一名玩家"
    night_action: false
    priority: 40
    win_condition: "帮助村民找出狼人"
    action_description: "死亡时选择一名玩家带走"
    
  # 神职角色 - 白痴
  idiot:
    name: "白痴"
    team: "villager"
    description: "被投票处决时不会死亡，但失去投票权"
    night_action: false
    priority: 50
    win_condition: "帮助村民找出狼人"
    action_description: "被投票时免疫死亡"

# 团队定义
teams:
  werewolf:
    name: "狼人阵营"
    color: "#dc2626"  # 红色
    description: "隐藏在村民中的狼人，夜晚猎杀村民"
    
  villager:
    name: "村民阵营"
    color: "#16a34a"  # 绿色
    description: "善良的村民，需要找出并投票处决狼人"

# 游戏阶段定义
phases:
  - name: "夜晚"
    description: "狼人和神职角色行动阶段"
    duration: 60
    actions:
      - werewolf: "选择猎杀目标"
      - prophet: "查验玩家身份"
      - witch: "使用药水"
      
  - name: "白天"
    description: "所有玩家讨论和投票阶段"
    duration: 120
    actions:
      - all: "讨论和发言"
      - all: "投票处决嫌疑人"
```

### 配置文件使用指南

#### 1. 创建配置文件
```bash
# 复制模板文件
cp config/config.template.yaml config/config.yaml

# 编辑配置文件
# 添加您的API密钥和其他设置
```

#### 2. 配置AI提供商
每个AI提供商需要以下信息：
- `name`: 显示名称
- `provider`: 服务商类型 (openai/anthropic/google)
- `api_key`: API访问密钥
- `model`: 使用的模型名称
- `temperature`: 生成温度 (0.0-1.0)
- `max_tokens`: 最大生成长度

#### 3. 游戏设置调整
根据需求调整：
- 玩家数量和角色分配
- 时间限制设置
- 界面显示偏好
- 日志记录级别

#### 4. 自定义角色
可以在`roles.yaml`中：
- 添加新的角色类型
- 修改现有角色属性
- 调整团队配置
- 定义新的游戏阶段

#### 5. 配置文件验证
应用程序会自动验证：
- API密钥格式
- 角色配置完整性
- 游戏设置合理性
- 文件格式正确性

### 环境变量支持

除了配置文件，也支持环境变量：
```bash
# OpenAI配置
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4"

# Claude配置  
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_MODEL="claude-3-sonnet"

# Google配置
export GOOGLE_API_KEY="your-key"
export GOOGLE_MODEL="gemini-pro"
```

### 配置优先级
1. 环境变量 (最高优先级)
2. 配置文件设置
3. 默认值 (最低优先级)

### 配置热重载
配置文件支持热重载，修改后无需重启应用程序。