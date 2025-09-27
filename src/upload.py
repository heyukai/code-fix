import logging
from pathlib import Path
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server File Upload API")

# 添加 CORS 中间件（根据需要调整 origins）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应更具体
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
PROJECTS_DIR = Path("/app/tmpproject")
MAX_FILE_SIZE = 1024 * 1024 * 100  # 100 MB
ALLOWED_EXTENSIONS = {".zip", ".tar", ".tar.gz", ".tgz"}

# 确保项目目录存在
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否被允许"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.post("/upload")
async def upload_project(file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型。仅支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )


    safe_filename = Path(file.filename).name  # 移除任何路径信息
    file_location = PROJECTS_DIR / safe_filename

    try:
        async with aiofiles.open(file_location, "wb") as f:
            while chunk := await file.read(8192):  # 8KB chunks
                await f.write(chunk)

        logger.info(f"文件 {file.filename} 已成功上传到 {file_location}")


        return {
            "filename": file.filename,
            "saved_path": str(file_location),
            "message": "文件上传成功"
        }

    except IOError as e:
        logger.error(f"写入文件时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传过程中发生错误"
        )
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误"
        )
    finally:
        await file.close()


@app.get("/")
async def root():
    return {"message": "MCP Server File Upload API 正在运行"}



if __name__ == "__main__":
    import uvicorn

    print("启动文件上传API服务...")
    print("文件上传API将在 http://0.0.0.0:8001 运行")
    print(f"项目目录: {PROJECTS_DIR.absolute()}")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)