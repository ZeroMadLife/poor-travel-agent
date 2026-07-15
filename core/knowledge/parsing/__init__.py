"""Parser Registry and stable parsed-document contracts."""

from .markdown import MarkdownParser
from .registry import (
    DocumentParser,
    ParserConflictError,
    ParserNotFoundError,
    ParserRegistry,
)
from .serialization import deserialize_document, serialize_document
from .types import (
    BlockKind,
    ParseArtifact,
    ParsedBlock,
    ParsedDocument,
    ParseProvenance,
    ParseRequest,
)


def default_parser_registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register(MarkdownParser())
    return registry


__all__ = [
    "BlockKind",
    "DocumentParser",
    "MarkdownParser",
    "ParseArtifact",
    "ParseProvenance",
    "ParseRequest",
    "ParsedBlock",
    "ParsedDocument",
    "ParserConflictError",
    "ParserNotFoundError",
    "ParserRegistry",
    "default_parser_registry",
    "deserialize_document",
    "serialize_document",
]
