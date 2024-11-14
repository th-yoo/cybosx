import asyncio
from enum import Enum

from cybosx_login import login as _login

async def login(id: str, pw: str):
    return await asyncio.to_thread(_login, id, pw)
