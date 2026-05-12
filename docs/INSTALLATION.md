# Hướng dẫn Cài đặt — DichVuCong AI Assistant

> Phiên bản: v3.79 | Cập nhật: 2026-05-11

---

## Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Khởi động dịch vụ hạ tầng (Docker Compose)](#2-khởi-động-dịch-vụ-hạ-tầng-docker-compose)
3. [Cấu hình môi trường](#3-cấu-hình-môi-trường)
4. [Cài đặt Backend](#4-cài-đặt-backend)
5. [Cài đặt Frontend](#5-cài-đặt-frontend)
6. [Ingestion dữ liệu](#6-ingestion-dữ-liệu)
7. [Kiểm tra cài đặt](#7-kiểm-tra-cài-đặt)
8. [Triển khai với Ngrok (tùy chọn)](#8-triển-khai-với-ngrok-tùy-chọn)
9. [Chạy bộ kiểm thử](#9-chạy-bộ-kiểm-thử)

---

## 1. Yêu cầu hệ thống

### Phần mềm bắt buộc

| Phần mềm | Phiên bản tối thiểu | Ghi chú |
|---|---|---|
| Python | 3.12+ | Kiểm tra: `python --version` |
| Node.js | 18 LTS (khuyến nghị 20 LTS) | Kiểm tra: `node --version` |
| npm | 9+ | Đi kèm Node.js |
| Docker | 24+ | Kiểm tra: `docker --version` |
| Docker Compose | 2.20+ | Kiểm tra: `docker compose version` |
| LibreOffice | 7.x+ | Bắt buộc cho chuyển đổi .doc → PDF |
| Git | bất kỳ | Để clone repository |

### Cài đặt LibreOffice

LibreOffice headless được dùng để chuyển đổi tờ khai `.doc` sang PDF khi người dùng nộp form.

**Ubuntu/Debian:**
```bash
sudo apt-get install -y libreoffice libreoffice-l10n-vi
```

**Windows:**
Tải và cài đặt từ [https://www.libreoffice.org/download/](https://www.libreoffice.org/download/). Sau đó thêm thư mục cài đặt vào `PATH` hệ thống (ví dụ: `C:\Program Files\LibreOffice\program`).

**macOS:**
```bash
brew install libreoffice
```

### Phần cứng khuyến nghị

| Tài nguyên | Tối thiểu | Khuyến nghị |
|---|---|---|
| RAM | 4 GB | 8 GB+ |
| Ổ cứng | 10 GB trống | 20 GB+ |
| GPU | Không bắt buộc | CUDA-compatible (tăng tốc OCR) |
| CPU | 4 core | 8 core+ |

> **Lưu ý GPU:** Nếu có GPU CUDA, hệ thống sẽ tự động phát hiện và sử dụng để tăng tốc PaddleOCR và model embedding. Đặt `PADDLEOCR_USE_GPU=true` trong `.env`.

---

## 2. Khởi động dịch vụ hạ tầng (Docker Compose)

Dự án sử dụng 4 dịch vụ hạ tầng chạy qua Docker Compose:

| Dịch vụ | Image | Cổng | Mô tả |
|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | `5432` | Cơ sở dữ liệu quan hệ |
| Redis | `redis:7-alpine` | `6379` | Lưu trữ phiên (session) đã mã hóa |
| Qdrant | `qdrant/qdrant:latest` | `6333`, `6334` | Vector database cho RAG |
| MinIO | `minio/minio:latest` | `9000` (API), `9001` (Console) | Object storage (file/PDF) |

### Khởi động

Từ thư mục gốc của dự án:

```bash
# Khởi động tất cả dịch vụ hạ tầng
docker compose up -d

# Kiểm tra trạng thái
docker compose ps
```

Tất cả container cần ở trạng thái `healthy` hoặc `running` trước khi tiếp tục.

### Truy cập MinIO Console

Mở trình duyệt tại [http://localhost:9001](http://localhost:9001)

- **Username:** `minioadmin`
- **Password:** `minioadmin`

> Bucket `dichvucong` sẽ được tự động tạo khi backend khởi động.

---

## 3. Cấu hình môi trường

### 3.1 Tạo file `.env`

Sao chép từ file mẫu (nếu có) hoặc tạo mới tại thư mục gốc `dichvucong/.env`:

```bash
cp .env.example .env   # nếu có file mẫu
# hoặc tạo mới và điền theo bảng bên dưới
```

### 3.2 Tạo REDIS_ENCRYPTION_KEY

Key này bắt buộc phải có — backend sẽ từ chối khởi động nếu thiếu.

```python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Sao chép giá trị in ra và gán vào `REDIS_ENCRYPTION_KEY` trong `.env`.

### 3.3 Bảng biến môi trường đầy đủ

#### LLM (Bắt buộc)

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `""` | **Có** | API key của Anthropic (Claude) |
| `LLM_BACKEND` | `anthropic` | Không | Backend LLM: `anthropic` hoặc `gemini` |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Không | Model Claude đang dùng |
| `ROUTER_LLM_BACKEND` | `anthropic` | Không | Backend riêng cho router node: `anthropic` hoặc `local` |
| `LOCAL_LLM_URL` | `http://localhost:11434/v1` | Không | Endpoint Ollama (nếu dùng local LLM) |
| `LOCAL_LLM_MODEL` | `qwen2.5:3b-instruct` | Không | Model Ollama |
| `GOOGLE_API_KEY` | `""` | Không | API key Google (chỉ khi `LLM_BACKEND=gemini`) |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Không | Model Gemini |

> **Lưu ý:** Chỉ có `anthropic` là backend đang hoạt động trong phiên bản hiện tại. `ANTHROPIC_API_KEY` là bắt buộc.

#### Cơ sở dữ liệu

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `POSTGRES_URL` | `postgresql+asyncpg://dichvucong:dichvucong@localhost:5432/dichvucong` | Không | URL kết nối PostgreSQL |
| `REDIS_URL` | `redis://:dichvucong_redis_secret@localhost:6379/0` | Không | URL kết nối Redis (bao gồm password) |
| `QDRANT_URL` | `http://localhost:6333` | Không | URL kết nối Qdrant |

#### Bảo mật (Bắt buộc)

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `REDIS_ENCRYPTION_KEY` | `""` | **Có** | 32-byte Fernet key (xem mục 3.2) |
| `REDIS_PASSWORD` | `dichvucong_redis_secret` | **Có** | Phải khớp với `docker-compose.yml` |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | Không | Origin được phép (frontend URL) |
| `CORS_EXTRA_ORIGINS` | `""` | Không | Thêm origin, cách nhau bởi dấu phẩy (dùng cho Ngrok) |

#### MinIO (Object Storage)

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `MINIO_ENDPOINT` | `localhost:9000` | Không | Địa chỉ MinIO |
| `MINIO_ACCESS_KEY` | `minioadmin` | Không | Access key MinIO |
| `MINIO_SECRET_KEY` | `minioadmin` | Không | Secret key MinIO |
| `MINIO_BUCKET` | `dichvucong` | Không | Tên bucket |
| `MINIO_SECURE` | `false` | Không | Dùng HTTPS (`true`) hay HTTP (`false`) |

#### Embedding & RAG

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `EMBEDDING_BACKEND` | `bge-m3` | Không | Backend embedding: `bge-m3` hoặc `openai` |
| `OPENAI_API_KEY` | `""` | Không | Chỉ cần khi `EMBEDDING_BACKEND=openai` |
| `SENTENCE_TRANSFORMERS_HOME` | `.cache/` | Không | Thư mục cache model embedding |
| `QDRANT_COLLECTION` | `legal_documents` | Không | Tên collection Qdrant |
| `QDRANT_VECTOR_SIZE` | `1024` | Không | Số chiều vector (bge-m3: 1024) |
| `RAG_TOP_K` | `24` | Không | Số chunk tối đa trả về |
| `RAG_TOKEN_BUDGET` | `6000` | Không | Giới hạn token context RAG |
| `RAG_MIN_SCORE_THRESHOLD` | `0.01` | Không | Ngưỡng điểm RRF tối thiểu |

#### OCR

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `PADDLEOCR_USE_GPU` | `false` | Không | Bật GPU cho PaddleOCR |
| `PADDLEOCR_LANG` | `vi` | Không | Ngôn ngữ OCR |
| `OCR_QR_MAX_ATTEMPTS` | `5` | Không | Số lần thử decode QR |
| `OCR_CONFIDENCE_THRESHOLD` | `0.7` | Không | Ngưỡng tin cậy tối thiểu của OCR |
| `OCR_RAW_TOKEN_CAP` | `8000` | Không | Giới hạn token text OCR thô |

#### Quan sát (Tùy chọn)

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `LANGSMITH_API_KEY` | `""` | Không | API key LangSmith để theo dõi agent |
| `LANGCHAIN_TRACING_V2` | `true` | Không | Bật LangSmith tracing |
| `LANGCHAIN_PROJECT` | `dichvucong` | Không | Tên dự án trên LangSmith |

#### Rate Limiting & Ứng dụng

| Biến | Mặc định | Bắt buộc | Mô tả |
|---|---|---|---|
| `CHAT_RATE_LIMIT` | `10/minute` | Không | Giới hạn yêu cầu chat |
| `UPLOAD_RATE_LIMIT` | `5/minute` | Không | Giới hạn yêu cầu upload |
| `ENVIRONMENT` | `development` | Không | `development` hoặc `production` |
| `LOG_LEVEL` | `INFO` | Không | Mức độ log: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## 4. Cài đặt Backend

Tất cả lệnh dưới đây chạy trong thư mục `backend/`.

### 4.1 Tạo môi trường ảo Python

```bash
cd backend
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source .venv/bin/activate
```

### 4.2 Cài đặt thư viện

```bash
pip install -r requirements.txt
```

> **Lưu ý:** Lần đầu cài đặt sẽ tải model PaddleOCR và bge-m3 (~1.5 GB). Quá trình có thể mất 5–15 phút tùy tốc độ mạng.

### 4.3 Chạy migration cơ sở dữ liệu

```bash
# Từ thư mục backend/
PYTHONPATH=. alembic upgrade head
```

Lệnh này tạo 7 bảng trong PostgreSQL:
- `procedures`, `procedure_dependencies`, `procedure_categories`
- `legal_documents`, `form_templates`
- `sessions`
- `administrative_units`

### 4.4 Khởi động server

```bash
# Chế độ phát triển (tự động tải lại khi có thay đổi)
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Chế độ production
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Sau khi khởi động, truy cập:
- API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

> **Lần đầu khởi động:** Model embedding bge-m3 (~1.5 GB) sẽ được tải vào bộ nhớ. Endpoint `/health` trả về `503` cho đến khi model sẵn sàng (thường 30–120 giây).

---

## 5. Cài đặt Frontend

Tất cả lệnh dưới đây chạy trong thư mục `frontend/`.

### 5.1 Cài đặt dependencies

```bash
cd frontend
npm install
```

### 5.2 Cấu hình môi trường frontend

Tạo file `frontend/.env.local`:

```bash
# URL backend API (khi chạy local)
NEXT_PUBLIC_API_URL=http://localhost:8000

# URL backend API công khai (chỉ cần khi dùng Ngrok)
NEXT_PUBLIC_API_URL_PUBLIC=

# PIN bảo vệ (mặc định: 2026)
NEXT_PUBLIC_ACCESS_PIN=2026
```

### 5.3 Khởi động server

```bash
# Chế độ phát triển
npm run dev

# Build và chạy production
npm run build
npm start
```

Truy cập: [http://localhost:3000](http://localhost:3000)

---

## 6. Ingestion dữ liệu

Các script ingestion phải chạy **theo đúng thứ tự** dưới đây. Đảm bảo Docker Compose và backend đã sẵn sàng trước khi chạy.

Tất cả lệnh chạy từ thư mục `backend/` với virtual environment đã kích hoạt.

### Bước 1 — Seed đơn vị hành chính

```bash
PYTHONPATH=. python ingestion/seed_administrative_units.py
```

Thời gian: ~1 phút. Nạp bảng tra cứu tỉnh/huyện/xã của Việt Nam.

### Bước 2 — Seed thủ tục hành chính

```bash
PYTHONPATH=. python ingestion/ingest_procedures.py
```

Thời gian: ~30 giây. Tạo 7 thủ tục trong 3 lĩnh vực và các cạnh phụ thuộc DAG.

| Lĩnh vực | Thủ tục |
|---|---|
| Cư trú (housing) | Đăng ký thường trú, Đăng ký tạm trú, Xác nhận thông tin cư trú |
| Hộ tịch (civil_registration) | Đăng ký khai sinh, Cấp bản sao trích lục hộ tịch |
| Nuôi con nuôi (adoption) | Đăng ký nuôi con nuôi, Đăng ký lại nuôi con nuôi |

### Bước 3 — Ingestion tài liệu pháp luật

```bash
PYTHONPATH=. python ingestion/ingest_full_documents.py
```

> **Cảnh báo:** Quá trình này mất **10–30 phút** tùy phần cứng. Nó xử lý 19 văn bản pháp luật, phân đoạn theo Điều, tạo embedding và đẩy lên Qdrant (~904 điểm dữ liệu).

**Không chạy script này hai lần đồng thời.** Trên Windows, kiểm tra Task Manager để xác nhận tiến trình trước đó đã kết thúc hoàn toàn trước khi chạy lại.

### Bước 4 (tùy chọn) — Ingestion chunk thủ công

```bash
PYTHONPATH=. python ingestion/ingest_manual_chunks.py
```

Nạp các chunk bổ sung được định nghĩa thủ công trong `ingestion/manual_chunks/`.

---

## 7. Kiểm tra cài đặt

### 7.1 Health check

```bash
curl http://localhost:8000/health
```

Phản hồi kỳ vọng khi hệ thống sẵn sàng:

```json
{
  "status": "ready",
  "embedding_model": "loaded",
  "services": {
    "qdrant": true,
    "redis": true,
    "postgres": true
  },
  "gpu": {
    "cuda_available": false,
    "device_name": null
  }
}
```

Nếu `status` là `"warming_up"` hoặc `"embedding_model": "not_loaded"`, hãy đợi thêm 30–60 giây và thử lại.

### 7.2 Kiểm tra chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Đăng ký thường trú cần những giấy tờ gì?", "session_id": "test-session-001"}' \
  --no-buffer
```

Kết quả trả về là stream SSE với các event pipeline và câu trả lời của AI.

### 7.3 Kiểm tra frontend

Mở trình duyệt tại [http://localhost:3000](http://localhost:3000). Nhập PIN `2026` khi được yêu cầu. Widget chat AI sẽ xuất hiện ở góc dưới bên phải.

---

## 8. Triển khai với Ngrok (tùy chọn)

Ngrok cho phép expose backend và frontend ra internet để demo từ xa.

### 8.1 Expose backend

```bash
ngrok http 8000
```

Sao chép URL HTTPS nhận được (ví dụ: `https://abc123.ngrok-free.app`).

### 8.2 Cập nhật cấu hình

Trong `.env` (backend):
```bash
CORS_EXTRA_ORIGINS=https://abc123.ngrok-free.app,https://your-frontend.ngrok-free.app
```

Trong `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL_PUBLIC=https://abc123.ngrok-free.app
```

Khởi động lại cả backend và frontend sau khi thay đổi.

---

## 9. Chạy bộ kiểm thử

### Unit tests (không cần Docker)

```bash
cd backend
PYTHONPATH=. .venv/Scripts/pytest tests/unit/ -v        # Windows
PYTHONPATH=. .venv/bin/pytest tests/unit/ -v            # macOS/Linux
```

Kết quả kỳ vọng: **366 tests passed**.

### Chạy với coverage report

```bash
PYTHONPATH=. pytest tests/unit/ --cov=app --cov-report=term-missing
```

### Integration tests (cần Docker đang chạy)

```bash
PYTHONPATH=. pytest tests/integration/ -v
```

### Benchmark router

```bash
PYTHONPATH=. python scripts/benchmark/run_benchmark.py
```

Kết quả đánh giá độ chính xác của router node trên 23 trường hợp kiểm thử.
