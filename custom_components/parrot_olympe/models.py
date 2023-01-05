"""The Parrot Olympe integration models."""

from __future__ import annotations

from dataclasses import dataclass

import olympe

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


@dataclass
class ParrotOlympeData:
    """Data for the Parrot Olympe integration."""

    title: str
    device: olympe
    coordinator: DataUpdateCoordinator
