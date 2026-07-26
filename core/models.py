from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    """Represents a single property listing from any provider."""
    id: str                          # unique: provider + slug
    provider: str
    name: str
    location: str
    county: str
    status: str                      # open | closed | coming_soon | unknown
    bedrooms: list[str] = field(default_factory=list)
    price_from: Optional[str] = None
    units_available: Optional[int] = None
    applications_open: Optional[str] = None
    applications_close: Optional[str] = None
    apply_url: Optional[str] = None
    raw_status: Optional[str] = None  # original status text from site

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "Listing":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
