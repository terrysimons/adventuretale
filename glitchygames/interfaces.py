"""Interfaces for the game."""
from __future__ import annotations

from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    import pygame

class SpriteInterface:
    """Sprite interface."""

    def update_nested_sprites(self: Self) -> None:
        """Update the nested sprites.

        Args:
            None

        Returns:
            None
        """

    def update(self: Self) -> None:
        """Update the sprite.

        Args:
            None

        Returns:
            None
        """

    def render(self: Self, screen: pygame.Surface) -> None:
        """Render the sprite.

        Args:
            screen (pygame.Surface): The screen to render to.

        Returns:
            None
        """

class SceneInterface:
    """Scene interface."""

    def switch_to_scene(self: Self, next_scene: SceneInterface) -> None:
        """Switch to the next scene.

        Args:
            next_scene (SceneInterface): The next scene.

        Returns:
            None
        """

    def terminate(self: Self) -> None:
        """Terminate the scene.

        Args:
            None

        Returns:
            None
        """
