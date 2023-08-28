#!/usr/bin/env python3
import logging
from typing import ClassVar

import pygame

from glitchygames.events import FontEvents, ResourceManager

log = logging.getLogger('game.fonts')
log.addHandler(logging.NullHandler())


class FontManager(ResourceManager):
    OPTIONS: ClassVar = {}
    RENDER_CACHE: ClassVar = {}

    class FontProxy(FontEvents, ResourceManager):
        def __init__(self, game=None):
            """
            """
            super().__init__(game=game)
            self.game = game
            self.proxies = [self.game, pygame.freetype]

    def __init__(self, game=None):
        """
        Manage fonts.

        FontManager manages fonts.

        Args:
        ----
        font - The name of the font to use.  Default: pygame.freetype.get_default_font()
        font_size - The size of the font to use. Default: 12
        font_bold - True for bold.  Default: False
        font_italic - True for italic. Default: False
        font_antialias - True for antialiased. Default: False
        font_dpi - Font DPI.  Default: 72

        """
        super().__init__(game=game)

        # Register pygame.freetype
        pygame.freetype.init()
        # pygame.font.init()
        # pygame.ftfont.init()

        log.info('Freetype Font Cache Size: '
                 f'{pygame.freetype.get_cache_size()}')
        log.info('Freetype Font Default Resolution: '
                 f'{pygame.freetype.get_default_resolution()}')

        # Set up the default options.
        FontManager.OPTIONS['font_name'] = game.OPTIONS['font_name']
        FontManager.OPTIONS['font_size'] = game.OPTIONS['font_size']
        FontManager.OPTIONS['font_bold'] = game.OPTIONS['font_bold']
        FontManager.OPTIONS['font_italic'] = game.OPTIONS['font_italic']
        FontManager.OPTIONS['font_antialias'] = game.OPTIONS['font_antialias']
        FontManager.OPTIONS['font_dpi'] = game.OPTIONS['font_dpi']

        pygame.freetype.set_default_resolution(FontManager.OPTIONS['font_dpi'])

        # Ideas:
        #
        # Pre-generate font cache based on settings that are provided.
        # Indexed by the letter they represent.
        # a -> <font name>
        # What about bold, italic, bold + italic, anti-aliased?
        # Maybe we can generate all combinations?
        # Allow caller to pass in a font settings blob and generate.
        # A progress bar class that integrates with tqdm?

        # Ideally, I'd like to support both modes.
        #
        # https://www.pygame.org/docs/ref/font.html
        # To use the pygame.freetypeEnhanced pygame module for loading
        # and rendering computer fonts based pygame.ftfont as pygame.fontpygame
        # module for loading and rendering fonts define the environment variable
        # PYGAME_FREETYPE before the first import of pygamethe top level pygame
        # package. Module pygame.ftfont is a pygame.fontpygame module for loading
        # and rendering fonts compatible module that passes all but one of the font
        # module unit tests: it does not have the UCS-2 limitation of the SDL_ttf
        # based font module, so fails to raise an exception for a code point greater
        # than 'uFFFF'. If pygame.freetypeEnhanced pygame module for loading and
        # rendering computer fonts is unavailable then the SDL_ttf font module
        # will be loaded instead.
        # pygame.ftfont.init()

        # self.proxies = [FontManager.FontProxy(game=game), pygame.freetype]

    @classmethod
    def args(cls, parser):
        group = parser.add_argument_group('Font Options')

        group.add_argument('--font-name',
                           default=pygame.freetype.get_default_font())
        group.add_argument('--font-size',
                           type=int,
                           default=14)
        group.add_argument('--font-bold',
                           action='store_true',
                           default=False)
        group.add_argument('--font-italic',
                           action='store_true',
                           default=False)
        group.add_argument('--font-antialias',
                           action='store_true',
                           default=False)
        group.add_argument('--font-dpi',
                           type=int,
                           default=72)

        return parser

    def font(self, font_config=None):  # noqa: R0201
        if not font_config:
            font_config = FontManager.OPTIONS

        # try:
        log.info(f'Loading Font: {font_config["font_name"]}')
        log.info(f'Font Size: {font_config["font_size"]}')

        try:
            return pygame.freetype.SysFont(name=font_config['font_name'],
                                            size=font_config['font_size'])
        except (TypeError, FileNotFoundError):
            # Note: Not sure why but pygame.freetype.SysFont doesn't
            # seem to work with pyinstaller packaged games.
            log.info('Loading Font: Built-In')

            # BUG: pygame's documentation claims that passing None
            # as the font name will load the default font.  However,
            # this emits an error:
            #
            # File "glitchygames/fonts.py", line 131, in font
            #     return pygame.freetype.SysFont(name=None, size=12)
            #         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # File "pygame/freetype.py", line 78, in SysFont
            # File "pygame/sysfont.py", line 462, in SysFont
            # File "pygame/freetype.py", line 73, in constructor
            # TypeError: not a file object
            return pygame.freetype.SysFont(name=pygame.freetype.get_default_font(), size=12)
