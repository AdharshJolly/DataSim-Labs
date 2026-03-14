from redis import Redis
from rq import Connection, Worker

from app.core.config import settings


def run_worker() -> None:
    """Run an RQ worker for dataset generation jobs."""
    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker(["dataset_generation"])
        worker.work()


if __name__ == "__main__":
    run_worker()
