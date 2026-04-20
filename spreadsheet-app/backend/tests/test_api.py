"""
Модульные тесты для Spreadsheet App.
Запуск: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import Base, get_db

# Тестовая БД
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_spreadsheet.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Создание тестового клиента и таблиц."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user():
    """Данные тестового пользователя."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }


def test_register_user(client, test_user):
    """Тест регистрации пользователя."""
    response = client.post("/api/auth/register", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert "id" in data


def test_register_duplicate_user(client, test_user):
    """Тест регистрации дубликата пользователя."""
    client.post("/api/auth/register", json=test_user)
    response = client.post("/api/auth/register", json=test_user)
    assert response.status_code == 400


def test_login_success(client, test_user):
    """Тест успешного входа."""
    client.post("/api/auth/register", json=test_user)
    
    response = client.post(
        "/api/auth/token",
        data={"username": test_user["username"], "password": test_user["password"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """Тест входа с неправильным паролем."""
    client.post("/api/auth/register", json=test_user)
    
    response = client.post(
        "/api/auth/token",
        data={"username": test_user["username"], "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_get_current_user(client, test_user):
    """Тест получения текущего пользователя."""
    # Регистрация и вход
    client.post("/api/auth/register", json=test_user)
    login_response = client.post(
        "/api/auth/token",
        data={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]


def test_create_spreadsheet(client, test_user):
    """Тест создания таблицы."""
    # Регистрация и вход
    client.post("/api/auth/register", json=test_user)
    login_response = client.post(
        "/api/auth/token",
        data={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login_response.json()["access_token"]
    
    spreadsheet_data = {
        "name": "Test Spreadsheet",
        "description": "Test description"
    }
    
    response = client.post(
        "/api/spreadsheets/",
        headers={"Authorization": f"Bearer {token}"},
        json=spreadsheet_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == spreadsheet_data["name"]
    assert data["description"] == spreadsheet_data["description"]
    assert "id" in data


def test_get_spreadsheets(client, test_user):
    """Тест получения списка таблиц."""
    # Регистрация и вход
    client.post("/api/auth/register", json=test_user)
    login_response = client.post(
        "/api/auth/token",
        data={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login_response.json()["access_token"]
    
    # Создание таблицы
    client.post(
        "/api/spreadsheets/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test", "description": ""}
    )
    
    response = client.get(
        "/api/spreadsheets/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_update_cell(client, test_user):
    """Тест обновления ячейки."""
    # Регистрация и вход
    client.post("/api/auth/register", json=test_user)
    login_response = client.post(
        "/api/auth/token",
        data={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login_response.json()["access_token"]
    
    # Создание таблицы
    create_response = client.post(
        "/api/spreadsheets/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test", "description": ""}
    )
    spreadsheet_id = create_response.json()["id"]
    
    # Обновление ячейки
    cell_update = {
        "cell_address": "A1",
        "value": "Hello World",
        "formula": None,
        "style": {}
    }
    
    response = client.put(
        f"/api/spreadsheets/{spreadsheet_id}/cells/A1",
        headers={"Authorization": f"Bearer {token}"},
        json=cell_update
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["cells"]["A1"]["value"] == "Hello World"


def test_unauthorized_access(client):
    """Тест доступа без авторизации."""
    response = client.get("/api/spreadsheets/")
    assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
