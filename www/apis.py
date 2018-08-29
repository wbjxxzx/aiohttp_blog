#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
__author__ = wbjxxzx
'''

import json
import inspect
import functools
import logging

class APIError(Exception):
    """
    the base APIError which contains error(required), data(optinal) ans message(optional).
    """
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    """
    indicate the input value has error or invalid.
    the data specifies the error field of input form. 
    """
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value: invalid', field, message)

class APIResourceNotFoundError(APIError):
    """
    indicate the reource was not found
    the data specifies the resource name
    """
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    """
    indaicate the api has no permission
    """
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)