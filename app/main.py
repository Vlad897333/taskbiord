from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from .database import (
    init_database, get_all_tasks, get_task_by_id,
    create_task, update_task, delete_task, update_task_status,
    close_database
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(BASE_DIR, "templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    print("✅ PostgreSQL подключена")
    yield
    await close_database()
    print("✅ PostgreSQL отключена")

app = FastAPI(title="Task Board", lifespan=lifespan)
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/board", response_class=HTMLResponse)
async def board(request: Request):
    tasks = await get_all_tasks()
    
    stats = {
        "total": len(tasks),
        "pending": len([t for t in tasks if t['status'] == 'pending']),
        "in_progress": len([t for t in tasks if t['status'] == 'in-progress']),
        "completed": len([t for t in tasks if t['status'] == 'completed'])
    }
    
    return templates.TemplateResponse("board.html", {
        "request": request,
        "tasks": tasks,
        "stats": stats
    })

@app.post("/task/create")
async def task_create(
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("medium")
):
    await create_task(title, description, priority)
    return RedirectResponse(url="/board", status_code=303)

@app.post("/task/{task_id}/delete")
async def task_delete(task_id: int):
    await delete_task(task_id)
    return RedirectResponse(url="/board", status_code=303)

@app.post("/task/{task_id}/status")
async def task_status_update(task_id: int, status: str = Form(...)):
    await update_task_status(task_id, status)
    return RedirectResponse(url="/board", status_code=303)

@app.get("/task/{task_id}/edit", response_class=HTMLResponse)
async def task_edit_form(request: Request, task_id: int):
    task = await get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tasks = await get_all_tasks()
    stats = {
        "total": len(tasks),
        "pending": len([t for t in tasks if t['status'] == 'pending']),
        "in_progress": len([t for t in tasks if t['status'] == 'in-progress']),
        "completed": len([t for t in tasks if t['status'] == 'completed'])
    }
    
    return templates.TemplateResponse("board.html", {
        "request": request,
        "tasks": tasks,
        "stats": stats,
        "edit_task": task
    })

@app.post("/task/{task_id}/update")
async def task_update(
    task_id: int,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("medium")
):
    task = await get_task_by_id(task_id)
    if task:
        await update_task(task_id, title, description, priority, task['status'])
    return RedirectResponse(url="/board", status_code=303)