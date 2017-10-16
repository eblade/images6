#!/usr/bin/env python3

import pyglet
import glooey


class Panel(glooey.ScrollBox):
    custom_alignement = 'center'
    custom_height_hint = 300

    class Frame(glooey.Frame):
        outline = 'green'
        background = 'blue'

        class Box(glooey.Bin):
            costum_horz_padding = 2

    class VBar(glooey.VScrollBar):
        class Decoration(glooey.Background):
            custom_vert_padding = 25


