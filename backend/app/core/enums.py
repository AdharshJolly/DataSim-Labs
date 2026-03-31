from enum import Enum


class DatasetStatus(str, Enum):
    draft = "draft"
    active = "active"
    generating = "generating"
    archived = "archived"


class DataType(str, Enum):
    integer = "integer"
    float = "float"
    categorical = "categorical"
    boolean = "boolean"
    date = "date"
    text = "text"
    email = "email"
    name = "name"
    address = "address"


class DistributionType(str, Enum):
    uniform = "uniform"
    normal = "normal"
    skewed = "skewed"
    weighted_categorical = "weighted_categorical"
