import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator, UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: Any) -> str:
        return f"vector({self.dimensions})"


@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_: Vector, compiler, **kw) -> str:
    return "TEXT"


@compiles(Vector, "postgresql")
def compile_vector_postgresql(type_: Vector, compiler, **kw) -> str:
    return f"vector({type_.dimensions})"


class VectorString(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return "[" + ",".join(f"{float(item):.8f}" for item in value) + "]"

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return [float(item) for item in value]
        if isinstance(value, str):
            if value.startswith("["):
                return [float(item) for item in value.strip("[]").split(",") if item]
            return [float(item) for item in json.loads(value)]
        return value
