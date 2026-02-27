from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routes.chat_routes import router as chat_router
from contextlib import asynccontextmanager

# 加载环境变量
load_dotenv()

# 定义lifespan事件处理器
@asynccontextmanager
async def lifespan(app):
    # 启动时的初始化代码（如果需要）
    yield
    # 关闭时的清理代码（如果需要）

# 创建 FastAPI 应用
app = FastAPI(
    title="LangChain AI API",
    description="API for interacting with LangChain and OpenAI models",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )