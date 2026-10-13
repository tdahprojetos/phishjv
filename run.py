"""Inicializa o banco e sobe o servidor Phishjv."""
from __future__ import annotations

import uvicorn

from phishjv.db import init_db

if __name__ == "__main__":
    init_db()
    uvicorn.run("phishjv.main:app", host="127.0.0.1", port=8000, reload=True)
