# 竞赛智能客服系统

## 项目概述

本系统是一款高效的智能客服机器人，旨在回答用户关于各类竞赛的问题。系统采用最新的RAG（检索增强生成）和MCP（模型-上下文协议）技术，能够快速、准确地回答用户关于竞赛基本信息、要求、评分标准等问题。

## 系统特点

- **多竞赛知识库**：包含多个竞赛的完整信息，能够回答各类竞赛相关问题
- **智能检索引擎**：采用改进的RAG技术，高效检索相关文档内容
- **精准答案生成**：结合MCP与RAG技术，确保回答的准确性和相关性
- **实时更新能力**：支持知识库的实时更新，保证信息时效性
- **美观交互界面**：简洁直观的网页界面，提供良好的用户体验

## 系统架构

系统由以下主要组件构成：

1. **知识库模块**：存储竞赛相关PDF文档及处理后的文本数据
2. **RAG检索引擎**：基于关键词和语义相似度进行文档检索
3. **MCP生成模块**：基于检索结果生成准确的回答
4. **Web服务模块**：提供RESTful API接口和网页交互界面

### 详细架构说明

#### 项目目录结构

```
竞赛智能客服系统
├── app/                        # 主应用程序目录
│   ├── api/                    # API接口定义
│   │   ├── api_router.py       # API路由配置
│   │   └── session.py          # 会话管理
│   ├── controllers/            # 控制器层
│   │   ├── qa_controller.py    # 问答控制器
│   │   └── qa_router.py        # 问答路由
│   ├── models/                 # 核心模型组件
│   │   ├── MCPWithContext.py   # MCP上下文处理
│   │   ├── RAGAdapter.py       # RAG适配器
│   │   ├── SimpleMCPWithRAG.py # MCP与RAG集成
│   │   ├── SimpleRAG.py        # RAG实现
│   │   ├── mcp_engine.py       # MCP引擎
│   │   ├── query_router.py     # 查询路由
│   │   └── structured_kb.py    # 结构化知识库
│   ├── services/               # 服务层
│   │   ├── data/               # 数据服务
│   │   └── knowledge/          # 知识库服务
│   ├── templates/              # 前端模板
│   │   └── index.html          # 主页模板
│   ├── utils/                  # 工具类
│   │   ├── logging.py          # 日志工具
│   │   ├── middleware.py       # 中间件
│   │   ├── question_enhancer.py # 问题增强工具
│   │   └── response_formatter.py # 响应格式化工具
│   ├── views/                  # 视图层
│   ├── config.py               # 配置文件
│   └── main.py                 # 主程序入口
├── data/                       # 数据目录
│   ├── kb/                     # 知识库
│   ├── knowledge/              # 知识资源
│   │   ├── docs/               # 原始文档
│   │   ├── txt/                # 文本版本
│   │   ├── index/              # 索引文件
│   │   └── vectors/            # 向量存储
│   ├── processed/              # 处理后的数据
│   ├── session/                # 会话数据
│   ├── stopwords/              # 停用词
│   └── vector_store/          # 向量数据存储
├── docker/                     # Docker配置
├── logs/                       # 日志文件
├── test_results/               # 测试结果
├── direct_start.bat            # 直接启动脚本
├── docker-start.bat            # Docker启动脚本
├── force_rebuild_index.py      # 索引重建工具
├── requirements.txt            # 依赖项
├── setup.py                    # 安装配置
├── test_all_questions.py       # 问题测试脚本
├── test_api.py                 # API测试脚本
└── test_ws_simple.py           # WebSocket测试脚本
```

#### 组件功能说明

1. **核心模型层**
   - **SimpleRAG.py**: 实现检索增强生成技术，对用户问题进行分析，从知识库中检索相关文档
   - **MCPWithContext.py**: 提供MCP（模型上下文协议）支持，将检索的上下文与用户问题结合
   - **SimpleMCPWithRAG.py**: 集成RAG和MCP技术，构建完整的问答流程
   - **RAGAdapter.py**: 适配器类，统一接口格式，增强组件兼容性
   - **mcp_engine.py**: MCP核心引擎，处理与大型语言模型的交互
   - **query_router.py**: 查询路由器，根据问题特征分发到合适的处理组件
   - **structured_kb.py**: 处理结构化知识库数据，支持高效检索和更新

2. **控制器层**
   - **qa_controller.py**: 问答业务控制器，协调模型层和服务层，处理问答请求
   - **qa_router.py**: 问答路由器，定义问答相关的路由规则

3. **服务层**
   - **data/**: 数据服务相关组件，负责数据加载和处理
   - **knowledge/**: 知识库服务组件，管理知识库索引和查询

4. **工具层**
   - **logging.py**: 日志管理工具，记录系统运行日志
   - **middleware.py**: 中间件组件，处理请求前后的通用逻辑
   - **question_enhancer.py**: 问题增强工具，优化用户提问以提高检索质量
   - **response_formatter.py**: 响应格式化工具，统一处理API响应格式

5. **接口层**
   - **api_router.py**: API路由配置，定义系统对外接口
   - **session.py**: 会话管理，处理用户会话信息

6. **数据层**
   - **知识库**: 包含竞赛相关的PDF文档、预处理文本和索引
   - **向量存储**: 保存文档向量表示，用于语义检索
   - **会话存储**: 保存用户会话信息，支持上下文理解

7. **前端层**
   - **templates/index.html**: 主页模板，提供用户交互界面
   - **views/**: 视图组件，渲染用户界面

8. **支持工具**
   - **direct_start.bat**: 快速启动脚本
   - **force_rebuild_index.py**: 强制重建索引工具
   - **test_all_questions.py**: 系统功能测试脚本

#### 数据流向

1. 用户通过Web界面或API发送问题
2. 系统对问题进行预处理和关键词提取
3. RAG引擎检索相关文档片段
4. MCP引擎结合文档和问题生成答案
5. 系统评估答案质量并计算置信度
6. 将格式化的答案返回给用户

## 主要功能

- **竞赛信息查询**：回答关于竞赛背景、目标、时间安排等基本信息
- **参赛要求查询**：提供参赛条件、参赛对象、报名方式等信息
- **评分标准解答**：解释竞赛评分机制和标准
- **资料提交指导**：说明参赛作品的提交要求和方式
- **奖项设置说明**：介绍竞赛奖项设置和奖励机制

## 使用说明

### 系统启动方式

有两种方式启动系统：

1. **标准启动方式**：
   ```bash
   python -m app.main
   ```

2. **使用直接启动器**：
   ```bash
   .\direct_start.bat
   ```

### 重建索引

如需重建知识库索引，可以使用以下命令：

```bash
python force_rebuild_index.py
```

### 系统测试

为验证系统功能，可以运行以下测试脚本：

```bash
python test_all_questions.py
```

## 常见问题排查

### 前端页面显示"系统初始化出现问题"

可能原因：
1. 会话初始化失败
2. API服务未正常启动
3. 浏览器控制台出现网络错误

解决方法：
1. 刷新页面，检查浏览器控制台日志
2. 确保服务器正常运行 (`python -m app.main`)
3. 检查服务器日志 (`logs/app.log`)

### 回答质量不佳或不完整

可能原因：
1. 知识库索引过期或损坏
2. 相关竞赛信息不完整
3. 查询关键词提取不准确

解决方法：
1. 重建索引 (`python force_rebuild_index.py`)
2. 使用更具体的问题描述
3. 指定具体的竞赛类型

### 系统响应缓慢

可能原因：
1. 首次查询需要加载模型
2. 复杂问题需要处理更多文档
3. 服务器资源不足

解决方法：
1. 首次查询后系统会加速
2. 尝试简化问题或分多次提问
3. 确保服务器有足够的计算资源

## 技术支持

如有问题，请查阅问题汇总文档或联系开发团队。

## 系统访问

系统启动后，可通过以下地址访问：

- Web界面：http://localhost:53085
- API接口：
  - 问答API：http://localhost:53085/api/query
  - 重建索引：http://localhost:53085/api/rebuild_index

## API接口规范

### 问答接口 (/api/ask)

**请求方法**：POST

**请求参数**：
```json
{
    "text": "您的问题内容", // 必填，问题文本
    "session_id": "会话ID"  // 可选，用于跟踪对话上下文
}
```

**响应格式**：
```json
{
    "answer": "回答内容",
    "confidence": 0.95,  // 置信度，0-1之间的浮点数
    "competition_type": "竞赛类型",
    "sources": [  // 引用的知识库来源
        {
            "content": "相关内容片段",
            "source": "文档名称",
            "page": 1,
            "score": 0.85
        }
    ],
    "processing_time": 0.25  // 处理时间(秒)
}
```

### 重建索引接口 (/api/rebuild_index)

**请求方法**：POST

**请求参数**：无

**响应格式**：
```json
{
    "status": "success",
    "message": "索引重建成功, 耗时: 5.32秒"
}
```

### WebSocket接口 (/ws)

支持通过WebSocket发送与接收消息，参数格式与/api/ask相同。

## 最新改进

### 2025-05-20更新

针对WebSocket连接不稳定和前端无响应问题，进行了以下架构级改进：

1. **组件接口统一**：
   - 创建RAGAdapter适配器类，解决组件间接口不一致问题
   - 统一搜索参数处理，确保兼容性和稳定性
   - 使用适配器模式替代直接调用，增强系统弹性

2. **数据流处理完善**：
   - 新增response_formatter模块，实现响应标准化
   - 所有API和WebSocket返回使用统一格式，确保前端处理一致性
   - 修复"Too much data for declared Content-Length"错误

3. **错误处理机制优化**：
   - 实现层次化错误处理，区分系统错误和业务错误
   - 添加用户友好的错误提示，提高用户体验
   - 完善错误日志记录，便于问题定位

4. **WebSocket稳定性提升**：
   - 改进WebSocket连接管理，完善连接生命周期
   - 增加连接状态检查，防止向已关闭连接发送消息
   - 引入超时保护机制，避免长时间请求阻塞连接

通过这些深层次架构改进，系统稳定性和可靠性显著提升，用户可以流畅地进行问答交互。

### 2025-05-19更新

针对"答非所问"问题，进行了以下重要改进：

1. **重构SimpleRAG.py搜索逻辑**：
   - 改用全库搜索模式，不再限制在特定竞赛类型内搜索
   - 引入jieba.posseg进行词性标注，提高关键词提取质量
   - 实现停用词过滤机制，移除无关词语
   - 设计多维度评分机制，考虑关键词长度、频率和位置等因素

2. **引入改进的评估模型**：
   - 开发独立的qa_evaluator.py评估答案质量
   - 完善置信度计算，考虑答案质量、文档数量和文档质量
   - 增加编造信息检测，降低编造内容的评分

3. **优化系统架构**：
   - 创建direct_start.bat直接启动工具
   - 开发force_rebuild_index.py索引重建工具
   - 新增test_all_questions.py测试脚本

通过这些改进，系统回答质量显著提升，"答非所问"问题基本解决，用户体验大幅提高。

## 技术栈

- 后端：Python、FastAPI、LangChain
- 前端：HTML、CSS、JavaScript
- 人工智能：MCP（模型-上下文协议）、RAG（检索增强生成）
- 文本处理：Jieba分词、正则表达式
- 数据存储：JSON、TXT、PDF

## 系统要求

- Python 3.8+
- 现代浏览器（Chrome、Firefox、Edge等）
