# 短视频去水印网页程序开发文档

## 1. 项目目标

开发一个通过网页打开的短视频处理工具。用户复制短视频链接后粘贴到网页中，系统解析视频信息，生成处理任务，并输出去除可见水印后的新视频文件。

本项目建议定位为“个人素材清理与已授权内容处理工具”，仅允许处理用户本人拥有版权、已获授权或平台允许下载/二次处理的视频，避免用于绕过平台版权、水印声明或访问控制。

## 2. 核心功能

### 2.1 MVP 功能

- 网页端粘贴短视频链接。
- 后端校验链接格式与平台来源。
- 解析视频基础信息：标题、封面、时长、分辨率、来源平台。
- 创建视频处理任务。
- 通过授权视频源服务获取源视频文件。
- 检测常见固定位置水印区域。
- 使用裁剪、模糊、填充或图像修复方式处理水印。
- 生成处理后的视频。
- 网页端展示任务进度。
- 支持处理完成后下载结果文件。
- 任务失败时展示明确错误原因。

### 2.2 后续增强

- 支持链接任务历史与失败重试。
- 支持多水印区域处理。
- 支持预览处理效果。
- 支持保留原始分辨率、码率、帧率。
- 支持批量链接处理。
- 支持账号登录与历史任务列表。
- 支持对象存储保存原视频与结果视频。
- 支持管理员查看任务、失败日志和系统负载。

## 3. 合规与产品边界

### 3.1 必须限制

- 页面需明确提示：仅可处理本人拥有版权或已获授权的视频。
- 不提供绕过付费、登录、地区限制、私密视频、DRM 或平台访问控制的能力。
- 不承诺支持所有平台链接。
- 不保存解析到的视频超过必要期限。
- 默认给处理结果添加处理记录或内部任务编号，便于审计。

### 3.2 风险控制

- 对来源平台设置白名单。
- 对单个任务的视频大小、时长和处理频率做限制。
- 对可疑高频请求启用验证码或登录限制。
- 下载模块只允许访问可信视频资源地址，避免 SSRF。
- 定期清理临时文件。

## 4. 推荐技术架构

### 4.1 总体架构

```text
Browser
  |
  | HTTPS
  v
Web Frontend (Next.js)
  |
  | REST API / WebSocket
  v
API Server (FastAPI)
  |
  | create job / query job
  v
PostgreSQL + Redis
  |
  | queue
  v
Worker Service
  |
  | FFmpeg / OpenCV
  v
Local Storage or S3-compatible Object Storage
```

### 4.2 技术选型

前端：

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui 或自定义基础组件
- React Query 或 SWR

后端：

- Python FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Redis
- Celery 或 RQ
- FFmpeg
- OpenCV

存储：

- 开发环境：本地文件系统
- 生产环境：MinIO、阿里云 OSS、腾讯云 COS 或 AWS S3

部署：

- Docker Compose 用于开发和单机部署
- Nginx 作为反向代理
- 后续可迁移到 Kubernetes

## 5. 项目目录结构

```text
qushiuyin/
  apps/
    web/
      src/
        app/
        components/
        features/
        lib/
        styles/
      package.json
      next.config.js
    api/
      app/
        api/
          routes/
        core/
        db/
        models/
        schemas/
        services/
        workers/
      tests/
      pyproject.toml
  packages/
    shared/
      platform-rules/
      types/
  infra/
    docker/
    nginx/
    compose.dev.yml
    compose.prod.yml
  storage/
    tmp/
    originals/
    outputs/
  docs/
    short-video-watermark-remover-dev.md
  README.md
```

## 6. 前端页面设计

### 6.1 页面列表

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| 首页/处理页 | `/` | 粘贴链接、创建任务、查看进度 |
| 任务详情页 | `/jobs/[id]` | 查看视频信息、处理状态、下载结果 |
| 历史任务页 | `/history` | 登录后查看历史任务，MVP 可不做 |
| 管理页 | `/admin/jobs` | 管理任务和失败日志，后续做 |

### 6.2 首页核心交互

1. 用户粘贴短视频链接。
2. 点击“解析”。
3. 前端调用 `POST /api/links/parse`。
4. 展示标题、封面、时长、平台。
5. 用户确认自己拥有处理权限。
6. 点击“开始处理”。
7. 前端调用 `POST /api/jobs`。
8. 页面进入任务进度状态。
9. 通过轮询或 WebSocket 更新状态。
10. 完成后展示下载按钮。

### 6.3 前端状态

```ts
type JobStatus =
  | "pending"
  | "downloading"
  | "analyzing"
  | "processing"
  | "uploading"
  | "completed"
  | "failed"
  | "expired";
```

## 7. 后端模块设计

### 7.1 API 模块

- `links`: 链接校验与解析。
- `jobs`: 创建任务、查询任务、取消任务。
- `files`: 结果文件下载、临时文件访问。
- `health`: 服务健康检查。

### 7.2 Service 模块

- `PlatformResolver`: 识别平台与链接类型。
- `VideoFetcher`: 通过授权服务获取视频源文件。
- `WatermarkDetector`: 检测水印位置。
- `VideoProcessor`: 调用 FFmpeg/OpenCV 处理视频。
- `StorageService`: 管理原文件、临时文件、输出文件。
- `JobService`: 维护任务状态流转。

### 7.3 Worker 模块

任务执行流程：

```text
pending
  -> downloading
  -> analyzing
  -> processing
  -> uploading
  -> completed
```

失败时统一进入：

```text
failed
```

每一步都要记录：

- 当前状态
- 进度百分比
- 错误码
- 错误信息
- 处理日志
- 更新时间

## 8. 数据库设计

### 8.1 video_jobs

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | uuid | 任务 ID |
| source_url | text | 用户提交的原始链接 |
| platform | varchar | 平台标识 |
| title | varchar | 视频标题 |
| cover_url | text | 封面地址 |
| duration_ms | integer | 视频时长 |
| width | integer | 宽度 |
| height | integer | 高度 |
| status | varchar | 任务状态 |
| progress | integer | 0-100 |
| original_file_key | text | 原视频存储 key |
| output_file_key | text | 结果视频存储 key |
| error_code | varchar | 错误码 |
| error_message | text | 错误信息 |
| expires_at | timestamp | 文件过期时间 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

### 8.2 job_events

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 自增 ID |
| job_id | uuid | 任务 ID |
| status | varchar | 状态 |
| message | text | 日志消息 |
| created_at | timestamp | 创建时间 |

## 9. API 设计

### 9.1 解析链接

```http
POST /api/links/parse
Content-Type: application/json
```

请求：

```json
{
  "url": "https://example.com/video/123"
}
```

响应：

```json
{
  "platform": "example",
  "title": "视频标题",
  "coverUrl": "https://cdn.example.com/cover.jpg",
  "durationMs": 15800,
  "width": 1080,
  "height": 1920,
  "canFetchDirectly": true,
  "requiresUpload": false
}
```

### 9.2 创建任务

```http
POST /api/jobs
Content-Type: application/json
```

请求：

```json
{
  "sourceUrl": "https://example.com/video/123",
  "confirmedRights": true,
  "watermarkMode": "auto"
}
```

响应：

```json
{
  "jobId": "6d31029d-f7e0-4f9f-9288-d17a554ac273",
  "status": "pending"
}
```

### 9.3 查询任务

```http
GET /api/jobs/{jobId}
```

响应：

```json
{
  "jobId": "6d31029d-f7e0-4f9f-9288-d17a554ac273",
  "status": "processing",
  "progress": 64,
  "title": "视频标题",
  "outputUrl": null,
  "errorMessage": null
}
```

### 9.4 下载结果

```http
GET /api/jobs/{jobId}/download
```

说明：

- 任务未完成返回 `409 Conflict`。
- 文件过期返回 `410 Gone`。
- 成功时返回临时签名下载地址或文件流。

## 10. 视频处理方案

### 10.1 自动检测策略

MVP 不建议一开始追求复杂 AI 去水印。可以先支持常见固定水印区域：

- 左上角
- 右上角
- 左下角
- 右下角
- 底部标题栏区域

处理步骤：

1. 抽取关键帧。
2. 在候选区域内检测高对比度文字、Logo 或半透明图案。
3. 计算疑似水印矩形区域。
4. 多帧对比确认水印是否稳定存在。
5. 生成 FFmpeg filter 或 OpenCV mask。

### 10.2 处理方式

| 方式 | 优点 | 缺点 | 适用场景 |
| --- | --- | --- | --- |
| 裁剪 | 快、稳定 | 损失画面 | 水印在边缘 |
| 模糊 | 快、实现简单 | 处理痕迹明显 | 低要求场景 |
| 填色/覆盖 | 快 | 视觉生硬 | 背景简单 |
| OpenCV inpaint | 效果较好 | 较慢 | 小面积水印 |
| AI 视频修复 | 效果潜力高 | 成本高、部署复杂 | 后续高级版 |

MVP 推荐：

- 默认使用边缘裁剪或局部模糊。
- 提供“画面完整优先”和“清理痕迹优先”两个模式。
- 后续再引入 OpenCV inpaint。

### 10.3 FFmpeg 示例

边缘裁剪：

```bash
ffmpeg -i input.mp4 -vf "crop=iw:ih-120:0:0" -c:a copy output.mp4
```

局部模糊：

```bash
ffmpeg -i input.mp4 -filter_complex \
"[0:v]crop=240:80:20:20,boxblur=12[wm];[0:v][wm]overlay=20:20" \
-c:a copy output.mp4
```

## 11. 安全设计

- URL 校验必须使用白名单域名，不直接信任用户输入。
- 下载文件前先做 HEAD 或流式限制，避免超大文件。
- 禁止访问内网地址、回环地址、本地文件协议。
- 所有任务使用独立临时目录。
- 输出文件名不使用用户输入。
- 下载链接使用短期签名。
- API 增加频率限制。
- Worker 设置超时时间。
- FFmpeg 命令使用参数数组，不拼接 shell 字符串。

## 12. 开发环境

### 12.1 本地依赖

- Node.js 20+
- pnpm
- Python 3.11+
- uv 或 Poetry
- Docker Desktop
- FFmpeg
- PostgreSQL
- Redis

### 12.2 本地启动

```bash
docker compose -f infra/compose.dev.yml up -d postgres redis
pnpm install
pnpm --filter web dev
cd apps/api
uv run fastapi dev app/main.py
uv run celery -A app.workers.celery_app worker -l info
```

## 13. 测试计划

### 13.1 后端测试

- 链接解析单元测试。
- URL 安全校验测试。
- 任务状态流转测试。
- Worker 失败重试测试。
- 文件过期清理测试。
- FFmpeg 参数生成测试。

### 13.2 前端测试

- 链接输入校验。
- 解析成功状态。
- 解析失败状态。
- 任务进度展示。
- 下载按钮状态。
- 移动端布局。

### 13.3 集成测试

- 使用本地测试视频创建任务。
- 完成完整处理流程。
- 验证输出文件可播放。
- 验证错误任务可恢复或展示失败原因。

## 14. 里程碑拆分

### 阶段 1：项目骨架

- 创建 monorepo。
- 搭建 Next.js 前端。
- 搭建 FastAPI 后端。
- 配置 PostgreSQL、Redis、Docker Compose。
- 打通健康检查。

### 阶段 2：任务系统

- 创建数据库表。
- 实现任务创建与查询。
- 接入 Redis 队列。
- Worker 可执行模拟任务。
- 前端展示进度。

### 阶段 3：视频处理 MVP

- 支持链接任务获取授权视频源。
- 接入 FFmpeg。
- 实现固定区域裁剪/模糊。
- 输出处理后视频。
- 前端下载结果。

当前实现状态：

- 已通过 `imageio-ffmpeg` 提供本地开发可用的 FFmpeg 二进制。
- 已实现授权视频源服务适配器，配置 `AUTH_SOURCE_API_BASE_URL` 后可获取源视频地址。
- 已提供 `app.dev_mock_source` 用于本地验证完整链接处理链路。
- Linux 生产环境可通过 `FFMPEG_BINARY=/usr/bin/ffmpeg` 使用系统 FFmpeg。
- 当前默认处理策略为左上角和右下角局部模糊。
- 当前任务存储仍为内存版，服务重启后任务记录会丢失。

### 阶段 4：链接解析

- 实现平台白名单。
- 实现链接解析接口。
- 支持一个优先平台。
- 对无法获取授权源的视频返回明确失败原因。

### 阶段 5：自动水印区域

- 抽取关键帧。
- 检测候选水印区域。
- 生成处理参数。
- 前端展示自动检测结果和处理状态。

### 阶段 6：生产化

- 对接对象存储。
- 增加登录、限流、审计日志。
- 增加管理后台。
- 增加任务清理计划。
- 部署到云服务器。

## 15. 我需要你配合确认的内容

1. 优先支持哪个短视频平台。
2. 是否只做网页端，还是后续需要移动端适配。
3. 目标部署环境：本地电脑、Windows 服务器、Linux 服务器或云平台。
4. 单个视频预计最大时长和大小。
5. 是否需要用户登录。
6. 授权视频源服务的接口地址和认证方式。
7. 你更重视处理速度还是画面自然度。

## 16. 推荐 MVP 决策

为了最快做出可运行版本，建议第一版按以下范围开发：

- 网页端单页应用。
- 用户粘贴抖音或快手链接。
- 后端通过授权视频源服务获取源文件。
- 后端 FastAPI + Redis Worker。
- FFmpeg 固定区域模糊和裁剪。
- 本地文件存储。
- 不做登录。
- 结果文件 24 小时后自动删除。

这样可以先验证完整链路，再逐步增强平台解析和自动检测能力。
