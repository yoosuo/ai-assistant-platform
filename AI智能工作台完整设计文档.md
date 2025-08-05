# AI智能工作台完整设计文档

## 1. 项目概述

### 1.1 产品定位
- **风格基调**：企业微信式的冷静蓝白灰配色，布局清晰、信息密度高，强化「效率工具」的定位
- **使用场景**：AI协助用户在类似群聊的界面中进行问题解答、报告生成、思考推进
- **主要形式**：类「IM平台」的工作台 + AI助手 + 功能区，侧重生产与信息聚合

### 1.2 技术架构
- **前端技术**：HTML + Tailwind CSS + 原生JavaScript
- **后端框架**：Flask + SQLite
- **AI服务**：阿里云百炼API（通义千问）
- **搜索引擎**：Google Custom Search JSON API
- **部署方式**：本地部署

## 2. 系统架构设计

### 2.1 前端架构
```
frontend/
├── static/
│   ├── css/
│   │   └── tailwind.min.css
│   ├── js/
│   │   ├── main.js          # 主要交互逻辑
│   │   ├── chat.js          # 聊天功能
│   │   ├── config.js        # 配置管理
│   │   └── utils.js         # 工具函数
│   └── assets/
│       └── images/
├── templates/
│   ├── base.html           # 基础模板
│   ├── index.html          # 首页
│   ├── workspace.html      # 工作台主界面
│   ├── config.html         # 配置页面
│   └── report.html         # 报告详情页
```

### 2.2 后端架构
```
backend/
├── app.py                  # Flask应用主文件
├── config.py              # 配置管理
├── models/
│   ├── __init__.py
│   ├── conversation.py     # 会话模型
│   ├── message.py          # 消息模型
│   ├── expert.py          # 专家模型
│   └── report.py          # 报告模型
├── services/
│   ├── __init__.py
│   ├── ai_service.py      # AI服务
│   ├── search_service.py  # 搜索服务
│   └── tool_service.py    # 工具调用服务
├── routes/
│   ├── __init__.py
│   ├── chat.py            # 聊天相关路由
│   ├── config.py          # 配置相关路由
│   └── report.py          # 报告相关路由
└── utils/
    ├── __init__.py
    ├── database.py        # 数据库工具
    └── helpers.py         # 辅助函数
```

## 3. 界面结构设计

### 3.1 首页（index.html）
- **首次访问**：中间区域显示大文本框，引导文字："输入你现在的问题或任务，我们来帮你完成。"
- **非首次访问**：自动跳转到工作台页面

### 3.2 工作台主界面（workspace.html）
#### 布局结构（三列布局）：

**左侧：会话列表区域（宽度：300px）**
- 会话搜索框
- 会话列表（按时间倒序）
- 新建会话按钮

**中间：聊天区域（flex-1）**
- 聊天历史展示区
- 消息输入框
- 发送按钮
- 报告卡片展示

**右侧：AI思考区域（宽度：350px，可折叠）**
- AI思考过程展示
- 工具调用日志
- 折叠/展开按钮

### 3.3 配置页面（config.html）
- API密钥配置
- 搜索引擎配置
- 专家管理

### 3.4 报告详情页（report.html）
- 结构化报告展示
- 搜索功能
- 下载PDF功能

## 4. 数据库设计

### 4.1 表结构设计

```sql
-- 会话表
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 消息表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text',  -- 'text', 'report', 'thinking'
    metadata TEXT,  -- JSON格式的元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 专家表
CREATE TABLE experts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    role_setting TEXT,  -- AI角色设定
    avatar_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 报告表
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON格式，包含章节信息等
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 配置表
CREATE TABLE configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. API接口设计

### 5.1 聊天相关接口
```
POST /api/chat/send          # 发送消息
GET  /api/chat/conversations # 获取会话列表
POST /api/chat/conversation  # 创建新会话
GET  /api/chat/messages/{conversation_id}  # 获取会话消息
DELETE /api/chat/conversation/{id}  # 删除会话
```

### 5.2 配置相关接口
```
GET  /api/config            # 获取配置
POST /api/config            # 更新配置
POST /api/config/test       # 测试配置
```

### 5.3 专家相关接口
```
GET  /api/experts           # 获取专家列表
POST /api/experts           # 创建专家
PUT  /api/experts/{id}      # 更新专家
DELETE /api/experts/{id}    # 删除专家
```

### 5.4 报告相关接口
```
GET  /api/reports/{id}      # 获取报告详情
POST /api/reports/{id}/pdf  # 导出PDF
POST /api/reports/{id}/regenerate  # 重新生成报告
```

## 6. AI功能交互设计

### 6.1 FunctionCall机制
AI使用 `<tool_use>` 标记调用工具：
```json
{
  "tool_use": "search_web",
  "params": {"query": "2024年新能源汽车销量排名"}
}
```

### 6.2 支持的工具类型
- `search_web`: 网络搜索
- `generate_report`: 生成报告
- `create_expert`: 创建专家
- `analyze_data`: 数据分析

### 6.3 AI思考过程
- 推理过程存储在右侧思考面板
- 工具调用日志记录
- 用户可查看完整思考树

## 7. 搜索功能设计

### 7.1 Google Custom Search API集成
- 支持多站点配置
- 限制搜索域
- API调用稳定性保障

### 7.2 搜索结果处理
- 结果摘要提取
- 相关性排序
- 缓存机制

## 8. 动画与交互设计

### 8.1 页面动画
- 会话列表滑入动画
- 消息气泡渐入效果
- 思考面板展开/折叠动画

### 8.2 反馈动画
- 输入框聚焦发光效果
- 发送按钮点击反馈
- 报告生成加载动画
- AI回应打字动画

## 9. 配置管理

### 9.1 API配置
- 阿里云百炼API密钥
- Google搜索API密钥
- 自定义搜索引擎ID

### 9.2 应用配置
- 调试模式
- 数据库路径
- 会话保留时间

## 10. 部署说明

### 10.1 依赖安装
```bash
pip install flask flask-cors requests python-dotenv
```

### 10.2 环境配置
创建 `.env` 文件：
```
DASHSCOPE_API_KEY=your-dashscope-api-key
GOOGLE_SEARCH_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
SECRET_KEY=your-secret-key
DEBUG=True
```

### 10.3 启动应用
```bash
python app.py
```

## 11. 开发计划

### Phase 1: 基础框架搭建
1. Flask应用结构搭建
2. 数据库模型创建
3. 基础HTML模板

### Phase 2: 核心功能开发
1. 聊天界面实现
2. AI服务集成
3. 消息存储与展示

### Phase 3: 高级功能
1. FunctionCall机制
2. 搜索功能集成
3. 专家系统

### Phase 4: 优化与完善
1. 界面动画
2. 报告功能
3. 配置管理
4. 错误处理

## 12. 技术特点

- **轻量级**：使用原生HTML/JS，避免复杂框架
- **响应式**：使用Tailwind CSS确保跨设备兼容
- **模块化**：清晰的代码结构，便于维护
- **可扩展**：插件式工具架构，便于添加新功能