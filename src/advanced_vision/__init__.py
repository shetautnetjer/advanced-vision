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

# Schema Registry
from .core import SchemaRegistry, get_registry, get_cached_schema

# WSS v2 is the public default for this release.
try:
    from .wss_server_v2 import (
        ConnectionManagerV2,
        Topic,
        SchemaFamily,
        WSSLoggerV2,
        WSSServerV2,
        WSSServerConfigV2,
        TransportEnvelope,
        TopicRouter,
        create_server_v2,
        get_default_config_v2,
    )
    from .wss_client_v2 import (
        ClientConfigV2,
        WSSClientV2,
        WSSPublisherV2,
        WSSSubscriberV2,
        create_publisher_v2,
        create_subscriber_v2,
    )

    # Backward-compatible API aliases for v1-style names
    WSSServerConfigV2 = WSSServerConfigV2
    WSSServer = WSSServerV2
    WSSServerConfig = WSSServerConfigV2
    WSSMessage = TransportEnvelope
    DetectionMessage = TransportEnvelope
    ClassificationMessage = TransportEnvelope
    TradingSignalMessage = TransportEnvelope
    UIUpdateMessage = TransportEnvelope
    SystemEventMessage = TransportEnvelope
    PortRouter = TopicRouter
    ConnectionManager = ConnectionManagerV2
    WSSLogger = WSSLoggerV2
    WSSClient = WSSClientV2
    WSSPublisher = WSSPublisherV2
    WSSSubscriber = WSSSubscriberV2
    ClientConfig = ClientConfigV2
    create_publisher = create_publisher_v2
    create_subscriber = create_subscriber_v2
    create_server = create_server_v2
    get_default_config = get_default_config_v2
    WSS_AVAILABLE = True
except ImportError:
    WSS_AVAILABLE = False
    try:
        from .wss_server import (  # type: ignore
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
        from .wss_client import (
            WSSClient,
            WSSPublisher,
            WSSSubscriber,
            create_publisher,
            create_subscriber,
        )
        WSS_AVAILABLE = True
    except Exception:
        WSS_AVAILABLE = False

__all__ = [
    # Schemas
    "ScreenshotArtifact",
    "WindowInfo",
    "ActionProposal",
    "ActionResult",
    "VerificationResult",
    # Schema Registry
    "SchemaRegistry",
    "get_registry",
    "get_cached_schema",
]

# Add WSS exports if available
if WSS_AVAILABLE:
    __all__.extend([
        "WSSServerV2",
        "WSSServerConfigV2",
        "WSSLoggerV2",
        "TransportEnvelope",
        "SchemaFamily",
        "Topic",
        "TopicRouter",
        "WSSClientV2",
        "WSSPublisherV2",
        "WSSSubscriberV2",
        "ClientConfigV2",
        "create_server_v2",
        "get_default_config_v2",
        "create_publisher_v2",
        "create_subscriber_v2",
        "WSSServer",
        "WSSServerConfig",
        "WSSMessage",
        "DetectionMessage",
        "ClassificationMessage",
        "TradingSignalMessage",
        "UIUpdateMessage",
        "SystemEventMessage",
        "WSSClient",
        "WSSPublisher",
        "WSSSubscriber",
        "ClientConfig",
        "PortRouter",
        "ConnectionManager",
        "WSSLogger",
        "SchemaFamily",
        "Topic",
        "TopicRouter",
        "create_server",
        "get_default_config",
        "create_publisher",
        "create_subscriber",
    ])
