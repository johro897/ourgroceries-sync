"""Todo platform for OurGroceries Sync — one TodoListEntity per shopping list."""
import asyncio
import logging
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DELETE_CONCURRENCY, DOMAIN
from .coordinator import OurGroceriesCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one todo entity per OurGroceries shopping list."""
    coordinator: OurGroceriesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OurGroceriesTodoListEntity(coordinator, sl["id"], sl["name"])
        for sl in coordinator.lists
    )


def _completion_status(item: dict[str, Any]) -> TodoItemStatus:
    """Map an OurGroceries item to a TodoItemStatus."""
    return TodoItemStatus.COMPLETED if item.get("crossedOffAt") else TodoItemStatus.NEEDS_ACTION


class OurGroceriesTodoListEntity(CoordinatorEntity[OurGroceriesCoordinator], TodoListEntity):
    """A single OurGroceries shopping list, exposed as a todo.* entity."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator: OurGroceriesCoordinator, list_id: str, list_name: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._list_id = list_id
        self._attr_unique_id = list_id
        self._attr_name = list_name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data.get(self._list_id)
        self._attr_todo_items = (
            None
            if data is None
            else [
                TodoItem(
                    summary=i["name"],
                    uid=i["id"],
                    status=_completion_status(i),
                    # OurGroceries' own "note" surfaced via HA's standard
                    # description field — read-only for now, see CLAUDE.md
                    # ("Notes — read-only for now") for why this doesn't
                    # declare SET_DESCRIPTION_ON_ITEM.
                    description=i.get("note") or None,
                )
                for i in data["list"]["items"]
            ]
        )
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Update state from existing coordinator data once added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a todo item."""
        if item.status != TodoItemStatus.NEEDS_ACTION:
            raise ValueError("Only active tasks may be created.")
        await self.coordinator.og.add_item_to_list(self._list_id, item.summary, auto_category=True)
        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a todo item."""
        # HA's todo.update_item always passes the item's existing summary, even
        # for a status-only change, so rename only when the name actually
        # differs — otherwise every check-off sends a no-op rename first.
        items = self.coordinator.data[self._list_id]["list"]["items"]
        current = next(i for i in items if i["id"] == item.uid)
        if item.summary and item.summary != current["name"]:
            await self.coordinator.og.change_item_on_list(
                self._list_id, item.uid, current.get("categoryId"), item.summary
            )
        if item.status is not None:
            await self.coordinator.og.toggle_item_crossed_off(
                self._list_id, item.uid, cross_off=item.status == TodoItemStatus.COMPLETED
            )
        await self.coordinator.async_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items, bounding concurrency to avoid OurGroceries' 429 cap.

        See home-assistant/core#179603 — core's unbounded asyncio.gather over
        every uid floods OurGroceries' servers and silently drops deletions
        past their 15-req/user cap. Bound concurrency instead.
        """
        semaphore = asyncio.Semaphore(DELETE_CONCURRENCY)

        async def _delete_one(uid: str) -> None:
            async with semaphore:
                await self.coordinator.og.remove_item_from_list(self._list_id, uid)

        await asyncio.gather(*(_delete_one(uid) for uid in uids))
        await self.coordinator.async_refresh()
