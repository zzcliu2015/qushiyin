"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clipboard,
  Download,
  Link2,
  Loader2,
  Play,
  Search,
  ShieldCheck
} from "lucide-react";
import {
  createAuthorizedSource,
  createJob,
  getJob,
  listAuthorizedSources,
  AuthorizedSourceResponse,
  JobResponse,
  parseLink,
  ParseLinkResponse,
  toApiUrl
} from "@/lib/api";

const statusLabels: Record<JobResponse["status"], string> = {
  pending: "排队中",
  downloading: "获取授权视频源",
  analyzing: "分析水印",
  processing: "处理中",
  uploading: "保存结果",
  completed: "已完成",
  failed: "失败",
  expired: "已过期"
};

export default function HomePage() {
  const [url, setUrl] = useState("");
  const [parsed, setParsed] = useState<ParseLinkResponse | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [confirmedRights, setConfirmedRights] = useState(false);
  const [sourceLink, setSourceLink] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceRights, setSourceRights] = useState(false);
  const [authorizedSources, setAuthorizedSources] = useState<AuthorizedSourceResponse[]>([]);
  const [loading, setLoading] = useState<"parse" | "job" | "source" | "sources" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourceMessage, setSourceMessage] = useState<string | null>(null);

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
    refreshAuthorizedSources();
  }, []);

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

  async function handlePaste() {
    const text = await navigator.clipboard.readText();
    setUrl(text);
  }

  async function refreshAuthorizedSources() {
    try {
      setLoading((current) => current ?? "sources");
      const sources = await listAuthorizedSources();
      setAuthorizedSources(sources);
    } catch (err) {
      setSourceMessage(err instanceof Error ? err.message : "授权源列表加载失败");
    } finally {
      setLoading((current) => (current === "sources" ? null : current));
    }
  }

  async function handleCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSourceMessage(null);

    if (!sourceLink.trim() || !downloadUrl.trim()) {
      setSourceMessage("请填写平台链接和自有源视频地址");
      return;
    }

    try {
      setLoading("source");
      await createAuthorizedSource({
        sourceUrl: sourceLink.trim(),
        downloadUrl: downloadUrl.trim(),
        title: sourceTitle.trim() || undefined,
        confirmedRights: sourceRights
      });
      setSourceMessage("授权源已登记，可以在上方粘贴该链接开始处理。");
      setSourceLink("");
      setDownloadUrl("");
      setSourceTitle("");
      setSourceRights(false);
      await refreshAuthorizedSources();
    } catch (err) {
      setSourceMessage(err instanceof Error ? err.message : "授权源登记失败");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">去</div>
          <div>
            <h1 className="brand-title">抖音 / 快手链接去水印</h1>
            <p className="brand-subtitle">仅处理本人拥有版权、已获授权或平台允许处理的视频</p>
          </div>
        </div>
        <div className="status-pill">
          <ShieldCheck size={16} />
          授权视频源模式
        </div>
      </header>

      <div className="workbench">
        <section className="panel panel-main">
          <h2 className="section-title">粘贴视频链接</h2>

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
                  已识别为{parsed.platformLabel}链接。开始处理后，后端会调用你配置的授权视频源服务获取源视频，再进行 FFmpeg 处理。
                </span>
              </div>

              <div className="meta-grid">
                <div className="meta-item">
                  <p className="meta-label">平台</p>
                  <p className="meta-value">{parsed.platformLabel}</p>
                </div>
                <div className="meta-item">
                  <p className="meta-label">源视频</p>
                  <p className="meta-value">授权服务获取</p>
                </div>
                <div className="meta-item">
                  <p className="meta-label">处理模式</p>
                  <p className="meta-value">自动水印区域</p>
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

          <div className="source-block">
            <h2 className="section-title">登记授权源</h2>
            <form className="source-form" onSubmit={handleCreateSource}>
              <input
                className="url-input"
                value={sourceLink}
                onChange={(event) => setSourceLink(event.target.value)}
                placeholder="抖音或快手作品链接"
              />
              <input
                className="url-input"
                value={downloadUrl}
                onChange={(event) => setDownloadUrl(event.target.value)}
                placeholder="自有或已授权的 MP4 源视频地址"
              />
              <input
                className="url-input"
                value={sourceTitle}
                onChange={(event) => setSourceTitle(event.target.value)}
                placeholder="标题，可选"
              />
              <label className="rights-check">
                <input
                  checked={sourceRights}
                  onChange={(event) => setSourceRights(event.target.checked)}
                  type="checkbox"
                />
                <span>我确认该源视频为本人所有、已获授权，或平台允许下载和二次处理。</span>
              </label>
              <button
                className="button secondary"
                disabled={!sourceRights || loading === "source"}
                type="submit"
              >
                {loading === "source" ? <Loader2 size={18} /> : <ShieldCheck size={18} />}
                保存授权源
              </button>
            </form>

            {sourceMessage ? (
              <div className={`notice ${sourceMessage.includes("失败") ? "error" : ""}`}>
                <Link2 size={18} />
                <span>{sourceMessage}</span>
              </div>
            ) : null}
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
              {authorizedSources.slice(0, 4).map((source) => (
                <li key={source.id}>
                  <strong>{source.title || source.platformLabel}</strong>
                  <span>{source.normalizedUrl}</span>
                </li>
              ))}
              <li>
                <strong>支持范围</strong>
                <span>仅支持抖音、快手公开视频链接识别和授权源视频处理。</span>
              </li>
              <li>
                <strong>处理策略</strong>
                <span>当前使用 FFmpeg 对常见角标水印区域做局部模糊。</span>
              </li>
              <li>
                <strong>部署方向</strong>
                <span>Linux 上配置授权视频源服务、FFmpeg、Nginx 和持久化存储。</span>
              </li>
            </ul>
          )}
        </aside>
      </div>
    </main>
  );
}
