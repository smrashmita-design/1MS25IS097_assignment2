"""Tests for the shared dependency wiring.

These guard an important invariant: the agent controller and the API routes
must operate on the *same* conversation store, otherwise a conversation created
through the API would be invisible to the agent.
"""

from __future__ import annotations

from app.api import deps
from app.config import Settings
from app.services.conversation_store import build_conversation_store


class TestSharedDependencies:
    def test_controller_and_api_share_one_store(self, settings: Settings) -> None:
        deps.reset_dependencies()
        controller = deps.get_controller()
        store = deps.get_store()
        assert controller.store is store

    def test_store_is_memoised_per_location(self, settings: Settings) -> None:
        deps.reset_dependencies()
        assert build_conversation_store(settings) is build_conversation_store(settings)

    def test_reset_dependencies_rebuilds_the_controller(self, settings: Settings) -> None:
        deps.reset_dependencies()
        first = deps.get_controller()
        deps.reset_dependencies()
        second = deps.get_controller()
        assert first is not second
        assert first.store is not second.store
