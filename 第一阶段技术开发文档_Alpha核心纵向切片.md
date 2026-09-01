# 第一阶段技术开发文档｜Alpha 核心纵向切片

> 文档版本：v1.0  
> 创建日期：2026-08-30  
> 配套文档：《AI 游戏素材生成产品 PRD v0.9》《AI Agent 产品 Vibe Coding 通用技术栈手册 V2.1》及已确认的《技术适配声明》。  
> 本文档只覆盖第一阶段。开发时不得提前实现商业化、公开社区、批量生产、完整团队协作或引擎插件等后续能力。

## 一、阶段目标

### 1.1 交付范围

本阶段交付一条可在桌面 Web 中亲手操作的 Alpha 核心纵向切片：

**创建项目 → 填写中文/英文文本或上传参考图 → 清晰度检查与选项式追问 → 文字生成 Seedream 道具单图或人物四视图/独立配件并确认 → Tripo 多视图建模与 20K 优化 → 查看候选和任务状态 → 基础 QA → 导出 GLB → 在 Unity 中验证**

首条验收样例固定为：

- 资产类型：静态道具。
- 项目模板：Unity URP Mobile。
- 默认语言：简体中文。
- 可切换语言：英文。
- 默认导出：GLB。
- 默认候选数：4，同时支持 1、2、4。
- 默认输入：中文或英文文本；单张 PNG、JPG、WebP 参考图。

首条样例通过后，在本阶段内按相同契约扩展：

- 单图生成。
- Unity PC、Unreal PC、Roblox/Godot 通用低模模板。
- FBX 导出；OBJ 仅在不影响 Alpha 主链路时补充。
- 武器、家具、植物、岩石、建筑小件和模块化环境件的基准样例。

### 1.2 阶段产物

- 可运行的模块化单体后端和独立任务 Worker。
- 可运行的 Next.js Web 前端。
- 项目规格、任务、候选、资产版本、QA、导出的持久化数据结构。
- 一个可替换的 3D 生成供应商适配层。
- 不依赖真实 Key 的 mock 生成适配器和固定 3D 测试资产。
- 浏览器 3D 查看器、候选对比、任务恢复、QA 展示和下载入口。
- 基础确定性 3D QA 与导出打包能力。
- 中文、英文两套界面文案和可持久化的语言切换。
- mock 自动化测试、真实模型冒烟脚本、README 和非技术验收清单。

### 1.3 阶段完成门

本阶段分为两道完成门，不得混淆：

#### 完成门 A：工程链路通过

- 使用 mock 供应商跑通完整主链路。
- 任务、候选和版本在刷新页面、SSE 断开、后端或 Worker 重启后仍可恢复。
- 相同幂等键不会创建重复任务。
- 描述不清时返回最多 3 个针对性问题；用户回答前不创建任务、不调用 3D 模型。
- 候选可独立成功或失败，单个候选失败不会隐藏其他成功结果。
- 基础 QA 对每条规则返回检测值、目标值、Pass/Warning/Block 和修复建议。
- Block 会阻止 Ready 和导出；不存在缺失检测值却显示 Pass。
- GLB 导出包完整，并能在 Unity URP Mobile 样例工程中完成一次人工导入。
- 中文为默认语言，切换英文后核心流程无遗漏、无中英混排。
- mock、后端、前端和关键交互测试全部通过。

#### 完成门 B：真实产品效果通过

- 产品经理确认 3D 生成 API 后再接入真实供应商。
- 使用真实 Key 跑通“真实输入 → 真实生成 → 候选持久化 → 浏览器预览 → QA → GLB 导出 → Unity 导入”。
- Alpha 基准集首次技术通过率达到 PRD 要求的 60% 及以上。
- 至少一个真实资产从建项到首次通过 P0 QA 并导出的总耗时不超过 15 分钟；同时如实记录样本量、网络、供应商和质量档。
- 产品经理人工确认候选具备继续迭代价值，模型结构、材质和整体视觉不存在不可接受的系统性缺陷。
- 真实任务记录供应商、模型版本、耗时、错误、重试和内部调用成本。

没有真实 API Key 时，只能完成“工程链路通过”，不得声称“真实产品效果通过”。

### 1.4 明确不做

本阶段不实现：

- 充值、订阅、支付、套餐、额度钱包、用户扣费、退款和商业账单。
- 用户可见的商业化额度预估；内部仍记录供应商调用成本和异常成本。
- 公开社区、资产市场、公开投稿和商业许可证售卖。
- 批量资产清单、完整 Style Kit、局部重生成和程序化变体。
- 自动 LOD、碰撞体、平台专用 Shader 和高级烘焙。
- Unity/Unreal 原生插件及一键同步。
- 完整团队角色、审批流、评论链接、企业 SSO 和审计后台。
- 正式邮件通知、Webhook 公共平台和开发者 API 门户。
- 复杂角色、布料、头发、写实人脸和完整动画系统。
- 音频、音乐、视频、2D UI、对白、关卡编辑和游戏逻辑生成。

角色自动绑定只保留扩展接口，不进入首条切片。真实基准通过率达到 80% 且失败可解释后，才作为 Early Access 单独立项。

## 二、技术适配摘要

### 2.1 开发路径

采用**纵向切片**。3D 候选预览、比较、人工选版、任务恢复和 QA 解释都是核心产品能力，因此第一阶段同时建设最小前端、后端和真实数据链路。

### 2.2 本阶段采用

- Python 3.11.x、FastAPI、Pydantic、pytest。
- Next.js、TypeScript、App Router、Tailwind CSS。
- Three.js 与 React Three Fiber。
- PostgreSQL、SQLAlchemy、Alembic。
- 模块化单体后端 + 独立任务 Worker。
- 统一 /api/v1 接口前缀。
- 代码状态机和确定性 QA。
- Git 版本管理和双层验收。

### 2.3 本阶段启用的按需模块

- PostgreSQL：由项目、任务、候选、版本、QA、导出、幂等和并发修改触发。
- 独立 Worker：由长耗时 3D 生成、后处理、QA 和导出触发。
- SSE：由候选渐进返回和任务阶段反馈触发，同时保留轮询恢复。
- 本地受控文件存储：由参考图、3D 模型、纹理、预览图和导出包触发。
- Blender Headless、trimesh、Pillow：由 3D 解析、基础 QA、预览和导出触发。
- 国际化模块：由中国大陆首发、默认中文和英文切换触发。

### 2.4 本阶段偏离或暂缓

- 不采用后端先行，改为纵向切片。
- 不采用 SQLite 或纯文件清单作为业务主存储，直接使用 PostgreSQL。
- 不创建一次性 HTML 验收页，最小界面直接成为正式 Web 前端的第一条切片。
- Alpha 不引入 Redis/Celery；先由 PostgreSQL 任务表和独立 Worker 保证恢复。当出现多 Worker、公平调度、优先级或稳定并发要求时再引入。
- 不实现商业化模块。PRD 中用户可见的额度、扣费、退款和套餐在本阶段暂缓；仅保留内部成本观测。
- 不引入 RAG、Chroma、OCR、Word/PDF、动态规划 Agent 和无关中间件。

## 三、技术栈与模型

### 3.1 后端

| 组件 | 选择 | 本阶段职责 |
| --- | --- | --- |
| 语言 | Python 3.11.x | API、状态机、任务、模型适配、QA、打包 |
| Web 框架 | FastAPI | 受控 API、SSE、静态下载授权 |
| 数据校验 | Pydantic | 请求、响应、模型输出、manifest、QA |
| ORM / 迁移 | SQLAlchemy / Alembic | PostgreSQL 模型与迁移 |
| 测试 | pytest | 单元、集成、状态恢复和错误路径 |
| 3D 处理 | Blender Headless、trimesh | 解析、转换、几何检测、预览辅助 |
| 图片处理 | Pillow | 图片校验、缩略图和预览 |

### 3.2 前端

| 组件 | 选择 | 本阶段职责 |
| --- | --- | --- |
| 运行时 | Node.js 22 LTS | 前端构建与运行 |
| 框架 | Next.js + TypeScript + App Router | 正式 Web 纵向切片 |
| 样式 | Tailwind CSS | 页面与响应式 |
| 3D | Three.js + React Three Fiber | GLB 预览、线框和候选比较 |
| 数据请求 | 原生 fetch 封装 + SSE 客户端 | API、轮询恢复和流事件 |
| 国际化 | next-intl 或等价轻量模块 | zh-CN 默认、en 切换 |
| 质量检查 | ESLint、TypeScript | 静态检查 |
| 交互测试 | Vitest/Testing Library、Playwright | 组件和关键流程 |

### 3.3 数据与执行

| 组件 | 当前阶段 | 说明 |
| --- | --- | --- |
| PostgreSQL | 引入 | 业务与任务状态的唯一事实来源 |
| 本地文件目录 | 引入 | 开发期资产存储，结构与对象存储键兼容 |
| 独立 Worker | 引入 | 从数据库认领任务，支持租约和恢复 |
| Redis/Celery | 暂缓 | 达到并发和调度阈值后再引入 |
| 对象存储 | 暂缓 | 外部多用户测试前迁移 |

### 3.4 模型与 API

真实模型服务的选择、配置和付费测试必须经产品经理确认，不擅自扩大调用范围。

模型调用分为两类：

1. 提示词理解 API：把中文或英文用户输入整理成可编辑的结构化字段，并生成供应商需要的规范化提示词。
2. 3D 生成 API：完成文本/单图到候选 3D 的生成。

提示词理解必须包含生成前清晰度确认门。Alpha 先使用可测试的确定性规则识别主体类型与必要信息：先确认主体方向；道具/环境件检查风格、材质和结构；人物/角色检查风格、外观服装和姿态，不追问材质。需要追问时返回结构化问题，单轮最多 3 个，每题固定提供 4 个方向选项、简短说明以及“其他/自定义”。选项答案合并回可见的原始描述后再次分析，直到信息完整。后续接入语言模型只能增强问题相关性，不得绕过用户确认直接补写需求或调用模型。

在真实接入前，AI 必须先向产品经理提供一份 API 决策说明，至少包含：

- 调用目的和不可替代性。
- 供应商、模型和中国大陆可访问性。
- 文本生成、单图生成、输出格式和任务状态能力。
- 样例效果依据及已知失败类型。
- 单次调用预估价格、免费额度和测试预算。
- 输入图片或提示词是否传出中国大陆、是否用于训练及删除政策。
- 所需 Key 名称、申请入口和后端配置位置。
- 主供应商失效时的替换方式。

产品经理确认后提供 Key。Key 只写入后端 .env 或部署 Secret，不进入前端、Git、日志或对话输出。

当前 Alpha 的概念图继续通过 TokenHub 调用 `Seedream-Image-v5.0-pro`；真实 3D 主路由使用 Tripo 官方 API。产品层不允许文字直接提交 3D：文字道具先生成一张 Seedream 概念图；文字人物生成正、左、后、右四张无遮挡完整身体视图，检测到的可拆配件各生成一张独立参考资产，再由用户确认。人物四视图按 `[front, left, back, right]` 送入 `multiview_to_model`；用户上传单张人物图时跳过 Seedream，由 Tripo `generate_multiview_image` 补全视图。TokenHub `HY-3D-3.1` 适配器保留为待排障备用路由。两个供应商使用独立后端密钥，均不进入前端、Git、日志或文档正文。

2026-08-31 对 Meshy Agent 的一次实测用户旅程表明：文本需求可先生成概念图并由用户确认，再生成高模，最后依实测面数执行重拓扑；上传图片后，界面先描述可见内容，并使用带标题、说明和单选控件的问题卡确认用户意图与处理路径。实测初始模型约 197 万面，重拓扑后为 9,951 三角面，证明不能把 Prompt 中的技术规格当作已实现的输出指标。Alpha 复用的是可观察的“问题卡 → 用户单选/自定义 → 显式提交”交互结构，不假设或复制 Meshy 的隐藏实现。

Alpha 对此采用两项约束：

- 真实 3D 调用前必须显示最终输入、模型路由、候选数、技术目标与可能费用，用户显式确认后才创建任务。
- 文生参考图已接入 `Seedream-Image-v5.0-pro`，固定 2K 并在服务端立即持久化；人物使用四次明确的单图请求生成四视图，左/后/右均引用正面图锁定身份。人物图禁止拆分四肢、遮挡、裁切与手持可拆配件；配件单独生成。确认卡提前展示图片数量和估算成本。图像调用默认不自动重试，避免在超时/5xx 后重复计费。

2026-08-31 首次真实 Seedream 请求返回 `402 / 401007`：当时账号无可用免费额度且未开启 TokenHub 后付费。该请求未生成图片，未自动重试。

产品经理开启后付费后，同日完成一次经明确授权的真实复测：`Seedream-Image-v5.0-pro` 成功生成一张 2816×1584 JPEG 宝箱概念图，服务端完成图片校验与本地持久化，仅调用一次，未自动重试，接口返回的估算成本为约 ¥0.30。该结果只证明文生概念图链路通过，不代表真实 3D 效果完成验收。

3D 提交接口属于可计费且非幂等操作，因此即使状态查询允许有限重试，创建 3D 任务本身也固定为零自动重试，防止超时后重复创建付费任务。

首次真实 3D 冒烟测试的待确认方案为：使用上述已持久化的宝箱概念图，调用 `HY-3D-3.1` 的图生 3D `normal` + PBR 路由，目标面数 10,000，仅生成 1 个候选。TokenHub 官方当前公开价格为 15～60 积分/次，HY 系列 1 积分对应 0.12 元，因此单次任务的公开参考费用区间为 ¥1.80～¥7.20，实际以控制台账单为准。未获得产品经理针对该次费用上限的明确授权前不发起请求。

2026-08-31 14:51（中国标准时间），经产品经理授权后执行上述唯一一次提交。TokenHub 在创建阶段返回 HTTP 200，但未返回任务 ID，本地未进入轮询、未下载 GLB。控制台请求记录的 `request_id` 为 `84730f9e-2de3-4e5a-abf0-c478e74d49a3`；`HY-3D-3.1` 免费体验包在该次请求时自动领取，核查时仍显示剩余 100%，按量计费未启用，因此本次失败未消耗免费积分，也不会进入后付费。

本次暴露两个工程问题：旧适配器对 HTTP 200 + `status=failed` 的业务失败只报“无效响应”，且前端可能把终态 `FAILED` 当作已完成任务。现已修改为保留供应商错误码与 `request_id`，并在前端明确显示失败。在获得新的单次测试授权前不自动重提。

产品经理随后授权在已激活的免费体验包下再执行 1 次。第二次提交仍在创建阶段失败，未返回任务 ID，错误码为 `InvalidParameter.InvalidParameter`，`request_id` 为 `b1e2f99d-8628-4c6f-9fb0-74d16c039fcd`。本地未发起第三次请求。官方公开文档中 `model`、`image_base64`、`enable_pbr`、`face_count` 和 `generate_type` 的名称与取值范围均与本地请求一致；需通过供应商调用日志或新的经授权请求获取具体错误正文后再继续定位。

经产品经理明确授权，已创建 TokenHub 日志服务关联角色 `TokenHub_QCSLinkedRoleInCloudLogService`，并关联预设策略 `QcloudAccessForTokenhubLinkedRoleInCloudLogService`，控制台显示授权成功。等待权限传播并刷新后，上述历史 HY-3D 请求的“审计日志”和“调用日志”入口仍为禁用状态，当前无法从历史日志取得详细错误正文。日志采集可能仅对授权后的新请求生效，此判断仍需后续验证；本次角色授权后未发起新的模型请求，也未消耗生成额度。

已向腾讯云提交 TokenHub 技术工单 `202608318875`，请求供应商确认两次真实请求的具体参数错误、`image_base64` 是否存在未公开限制、历史日志不可查看的原因，以及失败请求是否消耗免费积分。当前状态为“已建单”；在收到明确诊断前不重复执行可计费的 HY-3D 请求。工单联系电话属于账号联系信息，不写入项目文件或技术文档。

工单的首轮自动回复仅确认失败发生在请求体参数校验阶段，并说明日志授权通常不补采历史请求，未给出具体错误字段。现已选择“未解决，升级人工”，并向真人工程师补充脱敏后的真实请求结构、请求头类型、图片尺寸/文件大小/Base64 长度/SHA-256、两次 `request_id` 以及本地实际保留的响应字段；API Key、完整图片 Base64 和联系电话均未提交。旧适配器未持久化逐字原始响应体，工单中已如实说明，未伪造响应。真人工程师随后确认接口路径、顶层字段、字段取值、图片尺寸、Base64 形式和请求大小均符合公开规范，并确认两次创建失败均不扣积分；但仍未从服务端日志给出具体失败字段。其建议核对的 Python 类型和 Base64 换行问题已由本地实现排除，因此 HY-3D 根因仍未关闭。

Tripo 官方适配器采用独立的 `ASSETFORGE_TRIPO_API_KEY`，参考图先通过官方上传接口换取文件令牌。标准档使用 `P1-20260311`、20K 面数上限与 Detailed PBR；高质量档使用 `v3.1-20260211` 的 Detailed geometry 生成高模，再提交 `P-v2.0-20251225` Smart LowPoly，烘焙并减面到 20K。每个付费阶段的 task ID 在创建后立即写入候选指标，最终汇总 `consumed_credit`。任务创建固定零自动重试；查询和非计费上传允许有限重试。

截至 2026-09-01，多视图、Detailed 纹理、高模转 Smart LowPoly、阶段任务 ID 持久化和单图人物自动补视图已完成模拟验证；后端 44 项自动化测试全部通过，前端 lint 与生产构建通过。概念图组现已持久化，刷新后可恢复且每张图可打开原图；自动门禁会拦截与正面过于相似的侧/后视图，并要求用户逐张确认方向、无遮挡及配件隔离。配件参考图会作为独立、单独计费的 3D 资产提交。GLB 下载后会读取真实三角面、顶点、材质与纹理指标，超出 20K 时进入 `NEEDS_FIX`，不会把供应商目标值冒充实际结果。自定义美术风格、材质和结构特征会通过问题语义标记确认为已回答，不再因不在固定关键词词库而重复追问。

2026-09-01 对人物高质量样本的复盘确认：输入四视图中的左图几乎等同正面、右图为透视三分之四视角，且独立长剑仍出现在人物图中；最终 GLB 实测为 29,981 三角面、1 个材质、最高 4096px 纹理，超过 20K 预算。该旧任务已回填真实指标并改标 `NEEDS_FIX`。本轮未再触发 Seedream 或 Tripo 付费调用。

无 Key、自动化测试或供应商降级时，保留以下适配契约：

- MockPromptAssistant：返回固定、可校验的中英文结构化字段。
- MockGenerationProvider：异步返回固定 GLB 候选，可模拟成功、部分成功、超时、失败和取消。
- PromptAssistantAdapter：未来接入真实提示词理解模型。
- GenerationProviderAdapter：未来接入真实 3D 生成服务。

## 四、环境与配置

### 4.1 当前环境检查

| 项目 | 当前状态 | 开工要求 |
| --- | --- | --- |
| Git | 已安装 2.50.1；目录不是仓库 | 初始化项目仓库并配置忽略文件 |
| Python | 系统 Python 3.9.6 | 安装并锁定 Python 3.11.x |
| Node.js | 已安装 24.19.0 | 项目锁定 Node.js 22 LTS |
| npm | 已安装 11.17.0 | 使用与 Node 22 匹配的 npm 和锁文件 |
| PostgreSQL | 未确认 | 开工时安装并创建本地开发库 |
| Blender | 未安装 | 进入真实 3D QA/导出前安装并锁定版本 |
| Docker | 未安装 | 本阶段不把 Docker 作为本地开发前置条件 |
| 真实 API Key | 未提供 | 不阻塞 mock 开发，阻塞真实效果验收 |

### 4.2 环境变量

.env.example 只提供名称和安全占位值，不包含真实秘密：

| 配置项 | 是否秘密 | 说明 |
| --- | --- | --- |
| APP_ENV | 否 | local / test / production |
| APP_LOCALE_DEFAULT | 否 | 默认 zh-CN |
| APP_SUPPORTED_LOCALES | 否 | zh-CN,en |
| API_PREFIX | 否 | /api/v1 |
| DATABASE_URL | 是 | PostgreSQL 连接串 |
| ASSET_STORAGE_ROOT | 否 | 本地资产根目录 |
| PUBLIC_BASE_URL | 否 | 下载地址基础 URL |
| TASK_LEASE_SECONDS | 否 | Worker 任务租约 |
| TASK_HEARTBEAT_SECONDS | 否 | Worker 心跳 |
| MODEL_PROVIDER | 否 | `mock`、`tencent_tokenhub` 或 `tripo_official` |
| MODEL_API_BASE_URL | 否 | 供应商接口地址 |
| MODEL_API_KEY | 是 | TokenHub Key，仅用于 TokenHub 能力 |
| MODEL_NAME | 否 | 模型名称和版本 |
| TRIPO_API_BASE_URL | 否 | Tripo 官方 API 地址 |
| TRIPO_API_KEY | 是 | 独立的 Tripo 官方 `tsk_` Key |
| TRIPO_MODEL_VERSION | 否 | 默认 `P1-20260311` |
| MODEL_TIMEOUT_SECONDS | 否 | 单次调用超时 |
| MODEL_MAX_RETRIES | 否 | 有限重试次数 |
| BLENDER_EXECUTABLE | 否 | Blender 可执行文件路径 |
| MAX_REFERENCE_IMAGE_MB | 否 | 默认 20，可配置 |
| MAX_REFERENCE_IMAGE_PIXELS | 否 | 默认 8192×8192，可配置 |
| MAX_MODEL_FILE_MB | 否 | 默认 500，可配置 |
| INTERNAL_COST_TRACKING | 否 | 默认 true，仅内部观测 |

浏览器端只能读取 NEXT_PUBLIC_API_BASE_URL 和非秘密显示配置，不得出现任何模型或数据库密钥。

### 4.3 本地服务

| 服务 | 默认端口 | 说明 |
| --- | --- | --- |
| 前端 | 3000 | Next.js |
| 后端 | 8000 | FastAPI |
| PostgreSQL | 5432 | 本地数据库 |
| Worker | 无公开端口 | 数据库任务认领和处理 |

端口被占用时使用不破坏其他项目的替代端口，并同步更新 README 和环境配置。

## 五、项目结构

~~~text
ai游戏素材生成产品/
├── backend/
│   ├── app/
│   │   ├── api/                    # /api/v1 路由、SSE、错误映射
│   │   ├── core/                   # 配置、日志、安全、国际化错误文案
│   │   ├── db/                     # 数据库会话、基础模型和迁移辅助
│   │   ├── models/                 # SQLAlchemy 模型
│   │   ├── schemas/                # Pydantic 请求、响应和模型契约
│   │   ├── services/
│   │   │   ├── prompts/            # 可版本追踪的 Prompt
│   │   │   ├── providers/          # mock 与真实供应商适配器
│   │   │   ├── tasks/              # 状态机、幂等、重试、取消
│   │   │   ├── assets/             # 资产和不可变版本
│   │   │   ├── qa/                 # 确定性 QA 规则
│   │   │   └── exports/            # manifest、license、打包
│   │   ├── workers/                 # 数据库任务 Worker
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── fixtures/
│   │   └── smoke/
│   └── pyproject.toml
├── frontend/
│   ├── app/[locale]/               # zh-CN 与 en 路由
│   ├── components/
│   │   ├── project/
│   │   ├── generator/
│   │   ├── viewer/
│   │   ├── qa/
│   │   └── export/
│   ├── lib/                         # API、SSE、状态和 i18n
│   ├── messages/                    # zh-CN.json、en.json
│   └── tests/
├── data/
│   ├── uploads/                     # 参考图
│   ├── generated/                   # 模型、纹理和预览
│   ├── exports/                     # 临时导出包
│   └── quarantine/                  # 未通过校验的隔离文件
├── docs/
├── .env.example
├── .gitignore
└── README.md
~~~

不得创建本阶段没有职责的空微服务、支付、社区、团队后台或插件目录。

## 六、数据、资产与状态

### 6.1 持久化原则

- PostgreSQL 保存业务实体、任务状态、关联关系、校验结果和文件元数据。
- 大二进制文件保存在受控文件目录，数据库只保存相对受控路径、校验和、大小、类型和业务归属。
- 数据库提交成功后才能向前端发送“已完成”事件。
- 资产版本不可修改。再次生成、优化或自动修复必须创建带 parent_version_id 的新版本。
- 任务、人工确认点和候选选择必须在刷新或服务重启后恢复。
- 所有时间使用 UTC 存储，界面按用户区域显示。
- 本阶段不建立支付、余额、订阅和退款数据表。

### 6.2 核心数据表

#### workspaces

Alpha 使用一个内部工作空间，但保留 PRD 的归属边界。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| name | string | 工作空间名称 |
| default_locale | enum | zh-CN / en |
| created_at | datetime | 创建时间 |

#### projects

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| workspace_id | UUID | 业务归属 |
| name | string | 项目名称 |
| engine | enum | unity / unreal / godot / roblox |
| platform | enum | mobile / pc / generic_low_poly |
| spec_profile | JSONB | 单位、轴向、面数、纹理、命名等快照 |
| locale | enum | zh-CN / en |
| created_at / updated_at | datetime | 时间 |

项目规格修改只影响新任务，不回写历史版本。

#### stored_files

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| project_id | UUID | 项目归属 |
| kind | enum | reference / model / texture / preview / export |
| original_name | string | 脱敏后的原文件名 |
| storage_key | string | 受控相对路径 |
| mime_type | string | 检测后的真实类型 |
| byte_size | integer | 文件大小 |
| sha256 | string | 完整性校验 |
| status | enum | validating / ready / quarantined / deleted |
| created_at | datetime | 创建时间 |

#### generation_tasks

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| project_id | UUID | 所属项目 |
| state | enum | 任务状态 |
| input_mode | enum | text / image |
| original_prompt | text | 用户原始输入 |
| structured_prompt | JSONB | 模型校验后的结构化输入 |
| reference_file_id | UUID nullable | 主参考图（兼容字段） |
| reference_file_ids | JSON array | 有序参考图；人物顺序为正、左、后、右 |
| concept_bundle_id | UUID nullable | 已确认的持久化概念图组 |
| accessory_references | JSON array | 独立配件名称与参考图 ID |
| asset_type | enum | 本阶段为 prop |
| candidate_count | integer | 1 / 2 / 4 |
| quality_tier | enum | draft / standard / high |
| idempotency_key | string | 24 小时幂等 |
| provider / model_version | string nullable | 真实或 mock 供应商 |
| attempt | integer | 当前尝试次数 |
| lease_owner / lease_until | nullable | Worker 租约 |
| diagnostic_id | string | 用户可反馈的诊断编号 |
| error_code / error_message | nullable | 脱敏错误 |
| started_at / finished_at | nullable | 执行时间 |
| created_at / updated_at | datetime | 时间 |

同一工作空间、同一 idempotency_key 在 24 小时内只允许创建一个任务。

#### task_candidates

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| task_id | UUID | 所属任务 |
| index | integer | 候选序号 |
| asset_role / asset_name | string nullable | main 或 accessory 及配件名 |
| state | enum | pending / running / ready / failed / cancelled |
| model_file_id | UUID nullable | 候选模型 |
| preview_file_id | UUID nullable | 预览 |
| metrics | JSONB | 面数、材质、包围盒等初步指标 |
| provider_result_id | string nullable | 供应商结果标识 |
| error_code | string nullable | 候选级失败 |
| created_at / updated_at | datetime | 时间 |

#### assets

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| project_id | UUID | 项目归属 |
| name | string | 符合模板的资产名 |
| asset_type | enum | prop |
| status | enum | needs_fix / ready / deleted |
| approved_version_id | UUID nullable | 当前通过版本 |
| created_at / updated_at | datetime | 时间 |

#### asset_versions

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| asset_id | UUID | 所属资产 |
| parent_version_id | UUID nullable | 父版本 |
| source_candidate_id | UUID nullable | 来源候选 |
| version_number | integer | 单资产递增 |
| model_file_id | UUID | 模型文件 |
| params | JSONB | 生成和处理参数快照 |
| model_version | string | 模型版本 |
| spec_snapshot | JSONB | 提交时项目规格 |
| checksum | string | 版本完整性 |
| internal_cost | decimal nullable | 内部成本，不面向用户 |
| created_at | datetime | 创建时间 |

#### qa_reports

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| asset_version_id | UUID | 对应版本 |
| rule_set_version | string | 规则版本 |
| ready_score | decimal | 解释分数 |
| has_block | boolean | 是否存在阻断 |
| results | JSONB | 六维检测值、目标值、结果、建议 |
| created_at | datetime | 创建时间 |

Alpha 不实现高风险豁免。临时技术美术验收记录不得覆盖 Block，只能作为反馈进入下一规则版本。

#### exports

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| asset_version_id | UUID | 导出版本 |
| target | enum | unity_urp_mobile 等 |
| format | enum | glb / fbx / obj |
| state | enum | queued / running / ready / failed |
| package_file_id | UUID nullable | 导出包 |
| manifest | JSONB | 导出清单 |
| diagnostic_id | string | 诊断编号 |
| created_at / finished_at | datetime | 时间 |

### 6.3 文件目录和清理

- 上传文件先进入 quarantine，校验通过后移动到 uploads。
- 生成文件使用 UUID 路径，不使用用户文件名拼接真实路径。
- 导出包按资产版本生成，不覆盖旧包。
- 失败任务保留诊断所需元数据；无业务引用的临时中间文件按可配置周期清理。
- 删除资产使用软删除；本阶段不自动物理清除历史版本。
- 任何下载都通过后端授权或短时签名地址，不直接暴露磁盘路径。

### 6.4 任务状态机

采用 PRD 状态：

**DRAFT → VALIDATING → QUEUED → PREPROCESSING → GEOMETRY → TEXTURING → POST_PROCESSING → QA → READY / NEEDS_FIX / FAILED / CANCELLED**

规则：

- VALIDATING 检查输入、格式、项目规格和供应商配置。
- QUEUED 前必须先持久化任务。
- Worker 使用租约认领任务，租约超时后可安全恢复。
- 已成功并持久化的候选不会因其他候选重试而重新生成。
- 只重试网络、限流、超时和供应商临时错误；参数、安全、格式和未配置 Key 不自动重试。
- 用户取消只停止未开始或供应商支持中止的步骤，已经持久化的结果保留。
- QA 存在任何 Block 时进入 NEEDS_FIX；无 Block 时进入 READY。
- 所有终态必须写入 finished_at、诊断 ID 和最终错误/结果。
- 迁移新增状态时必须兼容旧数据，不修改历史状态含义。

## 七、API / 工具设计

### 7.1 通用约定

- API 前缀：/api/v1。
- JSON 字段使用 snake_case。
- 成功响应返回 data；列表响应可附带 meta。
- 错误响应统一为：

~~~json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "可向用户展示的中文或英文信息",
    "diagnostic_id": "diag_xxx",
    "details": []
  }
}
~~~

- 错误信息根据请求语言返回 zh-CN 或 en，错误码保持不变。
- API 不返回程序堆栈、供应商秘密、数据库信息和本地文件路径。
- 创建任务必须带 Idempotency-Key 请求头。

### 7.2 接口清单

#### 健康与配置

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /api/v1/health | 检查 API 和数据库 |
| GET | /api/v1/capabilities | 返回当前模型模式、资产类型、模板、格式和语言，不返回秘密 |

#### 项目

| 方法 | 路径 | 请求/响应要点 |
| --- | --- | --- |
| POST | /api/v1/projects | 创建名称、模板、单位、轴向、面数和纹理规格 |
| GET | /api/v1/projects | 返回项目列表 |
| GET | /api/v1/projects/{project_id} | 返回项目和当前规格 |
| POST | /api/v1/prompts/analyze | 检查描述清晰度；信息不足时返回最多 3 个结构化追问，不创建生成任务 |
| PATCH | /api/v1/projects/{project_id} | 更新后续任务规格，不修改历史版本 |

无效模板组合返回 INVALID_SPEC_PROFILE。

#### 上传

| 方法 | 路径 | 请求/响应要点 |
| --- | --- | --- |
| POST | /api/v1/files/reference-images | 上传单张 PNG/JPG/WebP，返回 file_id 和安全预览 |
| DELETE | /api/v1/files/reference-images/{file_id} | 移除尚未提交生成的参考图 |

校验扩展名、真实 MIME、解码结果、尺寸、大小和安全文件名。错误码包括 UNSUPPORTED_FILE_TYPE、FILE_TOO_LARGE、INVALID_IMAGE 和 FILE_QUARANTINED。

#### 生成任务

| 方法 | 路径 | 请求/响应要点 |
| --- | --- | --- |
| POST | /api/v1/generation-tasks | 创建文本或单图生成任务，立即返回 task_id、state、diagnostic_id |
| GET | /api/v1/generation-tasks/latest | 恢复最近任务、参考图来源和候选 |
| GET | /api/v1/generation-tasks/{task_id} | 返回状态、阶段、候选和恢复入口 |
| GET | /api/v1/generation-tasks/{task_id}/events | SSE 任务进度和候选渐进事件 |
| POST | /api/v1/generation-tasks/{task_id}/cancel | 请求取消未完成步骤 |
| POST | /api/v1/generation-tasks/{task_id}/candidates/{candidate_id}/select | 选择候选并创建资产与 v001 |

创建请求最小字段：

~~~json
{
  "project_id": "uuid",
  "asset_type": "prop",
  "prompt": "低多边形风格的青铜宝箱",
  "reference_file_id": "front-uuid",
  "reference_file_ids": ["front-uuid", "left-uuid", "back-uuid", "right-uuid"],
  "candidate_count": 4,
  "quality_tier": "standard"
}
~~~

概念图接口 `POST /api/v1/concept-images` 返回持久化 `concept_bundle_id`、视图、独立配件、`ready_for_3d` 与质量警告；`GET /api/v1/concept-images/latest` 和 `GET /api/v1/concept-images/{id}` 用于刷新恢复与查看原图。未通过质量门禁的图组不能提交 3D，重新生成必须由用户显式触发，避免自动重复计费。

基础 Schema 要求 prompt 与参考图至少一个存在；真实 3D 路由要求至少一个 `reference_file_ids`。道具为一张主参考图，人物允许且仅按正、左、后、右顺序传四张；`reference_file_id` 保留为首图兼容字段。candidate_count 只允许 1、2、4。

#### 资产、版本与 QA

| 方法 | 路径 | 请求/响应要点 |
| --- | --- | --- |
| GET | /api/v1/assets/{asset_id} | 返回资产、当前版本和状态 |
| GET | /api/v1/assets/{asset_id}/versions | 返回不可变版本树 |
| GET | /api/v1/asset-versions/{version_id} | 返回参数、来源、文件、指标和血缘 |
| GET | /api/v1/asset-versions/{version_id}/qa | 返回六维 QA 和每条证据 |
| POST | /api/v1/asset-versions/{version_id}/qa/run | 创建可恢复的 QA 任务 |

本阶段不提供绕过 Block 的豁免接口。

#### 导出

| 方法 | 路径 | 请求/响应要点 |
| --- | --- | --- |
| POST | /api/v1/asset-versions/{version_id}/exports | 创建指定引擎和格式的导出任务 |
| GET | /api/v1/exports/{export_id} | 返回导出状态、manifest 摘要和诊断 ID |
| GET | /api/v1/exports/{export_id}/download | READY 后下载短时有效导出包 |

存在 QA Block 时返回 QA_BLOCKED；包未就绪返回 EXPORT_NOT_READY。

### 7.3 SSE 约定

事件序列：

**chunk 零到多次 → done 或 error，且终态事件必有且只有一个。**

chunk 示例：

~~~text
event: chunk
data: {"type":"candidate_ready","task_id":"...","candidate":{"id":"...","index":1,"preview_url":"..."}}
~~~

done 示例：

~~~text
event: done
data: {"task_id":"...","state":"READY","candidate_count":4,"succeeded":3,"failed":1}
~~~

error 示例：

~~~text
event: error
data: {"error":{"code":"PROVIDER_TIMEOUT","message":"生成服务暂时不可用，请稍后重试","diagnostic_id":"diag_xxx"}}
~~~

断流不是状态事实。前端断线后必须调用 GET 任务接口恢复，并可使用 Last-Event-ID 或数据库事件序号继续订阅。

### 7.4 统一错误码

- VALIDATION_ERROR
- INVALID_SPEC_PROFILE
- UNSUPPORTED_FILE_TYPE
- FILE_TOO_LARGE
- INVALID_IMAGE
- FILE_QUARANTINED
- TASK_NOT_FOUND
- INVALID_STATE_TRANSITION
- IDEMPOTENCY_CONFLICT
- MODEL_PROVIDER_NOT_CONFIGURED
- PROVIDER_UNAVAILABLE
- PROVIDER_TIMEOUT
- MODEL_OUTPUT_INVALID
- ASSET_PROCESSING_FAILED
- QA_BLOCKED
- EXPORT_NOT_READY
- INTERNAL_ERROR

## 八、Prompt 设计

### 8.1 提示词结构化 Prompt

职责：将中文或英文用户描述整理为可编辑、可校验的 3D 生成规格，不替用户增加受保护 IP、品牌、艺术家模仿或未要求的内容。

输入变量：

- locale。
- original_prompt。
- asset_type。
- project_spec。
- negative_terms。
- 可选参考图分析结果。

输出为严格 JSON：

~~~json
{
  "subject": "",
  "style": "",
  "materials": [],
  "era": "",
  "scale_hint": "",
  "view_hint": "",
  "negative_terms": [],
  "normalized_prompt_zh": "",
  "provider_prompt_en": ""
}
~~~

规则：

- 保留用户原始输入，不用规范化结果覆盖原文。
- 中文输入必须生成可供用户核对的中文字段。
- 英文切换只影响界面和解释语言，不静默改写用户原始输入。
- 若主体、风格或关键细节不足以支持当前生成，返回 `ready_to_generate=false` 和最多 3 个必要问题；先问主体方向，道具检查材质/结构，人物只检查外观服装/姿态。每个问题返回 4 个 `options`（`value`、`label`、`description`），前端另提供“其他/自定义”。
- 追问必须说明所缺信息，不得诱导用户增加未要求的题材、品牌、受保护 IP 或艺术家模仿。
- 用户回答与原描述合并后必须在界面可见；用户确认前不创建任务、不产生供应商费用。
- Prompt 文件独立版本化，记录 prompt_version。
- 输出由确定性解析器和 Pydantic 校验；失败有限重试，仍失败返回 MODEL_OUTPUT_INVALID。
- 不保存或展示模型思维链。
- 正式接入时为格式约束补充正例和禁止反例。

### 8.2 3D 供应商请求构建

职责：把结构化 Prompt、参考图、项目规格、候选数和质量档转换为供应商参数。

规则：

- 供应商不支持的参数必须显式记录，不能假装已生效。
- 每个技术目标必须同时记录 `requested_value`、`provider_parameter`、`measured_value` 和检测结论。
- 每个候选记录供应商任务 ID、模型版本、参数和可复现标识。
- 供应商返回先进入隔离区，完成文件解析和完整性检查后才能成为候选。
- 候选独立持久化和失败补偿。

### 8.3 QA 解释

Alpha 的 QA 结论由确定性规则产生，不使用 LLM 决定 Pass 或 Block。

- 每条规则使用中英文模板解释检测值、目标值、影响和建议。
- Ready Score 按 PRD：30% 几何 + 25% 规格 + 20% 材质 + 10% 绑定 + 5% 命名 + 10% 许可证。
- 静态道具未启用绑定时，绑定项显示 Not Applicable，并按冻结后的规则重新归一；不得伪造 Pass。
- 任一 Block 都阻止 READY，分数不能覆盖阻断。
- 具体几何阈值和模板数值使用版本化配置；临时值必须在界面和报告中标记为 Alpha 规则。

## 九、正式前端纵向切片

### 9.1 定位

本阶段界面是正式 Web 产品的第一条纵向切片，不是一次性调试页。只建设判断核心价值必需的页面和交互。

### 9.2 页面

1. 项目列表与建项页：创建项目，选择 Unity URP Mobile 等模板，查看默认规格。
2. 生成工作台：填写文本、上传单图、选择候选数和质量档，查看结构化提示词；信息完整后进入独立的生成前确认卡，不直接付费调用。
3. 任务与候选区：显示真实阶段、候选部分成功、失败原因和取消入口，不展示伪精确百分比。
4. 候选比较：最多四个候选并排或切换预览，支持旋转、缩放、线框和基础指标比较。
5. 资产详情：展示版本、来源、参数、3D 预览、QA 结果和导出入口。
6. 导出面板：选择目标模板和格式，展示包内容，完成后下载。

### 9.3 国际化

- 首次进入默认 zh-CN。
- 页面顶部提供“中文 / English”切换。
- 语言选择写入用户本地偏好，刷新后保持。
- 路由、导航、按钮、表单、状态、错误、QA 解释和空状态全部使用国际化键。
- 资产名、用户 Prompt 和上传文件名不因切换语言而自动翻译。
- 中文或英文缺少翻译键时测试失败，不允许生产界面直接显示键名。

### 9.4 交互边界

- 桌面端完成全流程。
- 移动端只保证页面可打开和基本查看，不实现完整 3D 编辑。
- 3D 文件过大时提供缩略图或降级预览，并明确提示。
- 运行中展示阶段、已持久化候选、取消边界和诊断 ID。
- 不展示模型思维链、虚假倒计时或商业额度。
- 不建设社区、商业化、团队后台和插件页面。

## 十、测试要求

### 10.1 第一层：mock 自动化测试

#### 后端单元测试

- 项目规格合法与非法组合。
- 中英文 Prompt 请求校验。
- prompt 与 reference_file_id 至少一个存在。
- 图片扩展名伪装、错误 MIME、损坏图片、超限尺寸和路径遍历。
- 状态机每条允许和禁止转换。
- 同一幂等键重复提交只产生一个任务。
- Worker 租约、心跳、超时认领和进程重启恢复。
- 候选 4 个全成功、部分失败、全部失败、超时、取消。
- 已成功候选不会因失败分支重试而重复生成。
- SDK 初始化失败、无 Key、错误 Key、超时和有限重试的统一错误。
- 模型结构化输出正确、常见等价格式、格式错误和超量内容。
- 模糊描述触发带选项的针对性追问，主体选择会决定下一轮显示道具细节或人物细节；完整描述不重复追问，回答前不会创建生成任务。
- 版本不可变和父版本血缘。
- GLB 可解析、空网格、面数、单位、轴向、材质和纹理引用 QA。
- Block 阻止 READY 和导出。
- Ready Score 计算和 Not Applicable 处理。
- manifest、qa_report 和 license 文件完整。
- 导出包校验和、短时下载和越权路径。
- 日志脱敏，不出现 Key、数据库密码、本地绝对路径和完整私有输入。

#### 后端集成测试

- API → PostgreSQL → Worker → 文件存储 → QA → 导出完整链路。
- 后端、Worker 分别重启后的任务恢复。
- SSE 正常完成、错误完成和中途断线后的轮询恢复。
- 数据库提交失败时不得发送完成事件。
- 并发重复提交不重复创建或处理。

#### 前端测试

- 默认中文和英文切换。
- 关键国际化键完整。
- 创建项目和规格错误提示。
- 文本/单图提交。
- 运行状态、部分成功、失败、取消和恢复。
- 四候选展示和明确选中。
- 3D 查看器加载成功与降级状态。
- QA Pass/Warning/Block 证据展示。
- Block 时禁用导出并解释原因。
- READY 后导出和下载。
- 刷新页面后恢复项目、任务和语言。

### 10.2 第二层：真实模型与真实文件冒烟

真实 API 确认后执行：

1. 使用一条中文静态道具描述生成 4 个候选。
2. 使用一张拥有必要权利的参考图生成候选。
3. 记录供应商、模型版本、首个候选时间、总耗时、成功候选数、重试、内部成本和错误。
4. 选择一个候选，完成确定性 QA 和 GLB 导出。
5. 在 Unity URP Mobile 样例工程导入，核对尺度、轴向、原点、材质、纹理、命名和视觉表现。
6. 使用 curl -N 验证 SSE 以 done 或 error 正确收尾。
7. 使用固定 Alpha 基准集计算首次技术通过率，并如实记录失败分布。

产品效果人工判断项：

- 主体是否符合输入。
- 轮廓、比例和整体风格是否可用于游戏原型。
- 四候选是否存在有意义差异，而不是近似重复。
- 材质和纹理是否出现系统性破损。
- 为达到可用状态所需的重生成次数是否可接受。

这些人工判断不得被格式校验或 Ready Score 代替。

### 10.3 安全和恢复测试

- 恶意文件名、路径遍历、压缩炸弹样例和超大文件。
- 未授权磁盘路径不可通过下载接口访问。
- 服务或 Worker 在各任务阶段强制退出后能够恢复或明确失败。
- 失败任务有诊断 ID、错误码和可操作恢复入口。
- 删除为软删除，历史版本和导出记录不被静默破坏。
- 日志和错误响应不泄露堆栈或秘密。

## 十一、产品经理验收清单

### 11.1 工程链路验收

- [ ] 按 README 启动后，浏览器能打开产品，不需要阅读代码。
- [ ] 首次打开默认为中文，点击“English”后页面切换为英文，刷新后仍保持选择。
- [ ] 新建项目，选择“Unity URP Mobile”，能看到单位、轴向、面数和纹理等默认规格。
- [ ] 修改项目规格后，新任务使用新规格，旧资产版本仍显示原规格。
- [ ] 输入一条中文静态道具描述，提交前能查看并编辑系统整理出的结构化字段。
- [ ] 上传一张 PNG/JPG/WebP 参考图，错误格式或损坏文件会说明具体原因。
- [ ] 选择 4 个候选并提交后，页面立即显示任务已创建，不会一直卡住请求。
- [ ] 运行中只显示真实阶段，不显示伪精确进度或模型思维链。
- [ ] 候选逐个出现；模拟一个候选失败后，其余成功候选仍可查看和选择。
- [ ] 刷新浏览器后，任务状态和已出现候选仍然存在。
- [ ] 关闭并重启后端或 Worker 后，任务能够继续，或明确显示失败原因和恢复入口。
- [ ] 重复点击提交不会创建两份相同任务。
- [ ] 3D 预览可以旋转、缩放和切换线框；加载失败时有明确降级提示。
- [ ] 可以清楚选中一个候选，并看到资产 v001 和来源信息。
- [ ] QA 页面按几何、规格、材质、绑定、命名、许可证展示结果、检测值、目标值和建议。
- [ ] 制造一个 Block 后，资产显示 NEEDS_FIX，导出按钮不可用并解释原因。
- [ ] 无 Block 时资产显示 READY，可以生成并下载 GLB 资产包。
- [ ] 解压资产包能看到模型、纹理、manifest、qa_report 和 license；清单与页面选择一致。
- [ ] 所有失败状态都能看到用户可理解的原因和诊断 ID，看不到程序堆栈。
- [ ] 整个流程没有充值、套餐、额度钱包、扣费或支付入口。

### 11.2 真实效果验收

- [ ] 在提供真实 API Key 前，已先看到并确认供应商、效果、费用和数据使用说明。
- [ ] 使用中文文本真实生成 4 个候选，至少一个候选可在浏览器中正常预览。
- [ ] 使用单张参考图真实生成候选，结果与参考主体存在可接受的一致性。
- [ ] 产品经理人工确认候选具备游戏原型使用价值。
- [ ] 选中候选后完成真实 QA 和 GLB 导出。
- [ ] GLB 在 Unity URP Mobile 中成功导入，尺度、轴向、原点、材质、纹理和命名符合模板。
- [ ] 至少一个真实资产从建项到通过 QA 并导出的总耗时不超过 15 分钟。
- [ ] 固定 Alpha 基准集首次技术通过率达到 60% 及以上。
- [ ] 真实测试报告如实列出成功、失败、耗时和内部成本，没有用 mock 结果代替。

模型输出中不影响结构和导入的细微视觉瑕疵，由产品经理按“是否值得继续迭代、是否能用于游戏原型”人工判断容忍度。

## 十二、风险与待确认项

### 12.1 已知风险

| 风险 | 当前处理 |
| --- | --- |
| 真实 3D 供应商尚未选择 | 先完成适配层和 mock；接入前与产品经理讨论 |
| 中国大陆访问、数据跨境和模型训练政策不确定 | API 决策时单独列明，不默认上传真实私有素材 |
| 产品效果优先可能带来高调用成本 | 不设商业额度，但保留内部成本和异常成本上限；真实批量测试前确认预算 |
| Web 预览大模型性能 | GLB 优先，提供缩略图和降级预览，记录首帧时间 |
| FBX 工具链兼容性 | 先以 GLB 完成主链路，FBX 通过 Blender 和 Unity/Unreal 样例验证后启用 |
| QA 阈值尚未完全冻结 | 使用版本化 Alpha 规则，依据基准资产和技术美术反馈迭代 |
| 本地缺少 Python 3.11、PostgreSQL、Blender | 开工前分步安装并验证真实路径，不依赖系统 Python 3.9 |
| Alpha 不含正式认证与租户隔离 | 仅限本地或受控内部验证；外部用户测试前必须补认证和对象存储 |
| 中英文文案产生含义偏差 | 错误码和规则保持同一语义源，两种语言分别验收 |

### 12.2 已确认决策

- 首发市场：中国大陆。
- 默认语言：简体中文。
- 可切换语言：英文。
- 当前优先级：真实产品效果和游戏资产可用性优先。
- 商业功能：本阶段不做。
- 首条切片：静态道具 + Unity URP Mobile + GLB。
- 角色绑定：达到 80% 且失败可解释后进入正式 MVP，否则保持 Early Access。
- API：需要时先讨论，产品经理确认后提供。

### 12.3 后续待确认

- 提示词理解 API 的供应商和模型。
- 文本/单图转 3D API 的供应商、模型、价格和数据政策。
- 真实冒烟和 Alpha 基准集允许使用的 API 测试预算。
- 四个项目模板的最终技术美术规则和基准资产。

这些事项不阻塞 mock 工程链路开发，但阻塞真实效果完成门。

## 十三、交接给下一阶段

本阶段完成后，下一阶段可直接复用：

- 稳定的项目规格、任务状态机、幂等和恢复机制。
- 模型供应商适配层及已经验证的真实供应商。
- 资产、不可变版本、QA 和导出数据契约。
- GLB/FBX 处理、确定性 QA 和 manifest 打包能力。
- 正式 Next.js 前端、3D 查看器和中英文国际化框架。
- Alpha 基准集、真实效果报告和 Unity/Unreal 导入样例。
- mock、集成、恢复、安全和真实冒烟测试。

只有第一阶段两道完成门均通过，才进入下一阶段。下一阶段候选范围为：更多静态资产模板、PBR/重拓扑增强、链接评审、外部测试所需的认证与对象存储。具体范围必须根据 Alpha 的生成效果、失败分布和用户验收结果重新出一份技术适配摘要，不自动把全部 P1 功能纳入。
