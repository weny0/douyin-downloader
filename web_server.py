"""
Web UI 服务 - 提供前端界面 + 文件浏览 + 下载功能
"""

import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 创建应用
app = FastAPI(title="抖音下载器 Web 服务")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 文件浏览 API ==========

def scan_files(path: Path, max_depth: int = 4, current_depth: int = 0):
    """递归扫描文件"""
    if current_depth >= max_depth or not path.exists():
        return []
    
    result = []
    try:
        for item in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith('.') or item.name.endswith('.tmp'):
                continue
            
            node = {
                "name": item.name,
                "path": str(item.relative_to(Path("./Downloaded"))),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
                "mtime": item.stat().st_mtime
            }
            
            if item.is_dir():
                node["children"] = scan_files(item, max_depth, current_depth + 1)
            
            result.append(node)
    except PermissionError:
        pass
    
    return result

@app.get("/api/files")
async def list_files():
    """列出所有下载文件"""
    download_path = Path("./Downloaded")
    if not download_path.exists():
        return {"files": []}
    
    return {"files": scan_files(download_path)}

@app.get("/api/download/{path:path}")
async def download_file(path: str):
    """下载单个文件"""
    # 安全检查：防止目录遍历
    download_path = Path("./Downloaded").resolve()
    file_path = (download_path / path).resolve()
    
    # 确保文件在下载目录内
    try:
        file_path.relative_to(download_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="访问被拒绝")
    
    if not file_path.exists() or file_path.is_dir():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type='application/octet-stream'
    )

# ========== 前端静态文件 ==========

# 尝试加载内置前端
WEB_DIR = Path(__file__).parent / "web"

@app.get("/", response_class=HTMLResponse)
async def index():
    """首页 - 返回 Web UI"""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding='utf-8')
    
    # 如果没有前端文件，返回简单提示
    return """
    <html>
    <head><title>抖音下载器</title></head>
    <body>
        <h1>抖音下载器 API 服务</h1>
        <p>API 端点: /api/v1</p>
        <p>文件浏览: /api/files</p>
        <p>请确保 web/index.html 存在以使用 Web 界面</p>
    </body>
    </html>
    """

# 挂载静态文件（如果存在）
if (WEB_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")

# ========== 代理原有 API ==========
# 原项目的 API 在 /api/v1 下，通过 nginx 或单独运行
# 这里我们直接集成

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    
    print(f"🚀 Web 服务启动: http://{args.host}:{args.port}")
    print(f"📡 API 地址: http://{args.host}:{args.port}/api/v1")
    uvicorn.run(app, host=args.host, port=args.port)
