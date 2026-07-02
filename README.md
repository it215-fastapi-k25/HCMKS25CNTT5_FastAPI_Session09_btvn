# BÁO CÁO PHÂN TÍCH THIẾT KẾ
## Mini Project: Hệ thống API Quản lý Công việc Nhóm (Team Task Manager API)

**Lớp:** HNKS25CNTT1
**Môn học:** FastAPI Backend Development
**Bài tập:** Mini Project - Team Task Manager API

---

## 1. Mục tiêu và phạm vi

Xây dựng RESTful API quản lý công việc nhóm với kiến trúc decoupled, sử dụng
`tasks_db` (List[dict]) làm cơ sở dữ liệu mô phỏng trong bộ nhớ, validate dữ liệu
tại tầng Gateway bằng Pydantic, và chuẩn hóa mọi phản hồi qua Unified Envelope
JSON 6 trường.

---

## 2. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT (Postman /                       │
│                          Swagger UI / Frontend)                  │
└───────────────────────────────┬───────────────────────────────────┘
                                 │  HTTP Request (JSON)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TẦNG GATEWAY (FastAPI + Pydantic)              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Pydantic Schemas: TaskCreateSchema, TaskStatusUpdateSchema │  │
│  │  -> Field(min_length, max_length, ge, le) tự động chặn      │  │
│  │     dữ liệu bẩn trước khi vào Endpoint                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TẦNG ENDPOINT (Path Operation Functions)          │
│   get_all_tasks()   create_task()   update_task_status()          │
│                    get_dashboard_analytics()                      │
└───────┬─────────────────┬──────────────────┬──────────────────────┘
        │                 │                  │
        ▼                 ▼                  ▼
┌───────────────┐ ┌────────────────┐ ┌──────────────────────┐
│ HELPER FUNCS   │ │ BUSINESS RULES │ │ calculate_team_metrics│
│ find_task_by_id│ │ ERR-TASK-01    │ │ (Pure function,       │
│ is_title_dup.  │ │ ERR-TASK-03    │ │  return Tuple 3 giá   │
│ get_next_id    │ │ ERR-TASK-04    │ │  trị, KHÔNG dùng      │
└───────┬────────┘ └────────┬───────┘ │  HTTPException)       │
        │                   │         └───────────┬───────────┘
        └─────────┬─────────┴─────────────────────┘
                   ▼
         ┌───────────────────┐
         │   tasks_db: List   │   <-- In-memory Database
         │   (List[dict])     │
         └───────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│              build_envelope() - Unified Envelope JSON             │
│   { statusCode, message, data, error, timestamp, path }           │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
                          CLIENT nhận JSON
```

---

## 3. Luồng xử lý lỗi tập trung (Exception Handling Flow)

```
                     Request đi vào Endpoint
                              │
              ┌───────────────┼────────────────┐
              ▼                                 ▼
     Sai định dạng Pydantic            Dữ liệu hợp lệ về mặt
     (title < 3 ký tự,                 kiểu dữ liệu (đi tiếp
     priority ngoài 1-5, ...)          vào logic nghiệp vụ)
              │                                 │
              ▼                                 ▼
  RequestValidationError            Kiểm tra Business Rule
  -> validation_exception_handler   (trùng title / not found /
     -> HTTP 422 (ERR-VAL-422)         đã done)
                                              │
                              ┌───────────────┼───────────────┐
                              ▼                               ▼
                    Vi phạm Business Rule            Hợp lệ hoàn toàn
                    -> raise BusinessException        -> Xử lý thành công
                    -> business_exception_handler      -> HTTP 200/201
                       -> HTTP 400/404 (ERR-TASK-xx)

                              (ngoài luồng)
                                    │
                                    ▼
                    Lỗi Runtime không lường trước
                    (chia 0, ép kiểu sai, KeyError...)
                    -> global_exception_handler
                       -> HTTP 500 (ERR-SYS-500)
                       -> KHÔNG lộ Stack Trace (OWASP A05)
```

Tất cả 4 nhánh trên đều đi qua `build_envelope()` trước khi trả về Client,
đảm bảo 100% response — kể cả lỗi — luôn đúng cấu trúc JSON 6 trường.

---

## 4. Mô hình dữ liệu (Data Model)

| Trường        | Kiểu    | Ràng buộc                                   |
|---------------|---------|----------------------------------------------|
| id            | int     | Tự sinh, `max_id + 1`                         |
| title         | str     | `min_length=3, max_length=100`, không trùng   |
| description   | str     | Bắt buộc, không được rỗng                     |
| assignee      | str     | Bắt buộc, không khoảng trắng thừa             |
| priority      | int     | `ge=1, le=5`                                  |
| status        | Enum    | `todo` / `in_progress` / `done`               |
| created_at    | str     | Tự sinh theo ISO 8601 khi tạo mới              |

**Quy tắc chuyển trạng thái:** một khi `status == "done"`, hệ thống chặn mọi
yêu cầu cập nhật lùi (ERR-TASK-04) — đảm bảo tính toàn vẹn tiến độ công việc.

---

## 5. Bảng ánh xạ Endpoint

| # | Hàm xử lý                | Method & Path                  | Mã lỗi nghiệp vụ liên quan     |
|---|---------------------------|---------------------------------|----------------------------------|
| 1 | `get_all_tasks`           | `GET /tasks`                    | — (mảng rỗng không phải lỗi)     |
| 2 | `create_task`              | `POST /tasks`                   | `ERR-TASK-01` (400)              |
| 3 | `update_task_status`       | `PUT /tasks/{task_id}`          | `ERR-TASK-03` (404), `ERR-TASK-04` (400) |
| 4 | `get_dashboard_analytics`  | `GET /tasks/analytics/dashboard`| — (gọi `calculate_team_metrics`) |

---

## 6. Tách bạch Pure Function khỏi tầng HTTP

`calculate_team_metrics()` được thiết kế là hàm thuần túy (pure function):
nhận dữ liệu từ `tasks_db`, tính toán, và `return` về đúng một `Tuple` gồm
`(total_tasks, completed_tasks, completion_rate_percentage)`. Hàm này **không**
import hay sử dụng bất kỳ thành phần nào của FastAPI, giúp:

- Dễ viết Unit Test độc lập, không cần khởi động server.
- Tách biệt rõ ràng "logic tính toán" khỏi "logic điều phối HTTP"
  (`get_dashboard_analytics` đóng vai trò Router/Controller, chỉ gọi hàm và
  đóng gói kết quả vào Envelope).

---

## 7. Kiểm thử (Testing)

Bộ test (`HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_test.py`) dùng
`fastapi.testclient.TestClient`, gồm 16 test case bao phủ:

- Danh sách rỗng / có dữ liệu / lọc theo `status`.
- Tạo task thành công, trùng tiêu đề (400), 5 trường hợp validate 422.
- Cập nhật trạng thái thành công, không tìm thấy (404), chặn cập nhật lùi (400).
- Thống kê dashboard đúng tỷ lệ, và không chia cho 0 khi `tasks_db` rỗng.

Kết quả chạy thực tế: **16/16 test PASSED**.

---

## 8. Cấu trúc file nộp bài

```
HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_main.py         # Toàn bộ API
HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_test.py          # Test suite
HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_requirements.txt # Thư viện
HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_PhanTich.md      # Báo cáo này
```

**Lệnh chạy server:**
```
uvicorn HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_main:app --reload
```

**Lệnh chạy test:**
```
pytest HNKS25CNTT1_MiniProject_TeamTaskManagerAPI_test.py -v
```