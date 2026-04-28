# coding=utf-8
from fastapi import HTTPException
from database import get_connection, release_connection

async def fetch_all(query: str, *args):
    conn = await get_connection()
    try:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]
    finally:
        await release_connection(conn)

async def fetch_one(query: str, not_found_msg: str, *args):
    conn = await get_connection()
    try:
        row = await conn.fetchrow(query, *args)
        if not row:
            raise HTTPException(404, not_found_msg)
        return dict(row)
    finally:
        await release_connection(conn)

async def execute_returning(query: str, not_found_msg: str | None, *args):
    conn = await get_connection()
    try:
        row = await conn.fetchrow(query, *args)
        if not row and not_found_msg:
            raise HTTPException(404, not_found_msg)
        return dict(row) if row else None
    finally:
        await release_connection(conn)

async def execute_query(query: str, *args):
    conn = await get_connection()
    try:
        await conn.execute(query, *args)
    finally:
        await release_connection(conn)
