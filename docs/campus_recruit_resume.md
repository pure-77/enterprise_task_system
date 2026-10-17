# **周伟东-后端开发（可全栈）**

::: left

**学校专业：** 天津商业大学 · 计算机科学与技术

**毕业时间：** 2027 届应届生（ 2027.06 毕业）

icon:github https://github.com/pure-77

:::

::: right

<div style="text-align:left">

icon:weixin 18418607921

icon:email [3082476730@qq.com](mailto:3082476730@qq.com)

</div>

:::

## **实习经历**

### **北京英视睿达科技股份有限公司** | **大气污染精准溯源系统 - 后端开发** | 2026.05 - 2026.09

*技术栈：Python, FastAPI, SQLAlchemy, Celery, Redis, MySQL, GeoPandas, Docker, Supervisor*

**项目描述**：针对北京大气高值报警（如 PM2.5 超标）需求研发的污染源溯源平台，实时分析 3km 半径内污染源贡献权重并生成扩散图谱。

1. **分布式调度流水线**：设计基于 Celery 的多阶段异步任务队列（数据拉取 → 预检 → 溯源计算 → 可视化渲染），通过 `try/except` 隔离机制保障单类污染源计算异常不阻断全局链路。
2. **高并发与性能优化**：引入 Redis 优先级队列实现状态机流转（pending→ready→processing→success/failed）；设计磁盘级 Pickle 缓存（TTL+LRU 淘汰）结合气象预检，有效拦截无效计算，降本增效明显。
3. **空间数据计算与渲染**：基于高斯衰减模型与 GeoPandas 开发烟羽扩散计算逻辑，运用 Catmull-Rom Bicubic 上采样与高斯模糊算法生成平滑等高线图层，并无缝集成阿里云 OSS 交付前端。
4. **业务 API 与运维部署**：独立开发 7 个核心 API（含站点聚合、溯源贡献 Top10 分析等），支持多维度组合筛选；使用 Supervisor 完成进程保护，在 Linux 环境下实现稳定运行。

## **项目经历**

### 企业级协作办公平台 + AI Agent 智能助手 | 全栈开发（FastAPI · Vue3 · AI）

*技术栈：FastAPI / SQLAlchemy / MySQL / Redis / Celery / RabbitMQ · Vue3 / Pinia / Element Plus · Docker Compose · DeepSeek / 通义千问*

**项目描述**：一个**独立设计并上线**的多工作空间协作平台，覆盖任务、IM、考勤、OA 审批、日历等 10+ 模块，
并集成 LLM Agent 提供自然语言操作与智能提醒能力。

1. **权限与安全体系**：基于 FastAPI 异步架构设计 RBAC 模块，实现多工作空间隔离；构建 JWT 动态刷新 + Redis 验证码 + 接口防刷 + bcrypt 加密安全网，配合全局审计日志中间件实现全链路追踪。
2. **分布式 IM 通讯引擎**：WebSocket + Redis Pub/Sub + RabbitMQ 三层架构，支撑集群部署下单/群聊消息投递一致性；消息已读回执、离线补偿、富文本 + 文件传输完整链路；前端自适应重连 + 消息分页加载，弱网体验平滑。
3. **复杂业务与异步解耦**：多级 OA 审批引擎（会签/或签/条件分支），考勤排班系统；Celery Beat 30 分钟轮询 + Redis 去重，实现任务/日程到期前 6 小时邮件提醒；预计算统计数据写入缓存，用户首屏加载 < 300ms。
4. **前端与工程化交付**：使用 Vue3 + Pinia + Axios 构建流畅 UI；基于 Docker/Docker-compose 进行多容器服务编排部署，实现环境隔离与日志统管。
5. **LLM Agent 智能助手**：零 LangChain 自研 Agent 框架 —— 单例 ToolRegistry 统一管理 20 个业务工具（task/IM/日程/审批等 10 模块），意图识别二级路由先分工具组再加载，避免 LLM 被 20+ tools 淹没；抽象 LLMProvider 工厂路由，DeepSeek 负责 Function Calling 推理、千问 VL 负责多模态图片理解；Redis 短期记忆 + localStorage 持久化跨会话；Celery Beat 30 分钟轮询 + Redis 去重实现任务/日程到期前 6 小时邮件提醒；后端 workspace_id 全链路透传 + Python falsy 边界修复 16 处，生产级稳定性打磨。

## **技能**

- **后端开发与语言**：熟练掌握 Python，深入理解 FastAPI / Django 框架请求生命周期、`asyncio` 异步编程模型及 ORM 查询优化；熟练掌握 RESTful API 设计、JWT 双 Token 鉴权与 RBAC 权限控制。
- **数据库与缓存**：具备 MySQL 表结构设计与慢查询调优能力；熟悉 ClickHouse 列式存储与高频时序数据聚合分析；深入理解 Redis 缓存设计（穿透/击穿/雪崩）、分布式锁（Lua 原子释放）及双队列可靠消费（BRPOPLPUSH）。
- **分布式与中间件**：深入理解 Celery 异步任务队列架构（优先路由、Beat 调度、指数退避重试与幂等保障）；熟练组合 WebSocket + Redis Pub/Sub + RabbitMQ 解决分布式集群下的实时消息广播与状态一致性。
- **数据处理与全栈工程**：熟练使用 pandas / numpy / GeoPandas 进行数据清洗，批处理等；熟练运用 Vue3 + Pinia 独立开发管理后台；熟悉 Linux 运维命令、Docker/Docker-compose 容器化编排及 Supervisor 进程守护。
- **Agent 开发**：深入理解 LLM Function Calling / Tool Use 协议与 ReAct 推理循环，自研 Agent 核心框架（LLM Provider 抽象层 + 单例 ToolRegistry 工具注册中心 + 意图二级路由器），工具层对齐 MCP 协议设计（JSON Schema + handler），零 LangChain 依赖；双 LLM 路由（DeepSeek 推理 + 千问 VL 多模态图片理解），Redis 短期记忆 + localStorage 跨会话持久化；Prompt 工程（System Prompt 上下文注入 + Few-shot 示例 + 时间/空间动态变量）；RAG 架构设计经验（ChromaDB 向量存储 + 通义 Embedding + BM25 混合检索）。

## **教育经历**

**2023.9-2027.6** 天津商业大学 | 计算机科学与技术

竞赛奖项：蓝桥杯全国软件和信息技术专业人才大赛省级二等奖

证书：CET-4

核心课程：数据结构、算法分析、数据库原理、计算机网络、操作系统