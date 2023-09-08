#!/usr/bin/env python3
from __future__ import annotations

import logging
import time
from typing import Callable, ClassVar, Self

import pygame

from glitchygames import events
from glitchygames.color import BLACK
from glitchygames.events.mouse import MousePointer
from glitchygames.interfaces import SceneInterface, SpriteInterface

LOG = logging.getLogger('game.scenes')
LOG.addHandler(logging.NullHandler())

class SceneManager(SceneInterface, events.EventManager):
    log: ClassVar = LOG
    OPTIONS: ClassVar = {}

    def __init__(self: Self) -> None:
        super().__init__()

        # Scene manager terminates on self.next_scene = None
        self.screen = pygame.display.get_surface()
        self.update_type = 'update'
        self.fps_refresh_rate = 1000
        self.target_fps = 0
        self.dt = 0
        self.timer = 0
        self._game_engine = None
        self.active_scene = None
        self.next_scene = self.active_scene
        self.previous_scene = self.active_scene
        self.quit_requested = False

        self.clock = pygame.time.Clock()

    @property
    def game_engine(self: Self) -> object:
        return self._game_engine

    @game_engine.setter
    def game_engine(self: Self, new_engine: object) -> None:
        self._game_engine = new_engine
        if self._game_engine:
            self.OPTIONS = self._game_engine.OPTIONS
            self.update_type = self.OPTIONS['update_type']
            self.fps_refresh_rate = self.OPTIONS['fps_refresh_rate']
            self.target_fps = self.OPTIONS.get('target_fps', 60)
            self.log.info(f'Screen update type: {self.update_type}')
            self.log.info(f'FPS Refresh Rate: {self.fps_refresh_rate}')
            self.log.info(f'Target FPS: {self.target_fps}')

    # This enables collided_sprites in sprites.py, since SceneManager is
    # not a scene, but is the entry point for event proxies.
    @property
    def all_sprites(self: Self) -> pygame.sprite.LayeredDirty | None:
        if self.active_scene:
            return self.active_scene.all_sprites

        return None

    def switch_to_scene(self: Self, next_scene: Scene) -> None:
        if next_scene != self.active_scene:
            self.dt = 0
            self.timer = 0
            self.log.info(
                f'Switching to scene "{next_scene}" '
                f'from scene "{self.active_scene}"'
            )

            if self.active_scene:
                self.active_scene._screenshot = self.active_scene.screenshot
                self.log.info(f'Cleaning up active scene {self.active_scene}.')
                self.active_scene.cleanup()

            if next_scene:
                self.log.info(f'Setting up new scene {next_scene}.')
                next_scene.setup()
                self.log.info('Scene event block list: '
                              f'{pygame.event.get_blocked(events.GAME_EVENTS)}')

            self.active_scene = next_scene

            if self.active_scene:
                self.active_scene.dt = self.dt
                self.active_scene.timer = self.timer
                self.active_scene.setup()

                caption = ''

                if self.active_scene.NAME:
                    caption = f'{self.active_scene.NAME}'

                if self.active_scene.VERSION:
                    caption += f' v{self.active_scene.VERSION}'

                pygame.display.set_caption(
                    caption,
                    caption
                )

                self.active_scene.load_resources()

                # Infinite refresh is the default; override it if FPS was configured
                # on the command line, unless the active scene has specific FPS requirements
                if self.target_fps > 0 and self.active_scene.target_fps == 0:
                    self.active_scene.target_fps = self.target_fps

                self.log.info(
                    f'Rendering Scene "{self.active_scene.NAME}({type(self.active_scene)})"'
                    f' at {self.active_scene.target_fps} FPS'
                )

                # This controls how events are marshalled
                self.proxies = [self, self.active_scene]

                # Force a scene redraw
                self.active_scene.dirty = 1

                # Redraw the new scene's background to clear out any artifacts
                self.screen.blit(self.active_scene.background, (0, 0))

                # Per-scene FPS configurability
                self.target_fps = self.active_scene.target_fps

    def start(self: Self) -> None:
        previous_time = time.perf_counter()
        previous_fps_time = previous_time
        current_time = previous_time

        while self.active_scene is not None and self.quit_requested is False:
            self.clock.tick(self.target_fps)

            now = time.perf_counter()
            self.dt = (now - previous_time) * 10
            previous_time = current_time

            self.active_scene.dt_tick(self.dt)

            self.game_engine.process_events()

            self.active_scene.update()

            self.active_scene.render(self.screen)

            if self.update_type == 'update':
                pygame.display.update(self.active_scene.rects)
            elif self.update_type == 'flip':
                pygame.display.flip()

            if (current_time - previous_fps_time) * 1000 >= self.OPTIONS['fps_refresh_rate']:
                pygame.event.post(
                    pygame.event.Event(events.FPSEVENT, {'fps': self.clock.get_fps()})
                )

                previous_fps_time = current_time

            self.switch_to_scene(self.active_scene.next_scene)

            current_time = time.perf_counter()

        self.log.info(f'Game Quitting: Active Scene: {self.active_scene}, '
                      f'Quit Requested: {self.quit_requested}')
        self.terminate()

    def terminate(self: Self) -> None:
        self.switch_to_scene(None)

    def quit_game(self: Self) -> None:
        # put a quit event in the event queue.
        self.log.info('POSTING QUIT EVENT')
        pygame.event.post(
            pygame.event.Event(pygame.QUIT, {})
        )

    def on_quit_event(self: Self, event: pygame.event.Event) -> None:
        # QUIT             none
        self.quit_requested = True

    def on_fps_event(self: Self, event: pygame.event.Event) -> None:
        # FPSEVENT is pygame.USEREVENT + 1
        if self.active_scene:
            self.active_scene.on_fps_event(event)

    def on_game_event(self: Self, event: pygame.event.Event) -> None:
        # GAMEEVENT is pygame.USEREVENT + 2
        # Call the event callback if it's registered.
        try:
            self.game_engine.registered_events[event.subtype](event)
        except KeyError:
            self.log.exception(
                f'Unregistered Event: {event} '
                '(call self.register_game_event(<event subtype>, <event data>))'
            )

    def register_game_event(self: Self, event_type: pygame.event.EventType,
                            callback: Callable) -> None:
        self.game_engine.register_game_event(event_type=event_type, callback=callback)

    # If the game hasn't hooked a call, we should check if the scene manager has.
    #
    # This will allow scenes to get pygame events directly, but we can still
    # hook those events in this engine, or in the subclassed game object, too.
    #
    # This allows maximum flexibility of event processing, with low overhead
    # at the expense of a slight layer violation.
    def __getattr__(self: Self, attr: str) -> Callable:
        # Attempt to proxy the call to the active scene.
        if (attr.startswith('on_') and attr.endswith('_event')):
            try:
                # Pass it to the active scene for handling
                return getattr(self.active_scene, attr)
            except AttributeError:
                # Pass it to the game engine for suppression
                return getattr(self.game_engine, attr)
        else:
            raise AttributeError(f"'{type(self)}' object has no attribute '{attr}'")


class Scene(SceneInterface, SpriteInterface, events.EventInterface):
    """
    Scene object base class.

    Subclass this to properly receive on_*_event() messages automatically.
    """
    log = LOG
    FPS = 0
    NAME = 'Unnamed Scene'
    VERSION = '0.0'

    def __init__(self: Self, options: dict | None = None,
                 groups: pygame.sprite.LayeredDirty | None = None) -> None:
        if options is None:
            options = {}

        if groups is None:
            groups = pygame.sprite.LayeredDirty()

        super().__init__()

        # Since SceneManager is a singleton, this will ensure that
        # any non-active scene which gets initialized will simply
        # get a copy of the scene manager, rather than overwriting
        # the active scene.
        #
        # This helps us keep the upper layers clean by not requiring
        # new scenes to care about the SceneManager when being
        # instantiated.
        self.target_fps = 0
        self.fps = 0
        self.dt = 0
        self.dt_timer = 0
        self.dirty = 1
        self.options = options
        self.scene_manager = SceneManager()
        self.name = type(self)
        self._background_color = None
        self.next_scene = self
        self.rects = None
        self.screen = pygame.display.get_surface()
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()

        # http://n0nick.github.io/blog/2012/06/03/quick-dirty-using-pygames-dirtysprite-layered/
        self.all_sprites = groups

        # Initial screen state.

        self.screen = pygame.display.get_surface()
        self.background = pygame.Surface(self.screen.get_size())
        self.background.convert()
        self.background_color = BLACK

        # This allows us to be treated like a sprite
        self.image = self.screen
        self.rect = self.screen.get_rect()

        self.dirty = 1
        # I don't think this will work since init() is called first.
        # for group in groups:
        #    for sprite in self.all_sprites:
        #        group.add(sprite)

    @property
    def screenshot(self: Self) -> pygame.Surface:
        _screenshot = pygame.Surface((self.screen_width, self.screen_height))
        _screenshot.convert()
        _screenshot.blit(self.screen, (0, 0))
        return _screenshot

    @property
    def background_color(self: Self) -> pygame.Color:
        return self._background_color

    @background_color.setter
    def background_color(self: Self, new_color: tuple) -> None:
        self._background_color = new_color
        self.background.fill(self.background_color)
        self.all_sprites.clear(self.screen, self.background)

    def setup(self: Self) -> None:
        pass

    def cleanup(self: Self) -> None:
        pass

    def dt_tick(self: Self, dt: float) -> None:
        self.dt = dt
        self.dt_timer += self.dt

    def update(self: Self) -> None:
        # Tweak to enable compound sprites to manage their own subsprites dirty states
        #
        # Ideally we'd just make dirty a property with a setter and getter on each
        # sprite object, but that doesn't work for some reason.
        [sprite.update_nested_sprites() for sprite in self.all_sprites]
        [sprite.update() for sprite in self.all_sprites if sprite.dirty]

        # Make all of the new scene's sprites dirty to force a redraw
        if self.dirty:
            for sprite in self.all_sprites:
                sprite.dirty = 1 if not sprite.dirty else sprite.dirty

    def render(self: Self, screen: pygame.Surface) -> None:
        self.rects = self.all_sprites.draw(self.screen)

    def sprites_at_position(self: Self, pos: tuple) -> list[pygame.sprite.Sprite] | None:
        mouse = MousePointer(pos=pos)

        return pygame.sprite.spritecollide(sprite=mouse, group=self.all_sprites, dokill=False)

    def on_mouse_drag_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.debug(f'{type(self)}: Mouse Drag Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_mouse_drag_event(event, trigger)

    def on_mouse_drop_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.debug(f'{type(self)}: Mouse Drop Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_mouse_drop_event(event, trigger)

    def on_left_mouse_drag_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.debug(f'{type(self)}: Left Mouse Drag Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        if collided_sprites:
            collided_sprites[-1].on_left_mouse_drag_event(event, trigger)

        # for sprite in collided_sprites:
        #     sprite.on_left_mouse_drag_event(event, trigger)

    def on_left_mouse_drop_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.debug(f'{type(self)}: Left Mouse Drop Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_left_mouse_drop_event(event, trigger)

    def on_middle_mouse_drag_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.info(f'{type(self)}: Middle Mouse Drag Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_middle_mouse_drag_event(event, trigger)

    def on_middle_mouse_drop_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.info(f'{type(self)}: Middle Mouse Drop Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_middle_mouse_drop_event(event, trigger)

    def on_right_mouse_drag_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.info(f'{type(self)}: Right Mouse Drag Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_right_mouse_drag_event(event, trigger)

    def on_right_mouse_drop_event(self: Self, event: pygame.event.Event, trigger: object) -> None:
        self.log.info(f'{type(self)}: Right Mouse Drop Event: {event} {trigger}')
        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_right_mouse_drop_event(event, trigger)

    def on_left_mouse_button_up_event(self: Self, event: pygame.event.Event) -> None:
        # MOUSEBUTTONUP    pos, button
        self.log.debug(f'{type(self)}: Left Mouse Button Up Event: {event}')

        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_left_mouse_button_up_event(event)

    def on_middle_mouse_button_up_event(self: Self, event: pygame.event.Event) -> None:
        # MOUSEBUTTONUP    pos, button
        self.log.debug(f'{type(self)}: Middle Mouse Button Up Event: {event}')

        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_middle_mouse_button_up_event(event)

    def on_right_mouse_button_up_event(self: Self, event: pygame.event.Event) -> None:
        # MOUSEBUTTONUP    pos, button
        self.log.info(f'{type(self)}: Right Mouse Button Up Event: {event}')

        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_right_mouse_button_up_event(event)

    def on_left_mouse_button_down_event(self: Self, event: pygame.event.Event) -> None:
        # MOUSEBUTTONDOWN  pos, button
        self.log.debug(f'{type(self)}: Left Mouse Button Down Event: {event}')

        collided_sprites = self.sprites_at_position(pos=event.pos)

        self.log.info(f'ENGINE SPRITES: {collided_sprites}')

        # if collided_sprites:
        #     collided_sprites[0].on_left_mouse_button_down_event(event)
        for sprite in collided_sprites:
            sprite.on_left_mouse_button_down_event(event)

    def on_middle_mouse_button_down_event(self: Self, event: pygame.event.Event) -> None:
        # MOUSEBUTTONDOWN    pos, button
        self.log.debug(f'{type(self)}: Middle Mouse Button Down Event: {event}')

        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_middle_mouse_button_down_event(event)

    def on_right_mouse_button_down_event(self: Self, event: pygame.event.Event) -> None:
        # MOUSEBUTTONDOWN  pos, button
        self.log.info(f'{type(self)}: Right Mouse Button Down Event: {event}')

        collided_sprites = self.sprites_at_position(pos=event.pos)

        for sprite in collided_sprites:
            sprite.on_right_mouse_button_down_event(event)

    def on_key_up_event(self: Self, event: pygame.event.Event) -> None:
        # Wire up quit by default for escape and q.
        #
        # If a game implements on_key_up_event themselves
        # they'll have to map their quit keys or call super().on_key_up_event()
        if event.key in (pygame.K_q, pygame.K_ESCAPE):
            self.scene_manager.quit_game()

    def on_quit_event(self: Self, event: pygame.event.Event) -> None:
        # QUIT             none
        self.log.debug(f'{type(self)}: {event}')

    def on_fps_event(self: Self, event: pygame.event.Event) -> None:
        # FPSEVENT is pygame.USEREVENT + 1
        self.log.info(f'Scene "{self.NAME}" ({type(self)}) FPS: {event.fps}')
        self.fps = event.fps

    def load_resources(self: Self) -> None:
        self.log.debug(f'Implement load_resource() in {type(self)}.')
