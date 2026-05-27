"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clipboard,
  Download,
  FileVideo,
  Link2,
  Loader2,
  Plus,
  Play,
  RotateCcw,
  Search,
  ShieldCheck
} from "lucide-react";
import {
  createJob,
  getJob,
  JobResponse,
  Platform,
  parseLink,
  ParseLinkResponse,
  toApiUrl,
  uploadJob,
  WatermarkRegion
} from "@/lib/api";

const statusLabels: Record<JobResponse["status"], string> = {
  pending: "排队中",
  downloading: "获取视频",
  analyzing: "分析水印",
  processing: "处理中",
  uploading: "保存结果",
  completed: "已完成",
  failed: "失败",
  expired: "已过期"
};

const defaultWatermarkRegions: WatermarkRegion[] = [
  { x: 0, y: 0, width: 0.34, height: 0.09 },
  { x: 0.64, y: 0.9, width: 0.36, height: 0.08 }
];

export default function HomePage() {
  const [url, setUrl] = useState("");
  const [parsed, setParsed] = useState<ParseLinkResponse | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [confirmedRights, setConfirmedRights] = useState(false);
  const [uploadRights, setUploadRights] = useState(false);
  const [uploadPlatform, setUploadPlatform] = useState<Platform>("douyin");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [watermarkRegions, setWatermarkRegions] = useState<WatermarkRegion[]>([
    ...defaultWatermarkRegions
  ]);
  const [activeRegionIndex, setActiveRegionIndex] = useState(0);
  const [loading, setLoading] = useState<"parse" | "job" | "upload" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canStart = Boolean(parsed && confirmedRights && loading !== "job");
  const isRunning = Boolean(
    job && !["completed", "failed", "expired"].includes(job.status)
  );

  const progressLabel = useMemo(() => {
    if (!job) return "等待任务";
    return `${statusLabels[job.status]} · ${job.progress}%`;
  }, [job]);

  useEffect(() => {
    if (!job || !isRunning) return;

    const timer = window.setInterval(async () => {
      try {
        const latest = await getJob(job.jobId);
        setJob(latest);
      } catch (err) {
        setError(err instanceof Error ? err.message : "任务状态查询失败");
      }
    }, 1200);

    return () => window.clearInterval(timer);
  }, [job, isRunning]);

  useEffect(() => {
    if (!uploadFile) {
      setPreviewUrl(null);
      return;
    }

    const nextUrl = URL.createObjectURL(uploadFile);
    setPreviewUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [uploadFile]);

  async function handleParse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setParsed(null);
    setJob(null);

    if (!url.trim()) {
      setError("请粘贴抖音或快手视频链接");
      return;
    }

    try {
      setLoading("parse");
      const result = await parseLink(url.trim());
      setParsed(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "链接解析失败");
    } finally {
      setLoading(null);
    }
  }

  async function handleCreateJob() {
    if (!parsed) return;

    try {
      setError(null);
      setLoading("job");
      const result = await createJob({
        sourceUrl: parsed.normalizedUrl,
        confirmedRights,
        watermarkMode: "auto"
      });
      setJob(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务创建失败");
    } finally {
      setLoading(null);
    }
  }

  async function handleUploadJob() {
    if (!uploadFile) {
      setError("请选择要处理的视频文件");
      return;
    }

    try {
      setError(null);
      setParsed(null);
      setLoading("upload");
      const result = await uploadJob({
        file: uploadFile,
        platform: uploadPlatform,
        confirmedRights: uploadRights,
        watermarkRegions
      });
      setJob(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传处理任务创建失败");
    } finally {
      setLoading(null);
    }
  }

  function addWatermarkRegion() {
    setWatermarkRegions((regions) => {
      if (regions.length >= 5) {
        setActiveRegionIndex(4);
        return regions;
      }

      const next = [...regions, { x: 0.32, y: 0.08, width: 0.34, height: 0.1 }];
      setActiveRegionIndex(next.length - 1);
      return next;
    });
  }

  function resetWatermarkRegions() {
    setWatermarkRegions([...defaultWatermarkRegions]);
    setActiveRegionIndex(0);
  }

  function clearWatermarkRegions() {
    setWatermarkRegions([]);
    setActiveRegionIndex(0);
  }

  function updateRegion(index: number, patch: Partial<WatermarkRegion>) {
    setWatermarkRegions((regions) =>
      regions.map((region, regionIndex) =>
        regionIndex === index ? clampRegion({ ...region, ...patch }) : region
      )
    );
  }

  function removeRegion(index: number) {
    setWatermarkRegions((regions) => regions.filter((_, regionIndex) => regionIndex !== index));
    setActiveRegionIndex((current) => Math.max(0, Math.min(current, watermarkRegions.length - 2)));
  }

  async function handlePaste() {
    const text = await navigator.clipboard.readText();
    setUrl(text);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">去</div>
          <div>
            <h1 className="brand-title">抖音 / 快手去水印处理台</h1>
            <p className="brand-subtitle">仅处理本人拥有版权或已获授权的视频素材</p>
          </div>
        </div>
        <div className="status-pill">
          <ShieldCheck size={16} />
          Linux 部署预留
        </div>
      </header>

      <div className="workbench">
        <section className="panel panel-main">
          <h2 className="section-title">创建处理任务</h2>

          <form className="link-form" onSubmit={handleParse}>
            <div className="input-row">
              <input
                className="url-input"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="粘贴抖音或快手视频链接"
              />
              <button
                className="button secondary"
                type="button"
                onClick={handlePaste}
                title="从剪贴板粘贴"
              >
                <Clipboard size={18} />
                粘贴
              </button>
            </div>

            <button className="button" type="submit" disabled={loading === "parse"}>
              {loading === "parse" ? <Loader2 size={18} /> : <Search size={18} />}
              解析链接
            </button>
          </form>

          {error ? (
            <div className="notice error" role="alert">
              <Link2 size={18} />
              <span>{error}</span>
            </div>
          ) : null}

          {parsed ? (
            <div className="result-block">
              <div className="notice">
                <CheckCircle2 size={18} />
                <span>
                  已识别为{parsed.platformLabel}链接。链接直取模块仍在授权接入阶段，
                  现在可以先使用下方上传入口进行真实 FFmpeg 处理。
                </span>
              </div>

              <div className="meta-grid">
                <div className="meta-item">
                  <p className="meta-label">平台</p>
                  <p className="meta-value">{parsed.platformLabel}</p>
                </div>
                <div className="meta-item">
                  <p className="meta-label">获取方式</p>
                  <p className="meta-value">
                    {parsed.requiresUpload ? "需后续接入解析" : "可直接处理"}
                  </p>
                </div>
                <div className="meta-item">
                  <p className="meta-label">处理模式</p>
                  <p className="meta-value">自动</p>
                </div>
              </div>

              <label className="rights-check">
                <input
                  checked={confirmedRights}
                  onChange={(event) => setConfirmedRights(event.target.checked)}
                  type="checkbox"
                />
                <span>我确认该视频为本人所有、已获授权，或平台允许下载和二次处理。</span>
              </label>

              <button className="button" disabled={!canStart} onClick={handleCreateJob}>
                {loading === "job" ? <Loader2 size={18} /> : <Play size={18} />}
                开始处理
              </button>
            </div>
          ) : null}

          <div className="upload-block">
            <div className="upload-header">
              <div>
                <h2 className="section-title">上传视频处理</h2>
                <p className="helper-text">
                  第二阶段已接入真实 FFmpeg 处理；适合先验证效果和处理链路。
                </p>
              </div>
              <FileVideo size={22} />
            </div>

            <div className="segmented" role="radiogroup" aria-label="视频来源平台">
              <button
                className={uploadPlatform === "douyin" ? "active" : ""}
                type="button"
                onClick={() => setUploadPlatform("douyin")}
              >
                抖音
              </button>
              <button
                className={uploadPlatform === "kuaishou" ? "active" : ""}
                type="button"
                onClick={() => setUploadPlatform("kuaishou")}
              >
                快手
              </button>
            </div>

            <label className="file-drop">
              <FileVideo size={20} />
              <span>{uploadFile ? uploadFile.name : "选择 MP4 / MOV / WEBM 视频"}</span>
              <input
                accept="video/mp4,video/quicktime,video/webm,.m4v"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                type="file"
              />
            </label>

            {previewUrl ? (
              <div className="preview-tool">
                <div className="preview-stage">
                  <video muted controls preload="metadata" src={previewUrl} />
                  <div className="region-layer" aria-label="水印区域">
                    {watermarkRegions.map((region, index) => (
                      <button
                        className={`region-box ${activeRegionIndex === index ? "active" : ""}`}
                        key={`${region.x}-${region.y}-${index}`}
                        onClick={() => setActiveRegionIndex(index)}
                        style={{
                          left: `${region.x * 100}%`,
                          top: `${region.y * 100}%`,
                          width: `${region.width * 100}%`,
                          height: `${region.height * 100}%`
                        }}
                        title={`水印区域 ${index + 1}`}
                        type="button"
                      >
                        {index + 1}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="region-controls">
                  <div className="control-row">
                    <button className="button secondary" type="button" onClick={addWatermarkRegion}>
                      <Plus size={17} />
                      添加区域
                    </button>
                    <button
                      className="button secondary"
                      type="button"
                      onClick={resetWatermarkRegions}
                    >
                      <RotateCcw size={17} />
                      默认区域
                    </button>
                  </div>

                  {watermarkRegions.length ? (
                    <RegionEditor
                      index={activeRegionIndex}
                      region={watermarkRegions[Math.min(activeRegionIndex, watermarkRegions.length - 1)]}
                      onRemove={() =>
                        removeRegion(Math.min(activeRegionIndex, watermarkRegions.length - 1))
                      }
                      onUpdate={(patch) =>
                        updateRegion(Math.min(activeRegionIndex, watermarkRegions.length - 1), patch)
                      }
                    />
                  ) : (
                    <div className="notice">
                      <Link2 size={18} />
                      <span>未设置手动区域，后端会使用默认角标区域。</span>
                    </div>
                  )}

                  <button className="text-button" type="button" onClick={clearWatermarkRegions}>
                    清空手动区域
                  </button>
                </div>
              </div>
            ) : null}

            <label className="rights-check">
              <input
                checked={uploadRights}
                onChange={(event) => setUploadRights(event.target.checked)}
                type="checkbox"
              />
              <span>我确认该视频为本人所有、已获授权，或平台允许下载和二次处理。</span>
            </label>

            <button
              className="button"
              disabled={!uploadFile || !uploadRights || loading === "upload"}
              onClick={handleUploadJob}
            >
              {loading === "upload" ? <Loader2 size={18} /> : <Play size={18} />}
              上传并处理
            </button>
          </div>
        </section>

        <aside className="panel panel-side">
          <h2 className="section-title">任务状态</h2>
          {job ? (
            <div className="job-card">
              <div className="job-status">
                <span className="status-text">{progressLabel}</span>
                <span>{job.platformLabel}</span>
              </div>
              <div className="progress-track" aria-label="处理进度">
                <div
                  className="progress-bar"
                  style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }}
                />
              </div>
              {job.status === "completed" ? (
                <a className="button" href={job.outputUrl ? toApiUrl(job.outputUrl) : "#"}>
                  <Download size={18} />
                  下载结果
                </a>
              ) : null}
              {job.errorMessage ? (
                <div className="notice error">
                  <Link2 size={18} />
                  <span>{job.errorMessage}</span>
                </div>
              ) : null}
            </div>
          ) : (
            <ul className="side-list">
              <li>
                <strong>支持范围</strong>
                <span>识别抖音、快手链接；上传视频可进行真实处理。</span>
              </li>
              <li>
                <strong>处理策略</strong>
                <span>当前使用 FFmpeg 对常见角标水印区域做局部模糊。</span>
              </li>
              <li>
                <strong>部署方向</strong>
                <span>后端、Worker、Redis、文件目录按 Linux 服务拆分。</span>
              </li>
            </ul>
          )}
        </aside>
      </div>
    </main>
  );
}

function RegionEditor({
  index,
  region,
  onRemove,
  onUpdate
}: {
  index: number;
  region: WatermarkRegion;
  onRemove: () => void;
  onUpdate: (patch: Partial<WatermarkRegion>) => void;
}) {
  return (
    <div className="region-editor">
      <div className="region-editor-head">
        <strong>区域 {index + 1}</strong>
        <button className="text-button danger" type="button" onClick={onRemove}>
          删除
        </button>
      </div>
      <SliderField label="水平位置" value={region.x} onChange={(x) => onUpdate({ x })} />
      <SliderField label="垂直位置" value={region.y} onChange={(y) => onUpdate({ y })} />
      <SliderField label="宽度" value={region.width} onChange={(width) => onUpdate({ width })} />
      <SliderField label="高度" value={region.height} onChange={(height) => onUpdate({ height })} />
    </div>
  );
}

function SliderField({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="slider-field">
      <span>
        {label}
        <strong>{Math.round(value * 100)}%</strong>
      </span>
      <input
        max="1"
        min="0"
        onChange={(event) => onChange(Number(event.target.value))}
        step="0.01"
        type="range"
        value={value}
      />
    </label>
  );
}

function clampRegion(region: WatermarkRegion): WatermarkRegion {
  const x = clamp(region.x, 0, 0.98);
  const y = clamp(region.y, 0, 0.98);
  const width = clamp(region.width, 0.01, 1 - x);
  const height = clamp(region.height, 0.01, 1 - y);
  return { x, y, width, height };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
