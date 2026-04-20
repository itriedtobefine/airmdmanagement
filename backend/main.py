"""
TimeTracker Pro - Backend API
Система учета времени и расчета стоимости проектов
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(
    title="TimeTracker Pro API",
    description="API для учета времени и расчета стоимости проектов",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    "dbname": "timetracker",
    "user": "timetracker",
    "password": "timetracker123",
    "host": "localhost",
    "port": "5432"
}


def get_db_connection():
    """Получение соединения с базой данных"""
    return psycopg2.connect(**DB_CONFIG)


# Pydantic модели
class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    client_id: int
    hourly_rate: float = Field(..., gt=0)
    description: Optional[str] = None
    budget: Optional[float] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    hourly_rate: Optional[float] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[str] = None


class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    project_id: int
    description: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class TimeEntryBase(BaseModel):
    task_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    end_time: Optional[datetime] = None
    description: Optional[str] = None


# Инициализация БД
def init_db():
    """Инициализация базы данных - создание таблиц"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Таблица клиентов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            contact_email VARCHAR(200),
            contact_phone VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица проектов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
            hourly_rate DECIMAL(10, 2) NOT NULL,
            description TEXT,
            budget DECIMAL(12, 2),
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица задач
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            description TEXT,
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица записей времени
    cur.execute("""
        CREATE TABLE IF NOT EXISTS time_entries (
            id SERIAL PRIMARY KEY,
            task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            description TEXT,
            duration_minutes INTEGER,
            cost DECIMAL(12, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Индексы для производительности
    cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_task ON time_entries(task_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_start ON time_entries(start_time)")
    
    conn.commit()
    cur.close()
    conn.close()


# Эндпоинты для клиентов
@app.get("/api/clients", tags=["Clients"])
def get_clients():
    """Получить всех клиентов"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM clients ORDER BY created_at DESC")
    clients = cur.fetchall()
    cur.close()
    conn.close()
    return {"clients": clients}


@app.post("/api/clients", tags=["Clients"], status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate):
    """Создать нового клиента"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO clients (name, contact_email, contact_phone) VALUES (%s, %s, %s) RETURNING *",
        (client.name, client.contact_email, client.contact_phone)
    )
    new_client = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"client": new_client}


@app.get("/api/clients/{client_id}", tags=["Clients"])
def get_client(client_id: int):
    """Получить клиента по ID"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
    client = cur.fetchone()
    cur.close()
    conn.close()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": client}


@app.put("/api/clients/{client_id}", tags=["Clients"])
def update_client(client_id: int, client: ClientUpdate):
    """Обновить клиента"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    updates = []
    values = []
    if client.name is not None:
        updates.append("name = %s")
        values.append(client.name)
    if client.contact_email is not None:
        updates.append("contact_email = %s")
        values.append(client.contact_email)
    if client.contact_phone is not None:
        updates.append("contact_phone = %s")
        values.append(client.contact_phone)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(client_id)
        query = f"UPDATE clients SET {', '.join(updates)} WHERE id = %s RETURNING *"
        cur.execute(query, values)
        updated_client = cur.fetchone()
        conn.commit()
    else:
        cur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
        updated_client = cur.fetchone()
    
    cur.close()
    conn.close()
    if not updated_client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": updated_client}


@app.delete("/api/clients/{client_id}", tags=["Clients"])
def delete_client(client_id: int):
    """Удалить клиента"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clients WHERE id = %s RETURNING id", (client_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}


# Эндпоинты для проектов
@app.get("/api/projects", tags=["Projects"])
def get_projects():
    """Получить все проекты с информацией о клиентах"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.*, c.name as client_name 
        FROM projects p 
        LEFT JOIN clients c ON p.client_id = c.id 
        ORDER BY p.created_at DESC
    """)
    projects = cur.fetchall()
    cur.close()
    conn.close()
    return {"projects": projects}


@app.post("/api/projects", tags=["Projects"], status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate):
    """Создать новый проект"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """INSERT INTO projects (name, client_id, hourly_rate, description, budget) 
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (project.name, project.client_id, project.hourly_rate, project.description, project.budget)
    )
    new_project = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"project": new_project}


@app.get("/api/projects/{project_id}", tags=["Projects"])
def get_project(project_id: int):
    """Получить проект по ID"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.*, c.name as client_name 
        FROM projects p 
        LEFT JOIN clients c ON p.client_id = c.id 
        WHERE p.id = %s
    """, (project_id,))
    project = cur.fetchone()
    cur.close()
    conn.close()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@app.put("/api/projects/{project_id}", tags=["Projects"])
def update_project(project_id: int, project: ProjectUpdate):
    """Обновить проект"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    updates = []
    values = []
    if project.name is not None:
        updates.append("name = %s")
        values.append(project.name)
    if project.hourly_rate is not None:
        updates.append("hourly_rate = %s")
        values.append(project.hourly_rate)
    if project.description is not None:
        updates.append("description = %s")
        values.append(project.description)
    if project.budget is not None:
        updates.append("budget = %s")
        values.append(project.budget)
    if project.status is not None:
        updates.append("status = %s")
        values.append(project.status)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(project_id)
        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = %s RETURNING *"
        cur.execute(query, values)
        updated_project = cur.fetchone()
        conn.commit()
    else:
        cur.execute("""
            SELECT p.*, c.name as client_name 
            FROM projects p 
            LEFT JOIN clients c ON p.client_id = c.id 
            WHERE p.id = %s
        """, (project_id,))
        updated_project = cur.fetchone()
    
    cur.close()
    conn.close()
    if not updated_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": updated_project}


@app.delete("/api/projects/{project_id}", tags=["Projects"])
def delete_project(project_id: int):
    """Удалить проект"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE id = %s RETURNING id", (project_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}


@app.get("/api/projects/{project_id}/summary", tags=["Projects"])
def get_project_summary(project_id: int):
    """Получить сводку по проекту: время и стоимость"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем информацию о проекте
    cur.execute("""
        SELECT p.*, c.name as client_name 
        FROM projects p 
        LEFT JOIN clients c ON p.client_id = c.id 
        WHERE p.id = %s
    """, (project_id,))
    project = cur.fetchone()
    if not project:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Получаем задачи проекта
    cur.execute("SELECT * FROM tasks WHERE project_id = %s", (project_id,))
    tasks = cur.fetchall()
    
    total_minutes = 0
    total_cost = 0
    
    for task in tasks:
        cur.execute("""
            SELECT COALESCE(SUM(duration_minutes), 0) as total_min, 
                   COALESCE(SUM(cost), 0) as total_cost
            FROM time_entries 
            WHERE task_id = %s
        """, (task['id'],))
        result = cur.fetchone()
        total_minutes += result['total_min']
        total_cost += float(result['total_cost'])
    
    cur.close()
    conn.close()
    
    return {
        "project": project,
        "tasks_count": len(tasks),
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "total_cost": round(total_cost, 2),
        "budget": float(project['budget']) if project['budget'] else None,
        "budget_remaining": round(float(project['budget']) - total_cost, 2) if project['budget'] else None
    }


# Эндпоинты для задач
@app.get("/api/tasks", tags=["Tasks"])
def get_tasks(project_id: Optional[int] = None):
    """Получить все задачи (опционально по проекту)"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if project_id:
        cur.execute("""
            SELECT t.*, p.name as project_name 
            FROM tasks t 
            LEFT JOIN projects p ON t.project_id = p.id 
            WHERE t.project_id = %s 
            ORDER BY t.created_at DESC
        """, (project_id,))
    else:
        cur.execute("""
            SELECT t.*, p.name as project_name 
            FROM tasks t 
            LEFT JOIN projects p ON t.project_id = p.id 
            ORDER BY t.created_at DESC
        """)
    
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return {"tasks": tasks}


@app.post("/api/tasks", tags=["Tasks"], status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    """Создать новую задачу"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO tasks (name, project_id, description) VALUES (%s, %s, %s) RETURNING *",
        (task.name, task.project_id, task.description)
    )
    new_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"task": new_task}


@app.get("/api/tasks/{task_id}", tags=["Tasks"])
def get_task(task_id: int):
    """Получить задачу по ID"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT t.*, p.name as project_name 
        FROM tasks t 
        LEFT JOIN projects p ON t.project_id = p.id 
        WHERE t.id = %s
    """, (task_id,))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}


@app.put("/api/tasks/{task_id}", tags=["Tasks"])
def update_task(task_id: int, task: TaskUpdate):
    """Обновить задачу"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    updates = []
    values = []
    if task.name is not None:
        updates.append("name = %s")
        values.append(task.name)
    if task.description is not None:
        updates.append("description = %s")
        values.append(task.description)
    if task.status is not None:
        updates.append("status = %s")
        values.append(task.status)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s RETURNING *"
        cur.execute(query, values)
        updated_task = cur.fetchone()
        conn.commit()
    else:
        cur.execute("""
            SELECT t.*, p.name as project_name 
            FROM tasks t 
            LEFT JOIN projects p ON t.project_id = p.id 
            WHERE t.id = %s
        """, (task_id,))
        updated_task = cur.fetchone()
    
    cur.close()
    conn.close()
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": updated_task}


@app.delete("/api/tasks/{task_id}", tags=["Tasks"])
def delete_task(task_id: int):
    """Удалить задачу"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


# Эндпоинты для записей времени
@app.get("/api/time-entries", tags=["Time Entries"])
def get_time_entries(task_id: Optional[int] = None):
    """Получить все записи времени (опционально по задаче)"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if task_id:
        cur.execute("""
            SELECT te.*, t.name as task_name, p.name as project_name, 
                   p.hourly_rate, te.cost
            FROM time_entries te 
            LEFT JOIN tasks t ON te.task_id = t.id 
            LEFT JOIN projects p ON t.project_id = p.id 
            WHERE te.task_id = %s 
            ORDER BY te.start_time DESC
        """, (task_id,))
    else:
        cur.execute("""
            SELECT te.*, t.name as task_name, p.name as project_name, 
                   p.hourly_rate, te.cost
            FROM time_entries te 
            LEFT JOIN tasks t ON te.task_id = t.id 
            LEFT JOIN projects p ON t.project_id = p.id 
            ORDER BY te.start_time DESC
        """)
    
    entries = cur.fetchall()
    cur.close()
    conn.close()
    return {"time_entries": entries}


@app.post("/api/time-entries", tags=["Time Entries"], status_code=status.HTTP_201_CREATED)
def create_time_entry(entry: TimeEntryCreate):
    """Создать новую запись времени"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем ставку проекта
    cur.execute("""
        SELECT p.hourly_rate 
        FROM tasks t 
        JOIN projects p ON t.project_id = p.id 
        WHERE t.id = %s
    """, (entry.task_id,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    hourly_rate = float(result['hourly_rate'])
    
    # Вычисляем длительность
    if entry.end_time:
        duration = entry.end_time - entry.start_time
        duration_minutes = int(duration.total_seconds() / 60)
    else:
        duration_minutes = 0
    
    # Вычисляем стоимость
    cost = (duration_minutes / 60) * hourly_rate
    
    cur.execute(
        """INSERT INTO time_entries (task_id, start_time, end_time, description, duration_minutes, cost) 
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
        (entry.task_id, entry.start_time, entry.end_time, entry.description, duration_minutes, cost)
    )
    new_entry = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"time_entry": new_entry}


@app.get("/api/time-entries/{entry_id}", tags=["Time Entries"])
def get_time_entry(entry_id: int):
    """Получить запись времени по ID"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT te.*, t.name as task_name, p.name as project_name, p.hourly_rate
        FROM time_entries te 
        LEFT JOIN tasks t ON te.task_id = t.id 
        LEFT JOIN projects p ON t.project_id = p.id 
        WHERE te.id = %s
    """, (entry_id,))
    entry = cur.fetchone()
    cur.close()
    conn.close()
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return {"time_entry": entry}


@app.put("/api/time-entries/{entry_id}", tags=["Time Entries"])
def update_time_entry(entry_id: int, entry: TimeEntryUpdate):
    """Обновить запись времени"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем текущую запись
    cur.execute("SELECT * FROM time_entries WHERE id = %s", (entry_id,))
    current_entry = cur.fetchone()
    if not current_entry:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    updates = []
    values = []
    
    if entry.end_time is not None:
        updates.append("end_time = %s")
        values.append(entry.end_time)
        
        # Пересчитываем длительность и стоимость
        start_time = current_entry['start_time']
        end_time = entry.end_time
        duration = end_time - start_time
        duration_minutes = int(duration.total_seconds() / 60)
        updates.append("duration_minutes = %s")
        values.append(duration_minutes)
        
        # Получаем ставку
        cur.execute("""
            SELECT p.hourly_rate 
            FROM tasks t 
            JOIN projects p ON t.project_id = p.id 
            WHERE t.id = %s
        """, (current_entry['task_id'],))
        rate_result = cur.fetchone()
        hourly_rate = float(rate_result['hourly_rate'])
        cost = (duration_minutes / 60) * hourly_rate
        updates.append("cost = %s")
        values.append(cost)
    
    if entry.description is not None:
        updates.append("description = %s")
        values.append(entry.description)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(entry_id)
        query = f"UPDATE time_entries SET {', '.join(updates)} WHERE id = %s RETURNING *"
        cur.execute(query, values)
        updated_entry = cur.fetchone()
        conn.commit()
    else:
        cur.execute("SELECT * FROM time_entries WHERE id = %s", (entry_id,))
        updated_entry = cur.fetchone()
    
    cur.close()
    conn.close()
    return {"time_entry": updated_entry}


@app.delete("/api/time-entries/{entry_id}", tags=["Time Entries"])
def delete_time_entry(entry_id: int):
    """Удалить запись времени"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM time_entries WHERE id = %s RETURNING id", (entry_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return {"message": "Time entry deleted successfully"}


# Dashboard endpoint
@app.get("/api/dashboard", tags=["Dashboard"])
def get_dashboard():
    """Получить общую сводку по всем проектам"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Общая статистика
    cur.execute("SELECT COUNT(*) as total FROM clients")
    total_clients = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM projects WHERE status = 'active'")
    active_projects = cur.fetchone()['total']
    
    cur.execute("""
        SELECT COALESCE(SUM(duration_minutes), 0) as total 
        FROM time_entries
    """)
    total_minutes = cur.fetchone()['total']
    
    cur.execute("""
        SELECT COALESCE(SUM(cost), 0) as total 
        FROM time_entries
    """)
    total_revenue = cur.fetchone()['total']
    
    # Топ проектов по выручке
    cur.execute("""
        SELECT p.name, p.hourly_rate, 
               COALESCE(SUM(te.duration_minutes), 0) as total_minutes,
               COALESCE(SUM(te.cost), 0) as total_cost
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        LEFT JOIN time_entries te ON t.id = te.task_id
        GROUP BY p.id, p.name, p.hourly_rate
        ORDER BY total_cost DESC
        LIMIT 5
    """)
    top_projects = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        "total_clients": total_clients,
        "active_projects": active_projects,
        "total_hours_tracked": round(total_minutes / 60, 2),
        "total_revenue": round(float(total_revenue), 2),
        "top_projects": [
            {
                "name": p['name'],
                "hourly_rate": float(p['hourly_rate']),
                "total_hours": round(p['total_minutes'] / 60, 2),
                "total_cost": round(float(p['total_cost']), 2)
            }
            for p in top_projects
        ]
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    """Проверка здоровья API"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
