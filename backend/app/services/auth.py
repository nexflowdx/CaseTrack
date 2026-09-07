import httpx
from fastapi import Header, HTTPException

from app.config import API_LOGIN_BASE_URL


async def get_current_employee(authorization: str = Header(...)) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_LOGIN_BASE_URL}/me",
            headers={"Authorization": authorization},
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    return response.json()