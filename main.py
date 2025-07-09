# main.py
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from db_settings import DBConnection
from pydantic import BaseModel, AnyUrl
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import psycopg

class Category(str, Enum):
    NotAbleToSolve = "NotAbleToSolve"
    BuildConfidence = "BuildConfidence"
    Confident = "Confident"

class SpacedRepetition(BaseModel):
    url: AnyUrl
    current_stage: Category = Category.NotAbleToSolve
    next_pick_day: int
    is_active: Optional[bool] = True

class PatchSpacedRepetition(BaseModel):
    current_stage: Category
    next_pick_day: int
    is_active: Optional[bool] = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    await DBConnection.create_pool()
    print("DB Pool created")
    yield
    # Teardown
    await DBConnection.close_pool()
    print("DB Pool closed")

app = FastAPI(lifespan=lifespan)



@app.get("/")
async def read_root():
    pool = DBConnection._pool
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT now()")
        return {"result": str(result[0]['now'])}

@app.post("/space-repetition/create")
async def create_spaced_repetition(item: SpacedRepetition):
    ist = ZoneInfo("Asia/Kolkata")
    next_pick_date = datetime.now(ist).date() + timedelta(days=item.next_pick_day)

    query = """
    INSERT INTO review_schedules 
    (problem_url, current_stage, is_active, next_pick_date)
    VALUES (%(url)s, %(current_stage)s, %(is_active)s, %(next_pick_date)s)
    RETURNING *;
    """

    values = {
        "url": str(item.url),
        "current_stage": item.current_stage.value,
        "is_active": item.is_active,
        "next_pick_date": next_pick_date
    }
    try:
        async with DBConnection._pool.connection() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(query, values)
                row = await cur.fetchone()
                await conn.commit()  # Important: commit the transaction
                
                if row:
                    return row
    except Exception as e:
        raise HTTPException(status_code=500, detail="Insert failed")

@app.get("/spaced-repetition/daily-questions")
async def get_daily_questions():
    ist = ZoneInfo("Asia/Kolkata")
    current_date = datetime.now(ist).date()
    query = """
        SELECT problem_url, current_stage, next_pick_date
        FROM review_schedules
        WHERE next_pick_date = %(current_date)s and is_active=true;
    """
    async with DBConnection._pool.connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(query, {"current_date": current_date})
            row = await cur.fetchall()
            return row

@app.put("/spaced-repetition/question-update/{id}")
async def update_question(id: int, item: PatchSpacedRepetition):
    ist = ZoneInfo("Asia/Kolkata")
    next_pick_date = datetime.now(ist).date() + timedelta(days=item.next_pick_day)
    query = """
        UPDATE review_schedules
        SET current_stage = %(current_stage)s,
            next_pick_date = %(next_pick_date)s,
            is_active = %(is_active)s,
            record_last_updated = now() AT TIME ZONE 'Asia/Kolkata'
        WHERE id = %(id)s
        RETURNING *;
    """
    values = {
        "current_stage": item.current_stage.value,
        "next_pick_date": next_pick_date,
        "is_active": item.is_active,
        "id": id
    }
    async with DBConnection._pool.connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(query, values)
            row = await cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Record not found.")
            return row