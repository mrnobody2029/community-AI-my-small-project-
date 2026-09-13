from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI()


class LogRequest(BaseModel):
    user_id: str
    question: str
    hints_used: int
    completed: bool


@app.post("/api/log")
def create_log(log: LogRequest):
    try:
        with sqlite3.connect("learning_logs.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs (timestamp, user_id, question, hints_used, completed)
                VALUES (datetime('now'), ?, ?, ?, ?)
            """, (log.user_id, log.question, log.hints_used, log.completed))
            conn.commit()
        return {"status": "success", "message": "Log saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/{user_id}")
def get_user_stats(user_id: str):
    try:
        with sqlite3.connect("learning_logs.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(hints_used) FROM logs WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

        if not row or row[0] == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user_id": user_id, "total_questions": row[0], "total_hints": row[1] or 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))