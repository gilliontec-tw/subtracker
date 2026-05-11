from sqlalchemy import case
from sqlalchemy.orm import Session
from src.domain.entities.config_option import ConfigOption
from src.domain.repositories.config_option_repository import ConfigOptionRepository
from src.infrastructure.database.models import ConfigOptionModel


DEFAULT_CATEGORIES = [
    "生產力工具", "開發工具", "資安合規", "設計工具",
    "行銷廣告", "雲端基礎", "財務會計", "HR人資", "其他",
]
DEFAULT_DEPARTMENTS = [
    "總經理室", "管理處", "設備處", "材料處",
]


class SqlConfigOptionRepository(ConfigOptionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: ConfigOptionModel) -> ConfigOption:
        return ConfigOption(
            id=model.id,
            type=model.type,
            value=model.value,
            parent_id=model.parent_id,
        )

    def get_by_type(self, type: str) -> list[ConfigOption]:
        rows = (
            self._session.query(ConfigOptionModel)
            .filter(ConfigOptionModel.type == type)
            .order_by(
                case((ConfigOptionModel.parent_id.is_(None), 0), else_=1),
                ConfigOptionModel.id,
            )
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_tree(self, type: str) -> list[ConfigOption]:
        import copy
        all_opts = [copy.copy(o) for o in self.get_by_type(type)]
        by_id = {o.id: o for o in all_opts}
        roots = []
        for o in all_opts:
            if o.parent_id is None:
                roots.append(o)
            else:
                parent = by_id.get(o.parent_id)
                if parent:
                    parent.children.append(o)
        return roots

    def get_by_id(self, option_id: int) -> ConfigOption | None:
        model = self._session.get(ConfigOptionModel, option_id)
        return self._to_entity(model) if model else None

    def add(self, option: ConfigOption) -> ConfigOption:
        model = ConfigOptionModel(
            type=option.type,
            value=option.value,
            parent_id=option.parent_id,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def rename(self, option_id: int, new_value: str) -> None:
        model = self._session.get(ConfigOptionModel, option_id)
        if model:
            model.value = new_value
            self._session.commit()

    def delete(self, option_id: int) -> None:
        # Delete children first; synchronize_session="fetch" keeps session cache coherent
        self._session.query(ConfigOptionModel).filter(
            ConfigOptionModel.parent_id == option_id
        ).delete(synchronize_session="fetch")
        model = self._session.get(ConfigOptionModel, option_id)
        if model is None:
            return
        self._session.delete(model)
        self._session.commit()

    def exists(self, type: str, value: str, parent_id: int | None = None) -> bool:
        q = self._session.query(ConfigOptionModel).filter(
            ConfigOptionModel.type == type,
            ConfigOptionModel.value == value,
        )
        if parent_id is None:
            q = q.filter(ConfigOptionModel.parent_id.is_(None))
        else:
            q = q.filter(ConfigOptionModel.parent_id == parent_id)
        return q.first() is not None

    def seed_defaults_if_empty(self) -> None:
        for type_, defaults in [("category", DEFAULT_CATEGORIES), ("department", DEFAULT_DEPARTMENTS)]:
            if not self._session.query(ConfigOptionModel).filter(
                ConfigOptionModel.type == type_
            ).first():
                for v in defaults:
                    self._session.add(ConfigOptionModel(type=type_, value=v))
        self._session.commit()
