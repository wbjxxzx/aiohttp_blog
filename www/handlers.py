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
from webframe import get, post
from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
    users = await User.find_all()
    return {
        '__template__': 'test.html',
        'users': users
    }

@get('/hello')
def hello(request):
    return '<h1>Hello world</h1>'