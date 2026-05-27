# qushiuyin

短视频去水印网页程序项目。

当前阶段：第三阶段处理中。已支持抖音、快手链接识别、任务创建、任务进度查询、视频上传、手动水印区域设置、FFmpeg 局部模糊处理和真实 MP4 下载。抖音/快手链接直取源视频仍需要接入授权获取模块。

当前已完成开发文档：

- [短视频去水印网页程序开发文档](docs/short-video-watermark-remover-dev.md)

## 技术栈

- 前端：Next.js + TypeScript
- 后端：FastAPI + Pydantic
- 后续处理：FFmpeg / OpenCV
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

## 当前功能

- 抖音链接识别。
- 快手链接识别。
- 支持从分享文案里提取第一个链接。
- 创建链接任务。
- 上传 MP4 / MOV / M4V / WEBM 视频并处理。
- 使用 FFmpeg 对常见角标水印区域进行局部模糊。
- 上传前可在视频预览上配置最多 5 个水印区域。
- 网页端轮询任务进度。
- 上传任务完成后下载真实 MP4。

## 处理策略

当前 FFmpeg 滤镜支持两种区域来源：

- 手动区域：前端以百分比坐标传给后端，适配不同分辨率。
- 默认区域：未设置手动区域时，使用左上角和右下角常见水印区域。

后续会加入拖拽式框选、自动水印检测和局部修复算法。

## 下一步

- 接入抖音/快手授权视频获取模块。
- 增加拖拽式框选水印区域。
- 将内存任务替换为 Redis 队列和 PostgreSQL。
- 增加 Linux 部署配置。

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
```
