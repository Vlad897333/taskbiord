import pytest
import asyncpg
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = "postgresql://postgres:123@localhost:5432/taskboard_test"

# Глобальный пул
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool

async def init_test_db():
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

async def clear_test_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tasks")
        await conn.execute("ALTER SEQUENCE tasks_id_seq RESTART WITH 1")

async def create_task(title, description="", priority="medium", status="pending"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO tasks (title, description, priority, status) VALUES ($1, $2, $3, $4) RETURNING id",
            title, description, priority, status
        )

async def get_all_tasks():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM tasks ORDER BY id")
        return [dict(row) for row in rows]

async def get_task_by_id(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)

async def update_task_status(task_id, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("UPDATE tasks SET status = $1 WHERE id = $2", status, task_id)
        return result != "UPDATE 0"

async def delete_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
        return result != "DELETE 0"

@pytest.fixture(autouse=True)
async def setup_db():
    await init_test_db()
    await clear_test_db()
    yield
    await clear_test_db()

# ==================== 10 СЦЕНАРИЕВ ====================

@pytest.mark.asyncio
async def test_1_create_task():
    """Сценарий 1: Создание новой задачи"""
    task_id = await create_task("Изучить FastAPI", "Прочитать документацию", "high")
    assert task_id == 1
    print("\n✅ Сценарий 1: Задача создана с ID=1")

@pytest.mark.asyncio
async def test_2_get_task_by_id():
    """Сценарий 2: Получение задачи по ID"""
    await create_task("Сделать проект", "", "medium")
    task = await get_task_by_id(1)
    assert task is not None
    assert task["title"] == "Сделать проект"
    print("\n✅ Сценарий 2: Задача получена по ID")

@pytest.mark.asyncio
async def test_3_get_all_tasks():
    """Сценарий 3: Получение всех задач"""
    await create_task("Задача 1")
    await create_task("Задача 2")
    await create_task("Задача 3")
    tasks = await get_all_tasks()
    assert len(tasks) == 3
    print("\n✅ Сценарий 3: Получено 3 задачи")

@pytest.mark.asyncio
async def test_4_update_task_status_to_in_progress():
    """Сценарий 4: Изменение статуса на 'В работе'"""
    task_id = await create_task("Разработать API", "", "high")
    result = await update_task_status(task_id, "in_progress")
    assert result is True
    task = await get_task_by_id(task_id)
    assert task["status"] == "in_progress"
    print("\n✅ Сценарий 4: Статус изменён на 'in_progress'")

@pytest.mark.asyncio
async def test_5_update_task_status_to_completed():
    """Сценарий 5: Изменение статуса на 'Завершено'"""
    task_id = await create_task("Написать тесты", "", "medium")
    result = await update_task_status(task_id, "completed")
    assert result is True
    task = await get_task_by_id(task_id)
    assert task["status"] == "completed"
    print("\n✅ Сценарий 5: Статус изменён на 'completed'")

@pytest.mark.asyncio
async def test_6_delete_task():
    """Сценарий 6: Удаление задачи"""
    task_id = await create_task("Временная задача", "Будет удалена")
    result = await delete_task(task_id)
    assert result is True
    task = await get_task_by_id(task_id)
    assert task is None
    print("\n✅ Сценарий 6: Задача успешно удалена")

@pytest.mark.asyncio
async def test_7_create_task_without_description():
    """Сценарий 7: Создание задачи без описания"""
    task_id = await create_task("Задача без описания")
    assert task_id > 0
    task = await get_task_by_id(task_id)
    assert task["description"] == ""
    print("\n✅ Сценарий 7: Задача без описания создана")

@pytest.mark.asyncio
async def test_8_create_task_with_low_priority():
    """Сценарий 8: Создание задачи с низким приоритетом"""
    task_id = await create_task("Неважная задача", priority="low")
    task = await get_task_by_id(task_id)
    assert task["priority"] == "low"
    print("\n✅ Сценарий 8: Задача с низким приоритетом")

@pytest.mark.asyncio
async def test_9_create_task_with_high_priority():
    """Сценарий 9: Создание задачи с высоким приоритетом"""
    task_id = await create_task("Срочная задача", priority="high")
    task = await get_task_by_id(task_id)
    assert task["priority"] == "high"
    print("\n✅ Сценарий 9: Задача с высоким приоритетом")

@pytest.mark.asyncio
async def test_10_multiple_tasks_different_statuses():
    """Сценарий 10: Несколько задач с разными статусами"""
    await create_task("Ожидает", status="pending")
    await create_task("В работе", status="in_progress")
    await create_task("Готово", status="completed")
    
    tasks = await get_all_tasks()
    assert len(tasks) == 3
    
    statuses = [t["status"] for t in tasks]
    assert "pending" in statuses
    assert "in_progress" in statuses
    assert "completed" in statuses
    print("\n✅ Сценарий 10: Задачи с разными статусами созданы")   