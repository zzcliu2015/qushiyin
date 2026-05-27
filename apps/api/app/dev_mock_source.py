from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


class ResolveRequest(BaseModel):
    platform: str
    sourceUrl: str


app = FastAPI(title="qushiuyin dev mock source")


@app.post("/resolve")
def resolve_source(payload: ResolveRequest) -> dict[str, str]:
    if payload.platform not in {"douyin", "kuaishou"}:
        raise HTTPException(status_code=400, detail="unsupported platform")

    return {
        "downloadUrl": "http://127.0.0.1:8010/sample.mp4",
        "title": "local sample",
    }


@app.get("/sample.mp4")
def sample_video() -> FileResponse:
    return FileResponse("storage/tmp/sample.mp4", media_type="video/mp4")

