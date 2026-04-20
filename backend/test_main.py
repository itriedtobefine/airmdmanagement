"""
TimeTracker Pro - Backend Tests
Модульные тесты для API
"""
import pytest
import httpx
from main import app, init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Инициализация БД перед тестами"""
    init_db()


@pytest.fixture(scope="module")
def test_client():
    """Создание тестового клиента"""
    with httpx.Client(app=app, base_url="http://test") as client:
        yield client


class TestClients:
    """Тесты для клиентов"""

    def test_create_client(self, test_client):
        """Создание клиента"""
        response = test_client.post(
            "/api/clients",
            json={
                "name": "Test Client API",
                "contact_email": "test@api.com",
                "contact_phone": "+1234567890"
            }
        )
        assert response.status_code == 201
        data = response.json()["client"]
        assert data["name"] == "Test Client API"
        assert data["contact_email"] == "test@api.com"
        return data["id"]

    def test_get_clients(self, test_client):
        """Получение списка клиентов"""
        response = test_client.get("/api/clients")
        assert response.status_code == 200
        assert "clients" in response.json()

    def test_get_client_by_id(self, test_client):
        """Получение клиента по ID"""
        create_response = test_client.post(
            "/api/clients",
            json={"name": "Get Test Client"}
        )
        client_id = create_response.json()["client"]["id"]
        
        response = test_client.get(f"/api/clients/{client_id}")
        assert response.status_code == 200
        assert response.json()["client"]["id"] == client_id

    def test_update_client(self, test_client):
        """Обновление клиента"""
        create_response = test_client.post(
            "/api/clients",
            json={"name": "Update Test Client"}
        )
        client_id = create_response.json()["client"]["id"]
        
        response = test_client.put(
            f"/api/clients/{client_id}",
            json={"name": "Updated Client Name"}
        )
        assert response.status_code == 200
        assert response.json()["client"]["name"] == "Updated Client Name"

    def test_delete_client(self, test_client):
        """Удаление клиента"""
        create_response = test_client.post(
            "/api/clients",
            json={"name": "Delete Test Client"}
        )
        client_id = create_response.json()["client"]["id"]
        
        response = test_client.delete(f"/api/clients/{client_id}")
        assert response.status_code == 200


class TestProjects:
    """Тесты для проектов"""

    def test_create_project(self, test_client):
        """Создание проекта"""
        client_response = test_client.post(
            "/api/clients",
            json={"name": "Project Client"}
        )
        client_id = client_response.json()["client"]["id"]
        
        response = test_client.post(
            "/api/projects",
            json={
                "name": "Test Project",
                "client_id": client_id,
                "hourly_rate": 75.00,
                "budget": 10000
            }
        )
        assert response.status_code == 201
        data = response.json()["project"]
        assert data["name"] == "Test Project"
        assert data["hourly_rate"] == 75.00

    def test_get_projects(self, test_client):
        """Получение списка проектов"""
        response = test_client.get("/api/projects")
        assert response.status_code == 200
        assert "projects" in response.json()

    def test_project_summary(self, test_client):
        """Получение сводки по проекту"""
        client_response = test_client.post(
            "/api/clients",
            json={"name": "Summary Client"}
        )
        client_id = client_response.json()["client"]["id"]
        
        project_response = test_client.post(
            "/api/projects",
            json={
                "name": "Summary Project",
                "client_id": client_id,
                "hourly_rate": 50.00
            }
        )
        project_id = project_response.json()["project"]["id"]
        
        response = test_client.get(f"/api/projects/{project_id}/summary")
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert "total_hours" in data
        assert "total_cost" in data


class TestTasks:
    """Тесты для задач"""

    def test_create_task(self, test_client):
        """Создание задачи"""
        client_response = test_client.post(
            "/api/clients",
            json={"name": "Task Client"}
        )
        client_id = client_response.json()["client"]["id"]
        
        project_response = test_client.post(
            "/api/projects",
            json={
                "name": "Task Project",
                "client_id": client_id,
                "hourly_rate": 60.00
            }
        )
        project_id = project_response.json()["project"]["id"]
        
        response = test_client.post(
            "/api/tasks",
            json={
                "name": "Test Task",
                "project_id": project_id,
                "description": "Task description"
            }
        )
        assert response.status_code == 201
        data = response.json()["task"]
        assert data["name"] == "Test Task"

    def test_get_tasks(self, test_client):
        """Получение списка задач"""
        response = test_client.get("/api/tasks")
        assert response.status_code == 200
        assert "tasks" in response.json()


class TestTimeEntries:
    """Тесты для записей времени"""

    def test_create_time_entry(self, test_client):
        """Создание записи времени"""
        client_response = test_client.post(
            "/api/clients",
            json={"name": "Time Client"}
        )
        client_id = client_response.json()["client"]["id"]
        
        project_response = test_client.post(
            "/api/projects",
            json={
                "name": "Time Project",
                "client_id": client_id,
                "hourly_rate": 100.00
            }
        )
        project_id = project_response.json()["project"]["id"]
        
        task_response = test_client.post(
            "/api/tasks",
            json={
                "name": "Time Task",
                "project_id": project_id
            }
        )
        task_id = task_response.json()["task"]["id"]
        
        response = test_client.post(
            "/api/time-entries",
            json={
                "task_id": task_id,
                "start_time": "2026-01-01T09:00:00",
                "end_time": "2026-01-01T17:00:00",
                "description": "Work day"
            }
        )
        assert response.status_code == 201
        data = response.json()["time_entry"]
        assert data["duration_minutes"] == 480
        assert data["cost"] == 800.00

    def test_get_time_entries(self, test_client):
        """Получение записей времени"""
        response = test_client.get("/api/time-entries")
        assert response.status_code == 200
        assert "time_entries" in response.json()


class TestDashboard:
    """Тесты для dashboard"""

    def test_get_dashboard(self, test_client):
        """Получение статистики dashboard"""
        response = test_client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_clients" in data
        assert "active_projects" in data
        assert "total_hours_tracked" in data
        assert "total_revenue" in data
        assert "top_projects" in data


class TestHealth:
    """Тесты для health check"""

    def test_health_check(self, test_client):
        """Проверка здоровья API"""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
