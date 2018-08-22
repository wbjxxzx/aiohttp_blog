#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
__author__ = wbjxxzx
'''
from aiohttp import web
import asyncio
import os
import json
import time
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)

def index(request):
    return web.Response(body=b'<h1>hello world</h1>')

async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 8000)
    logging.info('server started at http://127.0.0.1:8000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()