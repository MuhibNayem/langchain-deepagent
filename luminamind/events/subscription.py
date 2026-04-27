from luminamind.events.schema import EventSubscription, AgentEventType, AgentEvent


class SubscriptionManager:
    """Manages event subscriptions and filtering."""

    def __init__(self):
        self._subscriptions: dict[str, EventSubscription] = {}
        self._counter = 0

    def create(self, subscription: EventSubscription) -> str:
        """Create new subscription. Returns subscription_id."""
        self._counter += 1
        subscription_id = f"sub_{self._counter}"
        self._subscriptions[subscription_id] = subscription
        return subscription_id

    def get(self, subscription_id: str) -> EventSubscription | None:
        """Get subscription by ID."""
        return self._subscriptions.get(subscription_id)

    def delete(self, subscription_id: str) -> bool:
        """Delete subscription."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False

    def matches(self, subscription_id: str, event: AgentEvent) -> bool:
        """Check if event matches subscription filter."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return False
        if subscription.session_id and event.session_id != subscription.session_id:
            return False
        if subscription.task_id and event.task_id != subscription.task_id:
            return False
        if subscription.agent_id and event.agent_id != subscription.agent_id:
            return False
        if subscription.event_types and event.event_type not in subscription.event_types:
            return False
        return True

    def list_active(self) -> list[str]:
        """List all active subscription IDs."""
        return list(self._subscriptions.keys())