import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ── 模块路由注册 ──

from app.modules.ai_cases.router import router as ai_cases_router  # noqa: E402
from app.modules.bq_query.router import router as bq_router  # noqa: E402

app.include_router(ai_cases_router, prefix="/api")
app.include_router(bq_router, prefix="/api/bq")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
