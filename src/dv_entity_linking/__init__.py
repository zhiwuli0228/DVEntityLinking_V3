"""Public V4 entity-linking module integration API."""

__version__ = "0.0.0"

from .application.dto import LinkRequestV1, LinkResponseV1
from .module import EntityLinkingModule, ModuleConfig, create_entity_linking_module

__all__ = [
    "EntityLinkingModule",
    "LinkRequestV1",
    "LinkResponseV1",
    "ModuleConfig",
    "create_entity_linking_module",
    "__version__",
]
