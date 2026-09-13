import os
import logging
from typing import Optional
import chromadb

from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings,
)
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(
            self,
            db_path: str = "./chroma_db",
            collection_name: str = "codebase_rag",
            api_key: Optional[str] = None,
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY chưa được thiết lập. Hãy thêm nó vào file .env!"
            )

        # Embedding Model
        Settings.embed_model = GeminiEmbedding(
            model_name="models/text-embedding-004",
            api_key=self.api_key,
        )

        # Gemini 2.5 Flash
        Settings.llm = Gemini(
            model_name="gemini-2.5-flash",
            api_key=self.api_key,
            temperature=0.2,
        )

        # Khởi tạo ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )

        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context,
        )

        self.query_engine: Optional[BaseQueryEngine] = None

    def ingest_documents(self, directory_path: str) -> int:
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        reader = SimpleDirectoryReader(
            input_dir=directory_path,
            recursive=True,
            # Bổ sung .pdf và .docx để xử lý file tài liệu/đề thi
            required_exts=[".md", ".py", ".txt", ".json", ".js", ".html", ".css", ".pdf", ".docx"],
        )
        documents = reader.load_data()

        if not documents:
            return 0

        self.index = VectorStoreIndex.from_documents(
            documents=documents,
            storage_context=self.storage_context,
            show_progress=True,
        )

        self.query_engine = None
        return len(documents)

    def query(self, user_query: str, similarity_top_k: int = 3) -> str:
        if not user_query or not user_query.strip():
            return "Câu hỏi không được để rỗng."

        try:
            if self.query_engine is None:
                self.query_engine = self.index.as_query_engine(
                    similarity_top_k=similarity_top_k
                )

            response = self.query_engine.query(user_query)
            return str(response)

        except Exception as e:
            return f"Lỗi khi tra cứu kiến thức: {str(e)}"