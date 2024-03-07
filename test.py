#!/usr/bin/env python3
from typing import List

import models
from tortoise import Tortoise

from nicegui import app, ui


async def init_db() -> None:
    await Tortoise.init(db_url='sqlite://stock_trading_records.db', modules={'models': ['models']})
    await Tortoise.generate_schemas()


async def close_db() -> None:
    await Tortoise.close_connections()

app.on_startup(init_db)
app.on_shutdown(close_db)


@ui.refreshable
async def list_of_users() -> None:
    async def delete(record: models.stock_trading_record) -> None:
        await record.delete()
        list_of_users.refresh()

    records: List[models.stock_trading_record] = await models.stock_trading_record.all()
    for record in reversed(records):
        with ui.card():
            with ui.row().classes('items-center'):
                ui.input('Code', on_change=record.save) \
                    .bind_value(record, 'code').on('blur', list_of_users.refresh)
                ui.number('Price', on_change=record.save, format='%.0f') \
                    .bind_value(record, 'price').on('blur', list_of_users.refresh).classes('w-20')
                ui.button(icon='delete', on_click=lambda u=record: delete(u)).props('flat')


@ui.page('/')
async def index():
    async def create() -> None:
        await models.stock_trading_record.create(name=name.value, age=age.value or 0)
        name.value = ''
        age.value = None
        list_of_users.refresh()

    with ui.column().classes('mx-auto'):
        with ui.row().classes('w-full items-center px-4'):
            name = ui.input(label='Name')
            age = ui.number(label='Age', format='%.0f').classes('w-20')
            ui.button(on_click=create, icon='add').props('flat').classes('ml-auto')
        await list_of_users()

ui.run()