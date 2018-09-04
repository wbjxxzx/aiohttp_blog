#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
__author__ = wbjxxzx
'''

import re
import time
import json
import hashlib
import base64
import asyncio
import logging
from aiohttp import web
from webframe import get, post
from models import User, Comment, Blog, next_id
from conf.config import configs
from apis import APIValueError, APIResourceNotFoundError

_RE_EMAIL = re.compile(r'^[a-zA-Z0-9\.\-\_]+\@[a-zA-Z0-9\-\_]+(\.[a-zA-Z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.find_all('email=?', [email])
    if len(users) > 0:
        raise APIValueError('register: failed', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '{}:{}'.format(uid, passwd)
    user = User(id=uid, name=name.strip(), email=email,
        passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
        image='http://www.gravator.com/avator/{}?d=mm&s=120'.format(hashlib.md5(email.encode('utf-8')).hexdigest())
    )
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


COOKIE_NAME = 'aiohttpsession'
_COOKIE_KEY = configs.session.secret

def user2cookie(user, max_age):
    '''
    Genetrate cookie str by user.
    '''
    expires = str(int(time.time() + max_age))
    s = '{}-{}-{}-{}'.format(user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '{}-{}-{}-{}'.format(uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@post('/api/authenticate')
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not passwd:
        raise APIValueError('passwd', 'Invalid passwd.')
    users = await User.find_all('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exists.')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid passwd.')
    # authenticate ok, set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/')
async def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur..'
    blogs = [
        Blog(id='1', name='test blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Aiohttp', summary=summary, created_at=time.time()-7300)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

@get('/api/users')
async def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = await User.find_all('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return {'page': p, 'users': []}
    users = await User.find_all(order_by='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return {'page': p, 'users': users}

@get('/hello')
def hello(request):
    return '<h1>Hello world</h1>'