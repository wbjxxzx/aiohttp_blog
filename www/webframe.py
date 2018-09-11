#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
__author__ = wbjxxzx
'''

import asyncio
import os
import inspect
import functools
from urllib import parse
from aiohttp import web
from apis import APIError
from mylogger import logger

def get(path):
    """
    define decorator @get('/path')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    """
    define decorator @post('/path')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

def get_required_kw_args(fn):
    ''' 将所有无默认值的命名关键字参数作为一个tuple 返回 '''
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and \
            param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    ''' 将所有的命名关键字参数作为一个tuple 返回 '''
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    ''' 检查是否有命名关键字参数 '''
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    ''' 检查是否有关键字参数集 '''
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    '''
    检查函数是否有 request 参数，若有，判断是否为最后一个参数
    '''
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        # 找到 'request' 后，还出现位置参数，则抛出异常
        if found and(
            param.kind != inspect.Parameter.VAR_POSITIONAL and
            param.kind != inspect.Parameter.KEYWORD_ONLY and
            param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: {}{}'.format(
                fn.__name__, str(sig)
            ))
    return found

class RequestHandler(object):
    ''' 封闭url处理函数 '''
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None
        # 当传入的处理函数具有 关键字参数集 或 命名关键字参数 或 request参数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('missing content-type')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object')
                    kw = params
                elif ct.startswith(('application/x-www-form-urlencoded', 'multipart/form-data')):
                    # 处理表单类型的数据，传入参数字典中
                    params = await request.post()
                    kw = dict(**params)
                else:
                    # 暂不支持处理其他正文类型的数据
                    return web.HTTPBadRequest('unsupported content-type: {}'.format(request.content_type))
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    # 获取URL中的请求参数，如 id=1
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw:
                copy = {}
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logger.warning('duplicat arg name in named arg and kw args: {}'.format(k))
                    kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            # 收集无默认值的关键字参数
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('missing argument: {}'.format(name))
        logger.warning('call with args: {}'.format(kw))
        try:
            # 最后调用处理函数，并传入请求参数，进行请求处理
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
    ''' 添加静态资源路径 '''
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logger.info('add static {}=>{}'.format('/static/', path))

def add_route(app, fn):
    ''' 注册处理函数到web服务器的路由 '''
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in {}'.format(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logger.info('add route {} {}=>{}({})'.format(method, path, fn.__name__, 
        ', '.join(inspect.signature(fn).parameters.keys()))
    )
    app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
    ''' 自动注册符合条件的函数 '''
    logger.debug('add url handlers {}...'.format(module_name))
    n = module_name.rfind('.')
    if n == -1:
        mod = __import__(module_name, globals(), locals())
    else:
        # 模块名，如 os.path 中的 path
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        # 模块所有属性，忽略私有
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                # 已经处理过的url函数注册到web服务器
                logger.debug('find handler function: {}'.format(fn))
                add_route(app, fn)