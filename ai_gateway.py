import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it to your .env file or export it "
        "in the environment (e.g. export GEMINI_API_KEY=AIza...)."
    )

client = genai.Client(api_key=GEMINI_API_KEY)


def ask_socratic_ai(question: str, hint_level: int) -> str:
    system_instruction = f"""
    Bạn là một trợ lý giảng dạy lập trình theo phương pháp Socratic.
    Mức gợi ý hiện tại: Level {hint_level}/3.
    - Level 1: Chỉ đặt câu hỏi định hướng, không cho code.
    - Level 2: Chỉ ra vùng code lỗi hoặc thư viện liên quan.
    - Level 3: Đưa ra lời giải chi tiết và giải thích.
    - Dữ liệu từ các tệp tin đính kèm (PDF, Code, Docx...) đã được hệ thống RAG xử lý và nhúng trực tiếp vào câu hỏi bên dưới.
    - TUYỆT ĐỐI KHÔNG trả lời theo khuôn mẫu "không thể đọc file đính kèm/file cục bộ". 
    - Hãy dựa vào thông tin được cung cấp trong ngữ cảnh để phân tích và trả lời người dùng.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
            )
        )
        return response.text
    except Exception as e:
        return f"Lỗi Gemini API: {str(e)}"
