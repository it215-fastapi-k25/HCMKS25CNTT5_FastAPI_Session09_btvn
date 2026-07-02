"""
Mini Project: He thong API quan ly cong viec nhom (Team Task Manager API)
Mo ta: Toan bo du lieu duoc mo phong bang bien tasks_db (List[dict]) trong bo nho.
       Tat ca phan hoi (thanh cong lan that bai) deu duoc boc qua Unified Envelope JSON 6 truong:
       statusCode, message, data, error, timestamp, path.
"""

from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator


tasks_db: List[dict] = [
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

class TaskStatus(str, Enum):
    """Cac trang thai hop le cua mot cong viec."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskCreateSchema(BaseModel):
    """Schema nhan du lieu khi tao moi cong viec (POST /tasks)."""

    title: str = Field(..., min_length=3, max_length=100, description="Tieu de cong viec")
    description: str = Field(..., min_length=1, description="Mo ta chi tiet cong viec")
    assignee: str = Field(..., min_length=1, description="Nguoi duoc giao viec")
    priority: int = Field(..., ge=1, le=5, description="Do uu tien tu 1 (thap) den 5 (cao)")

    @field_validator("description")
    @classmethod
    def description_khong_duoc_rong(cls, gia_tri: str) -> str:
        # Chan chuoi rong hoac chi toan khoang trang
        if not gia_tri.strip():
            raise ValueError("description khong duoc la chuoi rong")
        return gia_tri

    @field_validator("assignee")
    @classmethod
    def assignee_khong_khoang_trang_thua(cls, gia_tri: str) -> str:
        # Chan chuoi rong va chuoi co khoang trang du thua o dau/cuoi hoac o giua
        if not gia_tri.strip():
            raise ValueError("assignee khong duoc la chuoi rong")
        if gia_tri != gia_tri.strip() or "  " in gia_tri:
            raise ValueError("assignee khong duoc chua khoang trang thua")
        return gia_tri


class TaskStatusUpdateSchema(BaseModel):
    """Schema nhan du lieu khi cap nhat trang thai (PUT /tasks/{task_id})."""

    status: TaskStatus = Field(..., description="Trang thai moi cua cong viec")


class TaskResponseSchema(BaseModel):
    """Schema chuan hoa du lieu tra ve cho 1 task (dung lam tai lieu tham chieu / Swagger)."""

    id: int
    title: str
    description: str
    assignee: str
    priority: int
    status: str
    created_at: str


# =========================================================
# 3. CUSTOM EXCEPTION (Loi nghiep vu mang theo ma loi rieng)
# =========================================================
class BusinessException(Exception):
    """Loi nghiep vu tuy chinh: mang theo statusCode HTTP + ma loi noi bo + message tieng Viet."""

    def __init__(self, status_code: int, error_code: str, message: str, error_detail: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.error_detail = error_detail


# =========================================================
# 4. HELPER FUNCTIONS (Tach rieng khoi Endpoint, khong chua logic HTTP)
# =========================================================
def build_envelope(status_code: int, message: str, data, error, path: str) -> dict:
    """Dong goi moi phan hoi ve dung cau truc Unified Envelope 6 truong bat buoc."""
    return {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": path,
    }


def find_task_by_id(task_id: int) -> Optional[dict]:
    """Tim task theo id, tra ve None neu khong tim thay."""
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    return None


def is_title_duplicated(title: str) -> bool:
    """Kiem tra tieu de da ton tai trong he thong hay chua (khong phan biet hoa/thuong, bo khoang trang thua)."""
    return any(task["title"].strip().lower() == title.strip().lower() for task in tasks_db)


def get_next_id() -> int:
    """Sinh id tu dong theo quy tac max_id + 1."""
    if not tasks_db:
        return 1
    return max(task["id"] for task in tasks_db) + 1


def calculate_team_metrics() -> tuple:
    """
    Ham tinh toan thuan tuy (Pure function).
    KHONG chua bat ky code FastAPI Response hay HTTPException nao ben trong.
    Tra ve Tuple 3 gia tri: (tong_so_cong_viec, so_luong_da_hoan_thanh, ty_le_hoan_thanh_phan_tram)
    """
    total_tasks = len(tasks_db)
    completed_tasks = sum(1 for task in tasks_db if task["status"] == TaskStatus.DONE.value)
    completion_rate = round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0.0
    return total_tasks, completed_tasks, completion_rate


# =========================================================
# 5. KHOI TAO APP & GLOBAL EXCEPTION HANDLERS (Bay loi tap trung)
# =========================================================
app = FastAPI(
    title="Team Task Manager API",
    description="He thong API quan ly cong viec nhom - HNKS25CNTT1 Mini Project",
    version="1.0.0",
)


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """Bat cac loi nghiep vu tuy chinh (trung tieu de, khong tim thay, sai trang thai lui...)."""
    envelope = build_envelope(
        status_code=exc.status_code,
        message=exc.message,
        data=None,
        error=f"{exc.error_code}: {exc.error_detail}",
        path=str(request.url.path),
    )
    return JSONResponse(status_code=exc.status_code, content=envelope)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Bat loi 422 khi du lieu dau vao vi pham rang buoc Pydantic Field (ERR-VAL-422)."""
    envelope = build_envelope(
        status_code=422,
        message="Lỗi: Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
        data=None,
        error="ERR-VAL-422: Validation error at Request Body fields constraint layout.",
        path=str(request.url.path),
    )
    return JSONResponse(status_code=422, content=envelope)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Bay loi toan cuc (Global Exception Handler) - tuan thu OWASP A05.
    Chan tuyet doi Stack Trace tho (ten file, so dong loi Python) lo ra ngoai Client.
    """
    envelope = build_envelope(
        status_code=500,
        message="Lỗi hệ thống nội bộ, vui lòng thử lại sau!",
        data=None,
        error="ERR-SYS-500: Internal Server Error - unexpected runtime exception.",
        path=str(request.url.path),
    )
    return JSONResponse(status_code=500, content=envelope)


# =========================================================
# 6. ENDPOINTS (Path Operation Functions)
# =========================================================
@app.get("/tasks")
def get_all_tasks(status: Optional[str] = None):
    """Chuc nang 1: Xem danh sach cong viec, ho tro loc theo query param status."""
    result = tasks_db
    if status is not None:
        result = [task for task in tasks_db if task["status"] == status]

    return build_envelope(
        status_code=200,
        message="Lấy danh sách công việc thành công!",
        data=jsonable_encoder(result),
        error=None,
        path="/tasks",
    )


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreateSchema):
    """Chuc nang 2: Tao moi cong viec, tu sinh id/status/created_at, chan trung tieu de."""
    if is_title_duplicated(task_in.title):
        raise BusinessException(
            status_code=400,
            error_code="ERR-TASK-01",
            message="Lỗi: Tiêu đề công việc này đã tồn tại trong nhóm!",
            error_detail="Task conflict: Title field duplicates an existing record.",
        )

    new_task = {
        "id": get_next_id(),
        "title": task_in.title,
        "description": task_in.description,
        "assignee": task_in.assignee,
        "priority": task_in.priority,
        "status": TaskStatus.TODO.value,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    tasks_db.append(new_task)

    return build_envelope(
        status_code=201,
        message="Khởi tạo công việc mới thành công!",
        data=jsonable_encoder(new_task),
        error=None,
        path="/tasks",
    )


@app.put("/tasks/{task_id}")
def update_task_status(task_id: int, status_in: TaskStatusUpdateSchema):
    """Chuc nang 3: Cap nhat trang thai tien do cong viec theo task_id."""
    task = find_task_by_id(task_id)
    if task is None:
        raise BusinessException(
            status_code=404,
            error_code="ERR-TASK-03",
            message="Lỗi: Không tìm thấy công việc với ID đã cho!",
            error_detail=f"Task not found: id={task_id} does not exist in tasks_db.",
        )

    if task["status"] == TaskStatus.DONE.value:
        raise BusinessException(
            status_code=400,
            error_code="ERR-TASK-04",
            message="Lỗi: Công việc đã hoàn thành, không thể cập nhật lùi trạng thái!",
            error_detail="Task state conflict: cannot revert status of a completed task.",
        )

    task["status"] = status_in.status.value

    return build_envelope(
        status_code=200,
        message="Cập nhật tiến độ công việc thành công!",
        data=jsonable_encoder(task),
        error=None,
        path=f"/tasks/{task_id}",
    )


@app.get("/tasks/analytics/dashboard")
def get_dashboard_analytics():
    """Chuc nang 4: Ham dieu phoi - goi calculate_team_metrics() va dong goi ket qua JSON 6 truong."""
    total_tasks, completed_tasks, completion_rate = calculate_team_metrics()

    return build_envelope(
        status_code=200,
        message="Lấy số liệu thống kê hiệu suất nhóm thành công!",
        data={
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate_percentage": completion_rate,
        },
        error=None,
        path="/tasks/analytics/dashboard",
    )

