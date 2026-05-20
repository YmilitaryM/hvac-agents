from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProtocolBinding:
    protocol: str
    config: dict


class ProtocolAdapter(ABC):
    protocol: str

    @abstractmethod
    async def connect(self, binding: ProtocolBinding) -> None: ...

    @abstractmethod
    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float: ...

    @abstractmethod
    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...


class AdapterError(Exception):
    pass


class CommunicationError(AdapterError):
    pass


class WriteError(AdapterError):
    pass
