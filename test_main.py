"""
File kiem thu (Test Suite) cho Team Task Manager API.
Su dung FastAPI TestClient de xac minh toan bo endpoint truoc khi nop bai.
Chay: pytest HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_test.py -v
"""

import pytest
from fastapi.testclient import TestClient

from main import app, tasks_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_tasks_db():
    """Reset lai du lieu mo phong truoc moi test de cac test khong anh huong lan nhau."""
    original_data = [
        {
            "id": 1,
            "title": "Thiet ke database Shop AI",
            "description": "Xay dung bang va toi uu index",
            "assignee": "QuyDev",
            "priority": 1,
            "status": "todo",
            "created_at": "2026-07-01T09:00:00Z",
        },
        {
            "id": 2,
            "title": "Code bo API Authen",
            "description": "Trien khai filter verify JWT token",
            "assignee": "FixerQ",
            "priority": 2,
            "status": "done",
            "created_at": "2026-07-01T10:00:00Z",
        },
    ]
    tasks_db.clear()
    tasks_db.extend(original_data)
    yield
    tasks_db.clear()
    tasks_db.extend(original_data)


# =========================================================
# Chuc nang 1: GET /tasks
def test_get_all_tasks_returns_sample_data():
    response = client.get("/tasks")
    body = response.json()
    assert response.status_code == 200
    assert body["statusCode"] == 200
    assert body["error"] is None
    assert len(body["data"]) == 2
    assert body["path"] == "/tasks"


def test_get_all_tasks_filter_by_status():
    response = client.get("/tasks?status=done")
    body = response.json()
    assert response.status_code == 200
    assert len(body["data"]) == 1
    assert body["data"][0]["status"] == "done"


def test_get_all_tasks_empty_returns_empty_array_no_error():
    tasks_db.clear()
    response = client.get("/tasks")
    body = response.json()
    assert response.status_code == 200
    assert body["data"] == []
    assert body["error"] is None


# =========================================================
# Chuc nang 2: POST /tasks
def test_create_task_success():
    payload = {
        "title": "Viet tai lieu SRS project",
        "description": "Mo ta chi tiet endpoint va model dac ta",
        "assignee": "Gu AI",
        "priority": 3,
    }
    response = client.post("/tasks", json=payload)
    body = response.json()
    assert response.status_code == 201
    assert body["statusCode"] == 201
    assert body["data"]["id"] == 3
    assert body["data"]["status"] == "todo"
    assert body["error"] is None


def test_create_task_duplicate_title_returns_400():
    payload = {
        "title": "Thiet ke database Shop AI",  # trung voi task id=1
        "description": "Mot mo ta khac",
        "assignee": "NguoiKhac",
        "priority": 2,
    }
    response = client.post("/tasks", json=payload)
    body = response.json()
    assert response.status_code == 400
    assert body["statusCode"] == 400
    assert body["data"] is None
    assert "ERR-TASK-01" in body["error"]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "ab", "description": "Mo ta", "assignee": "A", "priority": 1},  # title < 3 ky tu
        {"title": "Tieu de hop le", "description": "", "assignee": "A", "priority": 1},  # description rong
        {"title": "Tieu de hop le", "description": "Mo ta", "assignee": "  A B  ", "priority": 1},  # khoang trang thua
        {"title": "Tieu de hop le", "description": "Mo ta", "assignee": "A", "priority": 0},  # priority < 1
        {"title": "Tieu de hop le", "description": "Mo ta", "assignee": "A", "priority": 6},  # priority > 5
    ],
)
def test_create_task_invalid_data_returns_422(payload):
    response = client.post("/tasks", json=payload)
    body = response.json()
    assert response.status_code == 422
    assert body["statusCode"] == 422
    assert body["data"] is None
    assert "ERR-VAL-422" in body["error"]


# =========================================================
# Chuc nang 3: PUT /tasks/{task_id}
def test_update_task_status_success():
    response = client.put("/tasks/1", json={"status": "in_progress"})
    body = response.json()
    assert response.status_code == 200
    assert body["data"]["status"] == "in_progress"
    assert body["path"] == "/tasks/1"


def test_update_task_status_not_found_returns_404():
    response = client.put("/tasks/999", json={"status": "in_progress"})
    body = response.json()
    assert response.status_code == 404
    assert "ERR-TASK-03" in body["error"]


def test_update_task_status_already_done_blocks_revert():
    # task id=2 co status ban dau la "done"
    response = client.put("/tasks/2", json={"status": "in_progress"})
    body = response.json()
    assert response.status_code == 400
    assert "ERR-TASK-04" in body["error"]


def test_update_task_status_invalid_enum_returns_422():
    response = client.put("/tasks/1", json={"status": "hoan_thanh_100%"})
    assert response.status_code == 422


# =========================================================
# Chuc nang 4: GET /tasks/analytics/dashboard
def test_dashboard_analytics_calculates_correct_rate():
    response = client.get("/tasks/analytics/dashboard")
    body = response.json()
    assert response.status_code == 200
    assert body["data"]["total_tasks"] == 2
    assert body["data"]["completed_tasks"] == 1
    assert body["data"]["completion_rate_percentage"] == 50.0


def test_dashboard_analytics_empty_no_division_by_zero():
    tasks_db.clear()
    response = client.get("/tasks/analytics/dashboard")
    body = response.json()
    assert response.status_code == 200
    assert body["data"]["total_tasks"] == 0
    assert body["data"]["completion_rate_percentage"] == 0.0