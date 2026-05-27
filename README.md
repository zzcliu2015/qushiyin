# qushiuyin

抖音 / 快手链接去水印网页程序。

当前版本只保留链接处理流程：用户粘贴抖音或快手链接，后端通过已配置的授权视频源服务获取源视频，再使用 FFmpeg 进行局部水印区域处理，最后提供 MP4 下载。

> 注意：本项目不内置绕过平台限制的抓取逻辑。源视频必须由你配置的官方、授权或自有服务提供。

开发文档：

- [短视频去水印网页程序开发文档](docs/short-video-watermark-remover-dev.md)

## 技术栈

- 前端：Next.js + TypeScript
- 后端：FastAPI + Pydantic
- 视频处理：FFmpeg
- 后续部署：Linux + Nginx + Docker Compose

## 本地启动

安装前端依赖：

```bash
npm install
```

创建并安装后端虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e apps/api
```

启动后端：

```bash
npm run dev:api
```

启动前端：

```bash
npm run dev:web
```

访问：

- 前端：http://localhost:3000
- 后端健康检查：http://127.0.0.1:8000/health

## 本地联调授权源

仓库内提供一个开发用 mock 授权源服务，方便验证完整链路：

```bash
python -m uvicorn app.dev_mock_source:app --app-dir apps/api --host 127.0.0.1 --port 8010
```

然后启动 API 前设置：

```bash
AUTH_SOURCE_API_BASE_URL=http://127.0.0.1:8010
AUTH_SOURCE_API_TOKEN=dev-token
ALLOW_PRIVATE_SOURCE_URLS=true
```

`ALLOW_PRIVATE_SOURCE_URLS=true` 只建议本地联调用，生产环境保持默认 `false`。

## 当前功能

- 抖音链接识别。
- 快手链接识别。
- 支持从分享文案里提取第一个链接。
- 登记自有/已授权视频源。
- 创建链接处理任务。
- 优先从本地授权源登记中获取源视频地址。
- 本地未登记时，通过授权视频源服务获取源视频地址。
- 下载授权源视频到本地任务目录。
- 使用 FFmpeg 对常见角标水印区域进行局部模糊。
- 网页端轮询任务进度。
- 任务完成后下载处理后的 MP4。

## 自有/授权视频源登记

当前网页提供“登记授权源”区域。你需要填写：

- 抖音或快手作品链接。
- 自有或已授权的 MP4 源视频地址。
- 标题，可选。
- 授权确认。

登记后，处理区只需要粘贴同一个抖音/快手作品链接即可。后端会从 `storage/authorized-sources.json` 找到对应源视频地址，再下载和处理。

该 JSON 文件已被 `.gitignore` 忽略，不会提交到仓库。

## 授权视频源服务

如果你后续有独立授权源服务，也可以继续使用以下配置作为兜底。处理任务会先查本地登记，查不到时再调用该服务。

后端需要配置：

```bash
AUTH_SOURCE_API_BASE_URL=https://your-authorized-source-service.example
AUTH_SOURCE_API_TOKEN=your-token
```

该服务需要提供：

```http
POST /resolve
Content-Type: application/json
Authorization: Bearer your-token
```

请求：

```json
{
  "platform": "douyin",
  "sourceUrl": "https://v.douyin.com/example/"
}
```

响应：

```json
{
  "downloadUrl": "https://authorized-cdn.example/video.mp4",
  "title": "可选标题"
}
```

## Linux 部署提示

生产环境建议安装系统 FFmpeg：

```bash
sudo apt update
sudo apt install -y ffmpeg
```

然后在环境变量中配置：

```bash
FFMPEG_BINARY=/usr/bin/ffmpeg
STORAGE_ROOT=/data/qushiuyin/storage
MAX_SOURCE_VIDEO_MB=200
```

## 下一步

- 将内存任务替换为 Redis 队列和 PostgreSQL。
- 增加 Linux Docker Compose 生产配置。
- 增加任务过期清理。
