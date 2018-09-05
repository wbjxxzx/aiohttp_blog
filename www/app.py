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
logging.basicConfig(level=logging.DEBUG)
from conf.config import configs

import orm
from webframe import add_routes, add_static
from jinja2 import Environment, FileSystemLoader
from urllib import parse
from handlers import cookie2user, COOKIE_NAME

def init_jinja2(app, **kw):
    logging.info('init jinja2 ...')
    options = {
        'autoescape': kw.get('autoescape', True),
        'block_start_string': kw.get('block_start_string', '{%'),
        'block_end_string': kw.get('block_end_string', '%}'),
        'variable_start_string': kw.get('variable_start_string', '{{'),
        'variable_end_string': kw.get('variable_end_string', '}}'),
        'auto_reload': kw.get('auto_reload', True)
    }
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: {}'.format(path))
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env

async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: {} {}'.format(request.method, request.path))
        # await asyncio.sleep(0.3)
        return (await handler(request))
    return logger

async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: {}'.format(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: {}'.format(request.__data__))
        elif request.method == 'GET':
            qs = request.query_string
            request.__data__ = {k: v[0] for k, v in parse.parse_qs(qs, True).items()}
            logging.info('request query: {}'.format(request.__data__))
        return (await handler(request))
    return parse_data

async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp 
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False,
                    default=lambda o:o.__dict__).encode('utf-8')
                )
                resp.content_type = 'application/json;charset=utf-8'
                return resp 
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and (r >= 100 and r < 600):
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

async def auth_factory(app, handler):
    async def auth(request):
        ''' 分析COOKIE, 将登录用户绑定到request对象 '''
        logging.info('check user: {} {}'.format(request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logging.info('set current user: {}'.format(user.email))
                request.__user__ = user 
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (await handler(request))
    return auth

def datetime_filter(t):
    delta = int(time.time())
    if delta < 60:
        return '1min ago'
    if delta < 3600:
        return '{}mins ago'.format(delta // 60)
    if delta < 86400:
        return '{}hours ago'.format(delta // 3600)
    if delta < 86400 * 7:
        return '{}days ago'.format(delta // 86400)
    dt = datetime.fromtimestamp(t)
    return '{}-{}-{}'.format(dt.year, dt.month, dt.day)

async def init(loop):
    # await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='admin', password='123456', db='myblog')
    await orm.create_pool(loop=loop, **configs.db)
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, data_factory, response_factory
    ])
    init_jinja2(app, filters={'datetime': datetime_filter})
    add_routes(app, 'handlers')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 8000)
    logging.info('server started at http://127.0.0.1:8000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()