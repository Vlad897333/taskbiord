import asyncpg
from typing import List, Dict

DATABASE_URL = "postgresql://postgres:123@localhost:5432/taskboard"

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool

async def init_database():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

async def close_database():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def get_all_tasks() -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM tasks ORDER BY id DESC")
        return [dict(row) for row in rows]

async def get_task_by_id(task_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)

async def create_task(title: str, description: str = "", priority: str = "medium", status: str = "pending") -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO tasks (title, description, priority, status) VALUES ($1, $2, $3, $4) RETURNING id",
            title, description, priority, status
        )

async def update_task(task_id: int, title: str, description: str, priority: str, status: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE tasks SET title = $1, description = $2, priority = $3, status = $4 WHERE id = $5",
            title, description, priority, status, task_id
        )
        return result != "UPDATE 0"

async def delete_task(task_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
        return result != "DELETE 0"

async def update_task_status(task_id: int, status: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE tasks SET status = $1 WHERE id = $2",
            status, task_id
        )
        return result != "UPDATE 0"