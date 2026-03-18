"""Advanced Vision - Computer Use Capability Layer"""

__version__ = "1.0.0"

# Core schemas
from .schemas import (
    ScreenshotArtifact,
    WindowInfo,
    ActionProposal,
    ActionResult,
    VerificationResult,
)

# WSS Server components
try:
    from .wss_server import (
        WSSServer,
        WSSServerConfig,
        WSSMessage,
        DetectionMessage,
        ClassificationMessage,
        TradingSignalMessage,
        UIUpdateMessage,
        SystemEventMessage,
        PortRouter,
        ConnectionManager,
        create_server,
        get_default_config,
    )
    WSS_AVAILABLE = True
except ImportError:
    WSS_AVAILABLE = False

__all__ = [
    # Schemas
    "ScreenshotArtifact",
    "WindowInfo",
    "ActionProposal",
    "ActionResult",
    "VerificationResult",
]

# Add WSS exports if available
if WSS_AVAILABLE:
    __all__.extend([
        "WSSServer",
        "WSSServerConfig",
        "WSSMessage",
        "DetectionMessage",
        "ClassificationMessage",
        "TradingSignalMessage",
        "UIUpdateMessage",
        "SystemEventMessage",
        "PortRouter",
        "ConnectionManager",
        "create_server",
        "get_default_config",
    ])