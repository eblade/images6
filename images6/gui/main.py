#!/usr/bin/env python3

import pyglet

#import pudb
#pu.db

class TextWidget(object):
    def __init__(self, text, x, y, width, batch):
        self.document = pyglet.text.document.UnformattedDocument(text)
        self.document.set_style(0, len(text),
            dict(color=(0, 0, 0, 255))
        )
        font = self.document.get_font()
        self.height = font.ascent - font.descent

        self.layout = pyglet.text.layout.IncrementalTextLayout(
            self.document, width, self.height, multiline=False, batch=batch)

        self.caret = pyglet.text.caret.Caret(self.layout)

        self.layout.x = x
        self.layout.y = y

    @property
    def value(self):
        return self.document.text

    def reset(self):
        self.document.text = ''

    def hit_test(self, x, y):
        return (0 < x - self.layout.x < self.layout.width and
                0 < y - self.layout.y < self.layout.height)


class StandardOutput:
    def __init__(self, context, text):
        self.document = pyglet.text.decode_attributed(text)
        self.layout = pyglet.text.layout.TextLayout(self.document,
            context.width - 20, None, multiline=True, wrap_lines=True)
        self.layout.x = 10
        self.layout.anchor_y = 'bottom'

    @property
    def height(self):
        return self.layout.content_height

    @property
    def y(self):
        return self.layout.y

    @y.setter
    def y(self, y):
        self.layout.y = y

    def draw(self):
        self.layout.draw()


class ErrorOutput(StandardOutput):
    def __init__(self, context, text, *args, **kwargs):
        super().__init__(context, "{color (255, 0, 0, 255)}" + text, *args, **kwargs)


class ImageOutput:
    def __init__(self, context, path):
        self.image = pyglet.image.load(path)
        self.sprite = pyglet.sprite.Sprite(self.image)
        actual_width = self.image.width
        wanted_width = context.width - 20
        self.sprite.scale = wanted_width / actual_width
        self.sprite.x = 10

    @property
    def height(self):
        return self.sprite.height

    @property
    def y(self):
        return self.sprite.y

    @y.setter
    def y(self, y):
        self.sprite.y = y

    def draw(self):
        self.sprite.draw()


class ImageViewerOverlay:
    def __init__(self, context, place, start_index=0):
        self.context = context
        self.place = place
        self.index = start_index
        self.batch = None
        self.sprite = None
        self.hires = False
        self.load()

    def get_path(self, entry):
        if self.hires:
            purposes = Purpose.original, Purpose.derivative, Purpose.proxy
        else:
            purposes = Purpose.proxy,

        for purpose in purposes:
            variant = entry.get_variant(purpose)
            if variant is not None:
                return os.path.join(
                    current_system().media_root,
                    variant.get_filename(entry.id))

    def load(self):
        self.batch = pyglet.graphics.Batch()
        entry = self.place.get(self.index)
        self.load_info(entry)
        self.load_image(entry)

    def load_info(self, entry):
        self.info_batch = pyglet.graphics.Batch()
        text = f"#{self.index} {entry.taken_ts} {{bold True}}{entry.state.value.upper()}{{bold False}}"
        tags = ', '.join(entry.tags)
        text += " {color (0, 50, 150, 255)}" + tags
        self.document = pyglet.text.decode_attributed(text)
        self.layout = pyglet.text.layout.TextLayout(self.document,
            self.context.width, batch=self.info_batch)
        self.layout.x = 0
        self.layout.anchor_y = 'bottom'

    def load_image(self, entry):
        path = self.get_path(entry)
        if path is None:
            self.sprite = None
            return

        image = pyglet.image.load(path)

        sprite = pyglet.sprite.Sprite(image, batch=self.batch)
        actual_width = image.width
        wanted_width = self.context.width - 20
        actual_height = image.height
        wanted_height = self.context.height - 30

        actual_ratio = actual_width / actual_height
        wanted_ratio = wanted_width / wanted_height

        if actual_ratio >= wanted_ratio:
            sprite.scale = wanted_width / actual_width
            sprite.x = 10
            sprite.y = 20 + wanted_height / 2 - (actual_height * sprite.scale) / 2
        else:
            sprite.scale = wanted_height / actual_height
            sprite.x = 10 + wanted_width / 2 - (actual_width * sprite.scale) / 2
            sprite.y = 20

        self.sprite = sprite

    def draw(self):
        if self.batch is not None:
            self.batch.draw()
        if self.info_batch is not None:
            self.info_batch.draw()

    def update(self, update):
        entry = self.place.get(self.index)
        update(entry) 
        self.place.set(self.index, update_entry_by_id(entry.id, entry))
        self.load_info(entry)

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.LEFT:
            self.index -= 1
            if self.index < 0:
                self.index = 0
            self.load()

        elif symbol == pyglet.window.key.RIGHT:
            self.index += 1
            if self.index >= len(self.place.entries):
                self.index = len(self.place.entries) - 1
            self.load()

        elif symbol == pyglet.window.key.H:
            self.hires = not self.hires

        elif symbol == pyglet.window.key.Q:
            def set_state(entry): entry.state = State.keep
            self.update(set_state)

        elif symbol == pyglet.window.key.W:
            def set_state(entry): entry.state = State.purge
            self.update(set_state)

        elif symbol == pyglet.window.key.A:
            def set_state(entry): entry.state = State.todo
            self.update(set_state)

        elif symbol == pyglet.window.key.S:
            def set_state(entry): entry.state = State.wip
            self.update(set_state)

        elif symbol == pyglet.window.key.Z:
            def set_state(entry): entry.state = State.final
            self.update(set_state)

        elif symbol == pyglet.window.key.ESCAPE:
            self.context.close_overlay()


import shlex
import io
import os
import sys
import traceback
from ..system import current_system
from ..date import get_dates, get_date
from ..entry import get_entries, get_entry_by_id, update_entry_by_id, EntryQuery, Purpose, State
from ..tag import get_tags
from .router import Router, Route


class Parser:
    def __init__(self):
        self._commands = {}

    def add_commands(self, commands):
        for command in commands:
            self._commands[command.__name__] = command

    def dispatch(self, args, context):
        command_name = args.pop(0)
        command = self._commands[command_name]
        pargs = [context]
        kwargs = {}
        while args:
            arg = args.pop(0)
            if arg.startswith("--"):
                value = args.pop(0)
                kwargs[arg[2:]] = value
            else:
                pargs.append(arg)
        return command(*pargs, **kwargs)


class Interpreter:
    def __init__(self):
        self._router = Router()
        self._parser = Parser()
        self._parser.add_commands([
            self.exit, self.help,
            self.cd, self.pwd, self.ls,
            self.info, self.cat, self.view,
            self.cache
        ])
        self.location = ''

    def place(self, path=None, callback=None):
        decorator = self._router.make_route_decorator(path)
        return decorator(callback) if callback else decorator

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, path):
        if path == '':
            self._location = ''
            self._place = None
            return
        route, args = self._router.match(path)
        self._place = route.call(**args)
        self._location = path

    def do(self, command, context):
        argv = shlex.split(command)
        try:
            for output in self._parser.dispatch(argv, context):
                yield output
        except Exception as e:
            traceback.print_exc()
            yield ErrorOutput(context, "BAD INPUT " + str(e))

    def exit(self, context):
        current_system().close()
        yield None
        pyglet.app.exit()

    def help(self, context):
        pass

    def cd(self, context, path):
        if path.startswith('/'):
            self.location = os.path.normpath(path)
        else:
            self.location = os.path.normpath(os.path.join(self.location, path))
        for output in self.pwd(context):
            yield output

    def pwd(self, context):
        yield StandardOutput(context, ' Current: {bold True}' + self.location + ' {bold False}{italic True}' + str(self._place))

    def ls(self, context):
        if self._place is None:
            yield ErrorOutput(context, 'You are nowhere.')
        elif hasattr(self._place, 'ls'):
            for output in  self._place.ls(context):
                yield output
        else:
            yield ErrorOutput(context, f'The place {self._place} does not support ls.')

    def info(self, context):
        if self._place is None:
            yield ErrorOutput(context, 'You are nowhere.')
        elif hasattr(self._place, 'info'):
            for output in self._place.info(context):
                yield output
        else:
            yield ErrorOutput(context, f'The place {self._place} does not support info.')

    def cat(self, context, subpath):
        if self._place is None:
            yield ErrorOutput(context, 'You are nowhere.')
        elif hasattr(self._place, 'cat'):
            for output in self._place.cat(context, subpath):
                yield output
        else:
            yield ErrorOutput(context, f'The place {self._place} does not support cat.')


    def view(self, context):
        if self._place is None:
            yield ErrorOutput(context, 'You are nowhere.')
        elif hasattr(self._place, 'view'):
            for output in self._place.view(context):
                yield output
        else:
            yield ErrorOutput(context, f'The place {self._place} does not support view.')

    def cache(self, context, command):
        system = current_system()
        if command == 'clear':
            for db in system.db.values():
                db.clear_cache()
            yield StandardOutput(context, 'OK.')
        elif command == 'index':
            for db in system.db.values():
                db.reindex()
            yield StandardOutput(context, 'OK.')
        else:
            yield ErrorOutput(context, f'The command cache should be followed by clear or index')

class Window(pyglet.window.Window):
    def __init__(self, *args, interpreter=None, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.interpreter = interpreter

        self.batch = pyglet.graphics.Batch()
        self.command_line = TextWidget('', 10, 10, self.width - 20, self.batch)

        self.text_cursor = self.get_system_mouse_cursor('text')

        self.outputs = []
        self.overlay = None

        self.focus = None
        self.set_focus(self.command_line)

    def repack(self):
        y = self.command_line.height + 20
        for output in reversed(self.outputs):
            output.y = y
            y += output.height + 10

    def close_overlay(self):
        self.overlay = None
        self.set_focus(self.command_line)

    def on_resize(self, width, height):
        super(Window, self).on_resize(width, height)
        self.command_line.width = width - 20

    def on_draw(self):
        pyglet.gl.glClearColor(1, 1, 1, 1)
        self.clear()
        self.batch.draw()
        if self.overlay is not None:
            self.overlay.draw()
        else:
            for output in self.outputs:
                output.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.command_line.hit_test(x, y):
            self.set_mouse_cursor(self.text_cursor)
        else:
            self.set_mouse_cursor(None)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.command_line.hit_test(x, y):
            self.set_focus(self.command_line)
        else:
            self.set_focus(None)

        if self.focus and hasattr(self.focus, 'caret'):
            self.focus.caret.on_mouse_press(x, y, button, modifiers)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.focus and hasattr(self.focus, 'caret'):
            self.focus.caret.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_text(self, text):
        if self.focus and hasattr(self.focus, 'caret'):
            if not self.focus.layout.multiline and text == '\r':
                return
            self.focus.caret.on_text(text)

    def on_text_motion(self, motion):
        if self.focus and hasattr(self.focus, 'caret'):
            self.focus.caret.on_text_motion(motion)

    def on_text_motion_select(self, motion):
        if self.focus and hasattr(self.focus, 'caret'):
            self.focus.caret.on_text_motion_select(motion)

    def on_key_press(self, symbol, modifiers):
        if hasattr(self.focus, 'on_key_press'):
            return self.focus.on_key_press(symbol, modifiers)

        if symbol == pyglet.window.key.TAB:
            pass

        elif symbol == pyglet.window.key.RETURN:
            command = self.focus.value
            self.focus.reset()
            for output in self.interpreter.do(command, self):
                if output is None:
                    continue
                if output.__class__.__name__.endswith("Overlay"):
                    self.overlay = output
                    self.set_focus(self.overlay)
                else:
                    self.outputs.append(output)
            self.repack()
            return pyglet.event.EVENT_HANDLED

    def set_focus(self, focus):
        if self.focus and hasattr(self.focus, 'caret'):
            self.focus.caret.visible = False
            self.focus.caret.mark = self.focus.caret.position = 0

        self.focus = focus
        if self.focus and hasattr(self.focus, 'caret'):
            self.focus.caret.visible = True
            self.focus.caret.mark = 0
            self.focus.caret.position = len(self.focus.document.text)


interpreter = Interpreter()

@interpreter.place('/')
class RootPlace:
    def __str__(self): return "Root"

    def ls(self, context):
        yield StandardOutput(context, ' dates\n tags')


@interpreter.place('/dates')
class DatesPlace:
    def __str__(self): return "Dates"

    def ls(self, context):
        output = ''
        for date in get_dates().entries:
            output +=  f'\n {{bold True}}{date.date}{{bold False}} {date.short}'
        yield StandardOutput(context, output)


@interpreter.place('/tags')
class TagsPlace:
    def __str__(self): return "Tags"

    def ls(self, context):
        output = ''
        for tag in get_tags().entries:
            output += f' {{bold True}}{tag.tag}{{bold False}} {tag.count}\n'
        yield StandardOutput(context, output)


@interpreter.place('/dates/<date>')
class DatePlace:
    def __str__(self): return f"Date {self._date}"

    def __init__(self, date):
        self._date = date
        self._entries = None

    @property
    def entries(self):
        if self._entries is None:
            self._entries = get_entries(EntryQuery(date=self._date)).entries
        return self._entries

    def get(self, index):
        return self.entries[index]

    def set(self, index, entry):
        self.entries[index] = entry

    def ls(self, context):
        output = ''
        for entry in self.entries:
            title = entry.title or ''
            tags = ', '.join(entry.tags)
            output += f' {{bold True}}{entry.id}{{bold False}} [{entry.original_filename}] {{italic True}}{title} {tags}\n'
        yield StandardOutput(context, output)

    def info(self, context):
        date = get_date(self._date)
        title = f' {{bold True}}{date.date}{{bold False}} {date.short}\n'
        descr = f' {{italic True}}{date.full}{{italic False}}\n'
        new = f' New = {date.stats.new}\n'
        keep = f' Keep = {date.stats.keep}\n'
        purge = f' Purge = {date.stats.purge}\n'
        todo = f' Todo = {date.stats.todo}\n'
        wip = f' WIP = {date.stats.wip}\n'
        final = f' Final = {date.stats.final}'
        yield StandardOutput(context, title + descr + new + keep + purge + todo + wip + final)

    def cat(self, context, subpath):
        if subpath == '.':
            for output in self.info(context):
                yield output
        else:
            entry = get_entry_by_id(subpath)
            path = os.path.join(
                current_system().media_root,
                entry.get_filename(Purpose.proxy))
            yield ImageOutput(context, path)

    def view(self, context):
        yield ImageViewerOverlay(context, self, 0)


interpreter.location = '/dates/2017-09-17'


window = Window(800, 600, resizable=True, caption="IMAGES", interpreter=interpreter)
window.set_minimum_size(320, 200)

#window.push_handlers(pyglet.window.event.WindowEventLogger())
pyglet.app.run()
