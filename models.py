"""In-memory data model for Cub Scout advancement: Requirement, Adventure, Scout, Den."""

from dataclasses import dataclass, field


@dataclass
class Requirement:
    """A single requirement within an adventure. Source: requirements.json only."""

    id: str  # e.g. "1", "2"
    text: str


@dataclass
class Adventure:
    """An adventure for a rank: name, type, URL, and list of requirements. Source: requirements.json."""

    name: str
    type: str  # "required" | "elective"
    url: str | None
    requirements: list[Requirement]


@dataclass
class Scout:
    """A scout: name, next rank, and finished/pending adventures for that rank."""

    name: str
    next_rank: str
    finished_adventures: list[Adventure] = field(default_factory=list)
    pending_adventures: list[Adventure] = field(default_factory=list)
    # For each pending adventure name, the list of Requirement objects not yet completed (for PDF reports)
    pending_incomplete_requirements: dict[str, list[Requirement]] = field(default_factory=dict)


@dataclass
class Den:
    """A den: name (rank name) and list of scouts whose Next Rank is that rank."""

    name: str
    scouts: list[Scout] = field(default_factory=list)
