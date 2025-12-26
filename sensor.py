"""Sensor platform for Merrytek Sensor (placeholder for future expansion)."""
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Merrytek sensors."""
    # Currently no additional sensors implemented
    # This platform is reserved for future expansion (delay, sensitivity readings)
    pass
