import logging
import bottle
from datetime import datetime

from .system import current_system
from .types import PropertySet, Property, EnumProperty
from .metadata import register_metadata_schema
from .web import App as MainApp


# WEB
#####


class App:
    BASE = '/publish'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=lambda: bottle.static_file(
                'publish.html', root=MainApp.HTML
            ),
        )

        return app


# DATAMODEL
###########

class ElementType(EnumProperty):
    image = 'image'
    text = 'text'
    heading = 'heading'


class Element(PropertySet):
    type = Property(enum=ElementType, default=ElementType.image)
    src = Property()
    content = Property()
    entry_id = Property()


class Page(PropertySet):
    number = Property(int)
    show = Property(bool, default=True)
    width = Property(int)
    height = Property(int)
    elements = Property(type=Element, is_list=True)


class Publication(PropertySet):
    author = Property()
    publish_ts = Property()
    title = Property()
    comment = Property()
    pages = Property(type=Page, is_list=True)


register_metadata_schema(Publication)
