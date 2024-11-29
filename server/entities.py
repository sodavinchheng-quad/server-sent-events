from enum import Enum
from typing import Callable
import asyncio


class TableStatus(Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"


class Table:
    def __init__(self, table_no: int):
        self.table_no = table_no
        self.status = TableStatus.AVAILABLE

    def update_status(self, status: TableStatus):
        self.status = self._get_table_staus_from_str(status)

    def _get_table_staus_from_str(self, status: str) -> TableStatus:
        if status == "available":
            return TableStatus.AVAILABLE
        elif status == "reserved":
            return TableStatus.RESERVED
        elif status == "occupied":
            return TableStatus.OCCUPIED
        else:
            raise ValueError("Invalid table status")

    def to_dict(self):
        return {
            "table_no": self.table_no,
            "status": self.status.value,
        }

    def __dict__(self):
        return self.to_dict()


class Store:
    def __init__(self, store_id: int, store_name: str):
        self.store_id = store_id
        self.store_name = store_name
        self.tables = {
            i: Table(i) for i in range(1, 51)
        }

    def to_dict(self):
        return {
            "id": self.store_id,
            "name": self.store_name,
        }

    def __dict__(self):
        return self.to_dict()


class Client:
    def __init__(self, store: Store):
        self.store = store
        self.queue = asyncio.Queue()
        self.task = None

    async def listen(self, on_cancel: Callable):
        try:
            while True:
                message = await self.queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            on_cancel()
            self.cancel()

    async def send(self, message: str):
        await self.queue.put(message)

    def set_task(self, task: asyncio.Task):
        if self.task is not None:
            self.task.cancel()
        self.task = task

    def cancel(self):
        if self.task:
            self.task.cancel()
            self.task = None
