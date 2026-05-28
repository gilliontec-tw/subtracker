from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    async def send(self, to: list[str], subject: str, body: str) -> None: ...
