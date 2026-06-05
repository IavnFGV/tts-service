from uvicorn import run
from .api import app, settings


def main() -> None:
    run(app, host=settings.host, port=settings.port)
