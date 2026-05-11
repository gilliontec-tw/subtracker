from dataclasses import dataclass, field


@dataclass
class ConfigOption:
    type: str    # "category" | "department"
    value: str
    id: int | None = None
    parent_id: int | None = None
    children: list["ConfigOption"] = field(default_factory=list, compare=False)
