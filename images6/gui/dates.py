#!/usr/bin/env python3

import pyglet
import glooey

from ..date import get_dates


class DateButton(glooey.Button):
    custom_alignment = "left"

    def __init__(self, date):
        super().__init__(f"{date.date} - {date.short}")
        self.date = date


class DateList(glooey.VBox):
    def add(self, widget):
        super().add(widget)
        widget.push_handlers(on_click=self.on_clicked_date)

    def on_clicked_date(self, sender):
        self.dispatch_event('on_select_date', sender.date.date)


DateList.register_event_type('on_select_date')


def create_date_list():
    date_list = DateList()

    for date in get_dates().entries:
        date_widget = DateButton(date)
        date_list.add(date_widget)

    return date_list
