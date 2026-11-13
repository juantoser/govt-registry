import os
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, JsonValue

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://demo:demo@127.0.0.1:5432/registry"
)

app = FastAPI(title="Company Registry Demo", version="0.1.0")


class CompanySummary(BaseModel):
    registry_code: str
    name: str


class CompanyDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    ariregistri_kood: int
    nimi: str
    yldandmed: dict[str, JsonValue]


@app.get("/companies", response_model=list[CompanySummary])
def list_companies(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        return connection.execute(
            """
            SELECT registry_code, name
            FROM companies
            ORDER BY registry_code
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()


@app.get(
    "/companies/{registry_code}",
    response_model=CompanyDetail,
    responses={404: {"description": "Company not found"}},
)
def get_company(registry_code: str):
    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT data FROM companies WHERE registry_code = %s",
            (registry_code,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")

    return row[0]
