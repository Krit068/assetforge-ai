# AssetForge AI

AssetForge AI 是一个面向游戏开发者和美术团队的 AI 3D 素材生成工作台。用户可以通过文字或参考图描述角色、道具和场景资产，经过需求补全、概念图确认、AI 建模、在线预览和技术质检，最终导出 GLB 模型。

## 项目内容

本仓库包含完整的前后端原型和产品文档：

- `frontend/`：基于 React 19、TypeScript、Tailwind CSS 和 React Three Fiber 的科技风 Web 工作台。
- `backend/`：基于 FastAPI、SQLAlchemy 和 Alembic 的生成任务、文件、质检与导出 API。
- 根目录 Markdown 文档：产品 PRD、阶段开发文档、前端技术栈手册和技术适配声明。

## 核心功能

- Meshy 风格的对话式生成入口，进入工作区后采用左侧交流、右侧 3D 预览的双栏布局。
- 文字生成与参考图生成，支持上传、格式/尺寸校验、预览、替换和移除图片。
- 人物/道具需求清晰度检查；信息不足时优先追问，不直接创建付费任务。
- Seedream 概念图和人物多视图链路，包含建模前质量门禁。
- Tripo 异步 3D 生成，支持 SSE 实时进度、断流后查询恢复、任务取消和诊断 ID。
- 默认选择最高约 200 万面的高模源文件，可切换为最高 20K 面的游戏就绪版本。
- 在线 3D 旋转、缩放和候选模型预览，并显示面数、顶点数和 PBR 信息。
- 任务中心、资产库、帮助中心、项目设置和中英文切换。
- 安全的 GLB 导出接口与前端下载入口。
- 生成前确认、前端防重复提交、后端幂等键和付费请求零自动重试，减少误触与重复扣费风险。

## 当前状态

第二阶段核心纵向链路已完成：输入/上传 → 概念图确认 → 3D 生成 → 任务恢复 → 模型预览 → GLB 导出。自动化测试使用 mock 供应商，不调用付费生成 API。Unity URP 一键交付尚未实现。

高质量多视图链路已通过模拟供应商测试，尚未执行新的付费效果验收；接口通过不等同于人物视觉质量验收。

## 一键启动前的环境

- 项目已准备 Python 3.11 虚拟环境：.venv
- 前端要求 Node.js 22 LTS；当前机器可使用已安装 Node 运行预览
- 前端端口：3000
- 后端端口：8010（8000 已被本机其他进程占用）

## 启动后端

~~~bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
~~~

API 文档：http://127.0.0.1:8010/docs

## 启动前端

~~~bash
cd frontend
npm run dev
~~~

本地页面：http://localhost:3000

## 自动化验证

~~~bash
cd backend
../.venv/bin/python -m pytest

cd ../frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
~~~

`test:e2e` 使用受控的浏览器 API Mock 验证语言持久化、任务 URL、候选展示和刷新恢复，不调用真实付费模型。真实前后端效果仍需按阶段完成门单独冒烟验收。

## 数据库说明

阶段目标数据库是 PostgreSQL。配置 PostgreSQL 后，将根目录 .env 中的 ASSETFORGE_DATABASE_URL 设置为 postgresql+psycopg://...，然后执行：

~~~bash
cd backend
../.venv/bin/alembic upgrade head
~~~

当前默认 SQLite 只为解决本机尚未安装 PostgreSQL 时的本地脚手架运行和测试，不作为 Alpha 持久化验收结论。

## API Key

真实 Key 只写入未提交的 .env：

~~~text
ASSETFORGE_MODEL_PROVIDER=tripo_official
ASSETFORGE_MODEL_API_BASE_URL=https://tokenhub.tencentmaas.com
ASSETFORGE_MODEL_API_KEY=TokenHub密钥
ASSETFORGE_TRIPO_API_BASE_URL=https://api.tripo3d.ai/v2/openapi
ASSETFORGE_TRIPO_API_KEY=Tripo官方tsk_密钥
ASSETFORGE_TRIPO_MODEL_VERSION=P1-20260311
~~~

不要把真实 Key 写入前端、Git、日志、截图或聊天内容。
