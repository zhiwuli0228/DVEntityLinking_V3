"""DV entity linking demo package."""

__version__ = "0.0.0"

from .service import EntityLinkingService
from .llm import LLMConfig, OpenAICompatibleLLMClient

__all__ = [
    "EntityLinkingService",
    "LLMConfig",
    "OpenAICompatibleLLMClient",
    "__version__",
]
