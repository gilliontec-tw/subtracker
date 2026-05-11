from abc import ABC, abstractmethod
from src.domain.entities.config_option import ConfigOption


class ConfigOptionRepository(ABC):
    @abstractmethod
    def get_by_type(self, type: str) -> list[ConfigOption]: ...

    @abstractmethod
    def get_tree(self, type: str) -> list[ConfigOption]: ...

    @abstractmethod
    def get_by_id(self, option_id: int) -> ConfigOption | None: ...

    @abstractmethod
    def add(self, option: ConfigOption) -> ConfigOption: ...

    @abstractmethod
    def rename(self, option_id: int, new_value: str) -> None: ...

    @abstractmethod
    def delete(self, option_id: int) -> None: ...

    @abstractmethod
    def exists(self, type: str, value: str, parent_id: int | None = None) -> bool: ...
