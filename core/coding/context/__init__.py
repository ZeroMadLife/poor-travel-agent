"""Context, prompt-budget, and workspace public API."""

from core.coding.context.compact import CompactionPolicy, CompactManager, Summarizer
from core.coding.context.manager import (
    DEFAULT_SYSTEM_PROMPT,
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
    ContextManager,
    SectionRender,
    normalize_text,
    tail_clip,
)
from core.coding.context.projection import ContextLevel, ContextProjector
from core.coding.context.summary import (
    CompactionCheckpoint,
    CompactionResult,
    CompactionSummary,
)
from core.coding.context.workspace import (
    IGNORED_PATH_NAMES,
    WorkspaceContext,
    clip,
    now,
)
from core.coding.context.workspace_diff import (
    MAX_DIFF_FILES,
    MAX_FILE_SIZE,
    FileChange,
    FileSnapshot,
    WorkspaceDiff,
    WorkspaceDiffTracker,
)

__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "IGNORED_PATH_NAMES",
    "MAX_DIFF_FILES",
    "MAX_FILE_SIZE",
    "SYSTEM_PROMPT_DYNAMIC_BOUNDARY",
    "CompactManager",
    "CompactionCheckpoint",
    "CompactionPolicy",
    "CompactionResult",
    "CompactionSummary",
    "ContextLevel",
    "ContextManager",
    "ContextProjector",
    "FileChange",
    "FileSnapshot",
    "SectionRender",
    "Summarizer",
    "WorkspaceContext",
    "WorkspaceDiff",
    "WorkspaceDiffTracker",
    "clip",
    "normalize_text",
    "now",
    "tail_clip",
]
