import os
import shutil
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from logger import app as logger_app
from ai_gateway import ask_socratic_ai
from rag_service import RAGService

app = FastAPI(
    title="AI Technical Debt Solver API",
    description="Hệ thống tự động hỗ trợ giải quyết Technical Debt & Tra cứu Codebase bằng RAG",
    version="1.1.0"
)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/logger", logger_app)

rag_service = None
try:
    rag_service = RAGService(db_path="./chroma_db", collection_name="codebase_rag")
except Exception as e:
    print(f"[Warning] Chưa thể khởi tạo RAG Service: {e}")


class SocraticRequest(BaseModel):
    user_id: str = Field(default="student_01", description="ID người dùng")
    question: str = Field(..., min_length=1, description="Mã lỗi hoặc câu hỏi của lập trình viên")
    hint_level: int = Field(default=1, ge=1, le=3, description="Mức gợi ý từ 1 đến 3")

class SocraticResponse(BaseModel):
    response: str

class RAGIngestRequest(BaseModel):
    directory_path: str = Field(..., description="Đường dẫn thư mục chứa tài liệu/codebase")

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi tra cứu tài liệu")
    similarity_top_k: Optional[int] = Field(default=3, ge=1, le=10)

class RAGResponse(BaseModel):
    answer: str


@app.get("/")
async def root():
    return {"status": "online", "message": "Backend AI Technical Debt Solver đang hoạt động!"}


@app.post("/api/v1/socratic", response_model=SocraticResponse)
def handle_socratic_ai(payload: SocraticRequest):
    try:
        context_text = ""
        # Tra cứu thông tin từ tài liệu RAG nếu dịch vụ đã sẵn sàng
        if rag_service:
            try:
                rag_result = rag_service.query(user_query=payload.question)
                if rag_result and "Lỗi khi tra cứu" not in rag_result:
                    context_text = f"\n\n[Thông tin tra cứu từ tài liệu đính kèm/Codebase]:\n{rag_result}"
            except Exception as rag_err:
                print(f"[Warning] Lỗi khi lấy context RAG: {rag_err}")

        # Ghép câu hỏi gốc với nội dung trích xuất từ tài liệu RAG
        full_prompt = f"{payload.question}{context_text}"
        
        response_text = ask_socratic_ai(full_prompt, payload.hint_level)
        return SocraticResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi AI Gateway: {str(e)}")


@app.post("/api/v1/upload")
def upload_file(file: UploadFile = File(...)):
    if not rag_service:
        raise HTTPException(status_code=500, detail="RAG Service chưa sẵn sàng.")
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Nạp lại toàn bộ tài liệu trong thư mục uploads vào ChromaDB
        count = rag_service.ingest_documents(UPLOAD_DIR)
        return {
            "status": "success",
            "message": f"Đã nhận file '{file.filename}' và nạp vào RAG!",
            "documents_ingested": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file: {str(e)}")


@app.post("/api/v1/rag/ingest", status_code=200)
async def ingest_documents(payload: RAGIngestRequest):
    if not rag_service:
        raise HTTPException(status_code=500, detail="RAG Service chưa sẵn sàng.")
    try:
        count = rag_service.ingest_documents(payload.directory_path)
        return {"status": "success", "message": "Nạp tài liệu thành công!", "documents_ingested": count}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Ingest RAG: {str(e)}")


@app.post("/api/v1/rag/query", response_model=RAGResponse)
async def query_rag(payload: RAGQueryRequest):
    if not rag_service:
        raise HTTPException(status_code=500, detail="RAG Service chưa sẵn sàng.")
    try:
        answer = rag_service.query(
            user_query=payload.query,
            similarity_top_k=payload.similarity_top_k
        )
        return RAGResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Query RAG: {str(e)}")