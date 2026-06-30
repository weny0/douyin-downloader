"""
Web UI 服务 - 集成原项目 API + 提供前端界面 + Cookie 管理 + 文件浏览
"""

import os
import sys
import json
import yaml
import subprocess
import tempfile
import time
import threading
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 将项目根目录加入路径，以便导入原项目模块
sys.path.insert(0, str(Path(__file__).parent))

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

# ========== 配置文件 ==========
CONFIG_PATH = Path("config.yml")
CONFIG_EXAMPLE = Path("config.example.yml")

def load_config():
    """加载配置文件"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    elif CONFIG_EXAMPLE.exists():
        with open(CONFIG_EXAMPLE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

# ========== 模拟原项目 API（简化版） ==========
# 实际使用时，应该导入原项目的下载逻辑

# 内存中的任务存储（实际应该用数据库）
jobs_db = {}
job_counter = 0
job_lock = threading.Lock()

class JobManager:
    @staticmethod
    def create_job(url, mode=None, number=0, thread=5):
        global job_counter
        with job_lock:
            job_counter += 1
            job_id = f"job_{job_counter:06d}"
        
        job = {
            "job_id": job_id,
            "url": url,
            "mode": mode or ["post"],
            "number": number,
            "thread": thread,
            "status": "pending",
            "progress": 0,
            "created_at": int(time.time()),
            "completed_at": None,
            "error": None
        }
        jobs_db[job_id] = job
        
        # 启动后台下载线程
        thread_obj = threading.Thread(target=JobManager._download_worker, args=(job_id,))
        thread_obj.daemon = True
        thread_obj.start()
        
        return job
    
    @staticmethod
    def _download_worker(job_id):
        """模拟下载过程"""
        job = jobs_db.get(job_id)
        if not job:
            return
        
        job["status"] = "running"
        
        # 模拟下载进度
        for i in range(1, 11):
            time.sleep(1)
            job["progress"] = i * 10
            if i == 10:
                job["status"] = "completed"
                job["completed_at"] = int(time.time())
        
        # 实际使用时，这里调用原项目的下载逻辑
        # from run import DouyinDownloader
        # downloader = DouyinDownloader(config)
        # downloader.download_url(job["url"])
    
    @staticmethod
    def get_job(job_id):
        return jobs_db.get(job_id)
    
    @staticmethod
    def list_jobs(limit=50):
        sorted_jobs = sorted(jobs_db.values(), key=lambda x: x["created_at"], reverse=True)
        return sorted_jobs[:limit]

# ========== API 路由 ==========

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.post("/api/v1/download")
async def api_download(request: Request):
    """提交下载任务"""
    try:
        data = await request.json()
        url = data.get("url", "").strip()
        mode = data.get("mode", ["post"])
        number = data.get("number", 0)
        thread = data.get("thread", 5)
        
        if not url:
            raise HTTPException(status_code=400, detail="URL 不能为空")
        
        # 检查 Cookie
        config = load_config()
        cookies = config.get("cookies", {})
        if not cookies.get("ttwid"):
            raise HTTPException(status_code=400, detail="Cookie 未配置，请先设置 ttwid")
        
        job = JobManager.create_job(url, mode, number, thread)
        
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "message": "任务已提交"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")

@app.get("/api/v1/jobs/{job_id}")
async def api_get_job(job_id: str):
    """获取单个任务"""
    job = JobManager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job

@app.get("/api/v1/jobs")
async def api_list_jobs(limit: int = 50):
    """列出任务"""
    return {"jobs": JobManager.list_jobs(limit)}

# ========== Cookie API ==========

@app.get("/api/cookies")
async def get_cookies():
    """获取当前 Cookie 配置"""
    config = load_config()
    cookies = config.get('cookies', {})
    return {
        "cookies": {
            "msToken": cookies.get('msToken', ''),
            "ttwid": cookies.get('ttwid', ''),
            "odin_tt": cookies.get('odin_tt', ''),
            "passport_csrf_token": cookies.get('passport_csrf_token', ''),
            "sid_guard": cookies.get('sid_guard', '')
        }
    }

@app.post("/api/cookies")
async def update_cookies(request: Request):
    """保存 Cookie 配置"""
    try:
        data = await request.json()
        new_cookies = data.get('cookies', {})
        
        config = load_config()
        if 'cookies' not in config:
            config['cookies'] = {}
        
        for key in ['msToken', 'ttwid', 'odin_tt', 'passport_csrf_token', 'sid_guard']:
            if key in new_cookies:
                config['cookies'][key] = new_cookies[key]
        
        # 确保必要字段存在
        if 'path' not in config:
            config['path'] = './Downloaded/'
        if 'mode' not in config:
            config['mode'] = ['post']
        if 'thread' not in config:
            config['thread'] = 5
        if 'database' not in config:
            config['database'] = True
        
        save_config(config)
        return {"success": True, "message": "Cookie 保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

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
    download_path = Path("./Downloaded").resolve()
    file_path = (download_path / path).resolve()
    
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

WEB_DIR = Path(__file__).parent / "web"

@app.get("/", response_class=HTMLResponse)
async def index():
    """首页 - 返回 Web UI"""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding='utf-8')
    
    return """
    <html>
    <head><title>抖音下载器</title></head>
    <body>
        <h1>抖音下载器 API 服务</h1>
        <p>API 端点: /api/v1/health</p>
        <p>Cookie 管理: /api/cookies</p>
        <p>文件浏览: /api/files</p>
        <p>请确保 web/index.html 存在以使用 Web 界面</p>
    </body>
    </html>
    """

if (WEB_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    
    print(f"🚀 Web 服务启动: http://{args.host}:{args.port}")
    print(f"📡 API 地址: http://{args.host}:{args.port}/api/v1")
    print(f"🍪 Cookie 管理: http://{args.host}:{args.port}/api/cookies")
    uvicorn.run(app, host=args.host, port=args.port)
