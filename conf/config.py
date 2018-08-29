#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
__author__ = wbjxxzx
'''
import config_develop

class MyDict(dict):
    """
    simple dict but support access as d.x style
    """
    def __init__(self, names=(), values=(), **kw):
        super(MyDict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'MyDict' object has no attribute '{}'".format(key))

    def __setattr__(self, key, value):
        self[key] = value


def merge(develop, override):
    r = {}
    for k, v in develop.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

def to_mydict(d):
    md = MyDict()
    for k, v in d.items():
        md[k] = to_mydict(v) if isinstance(v, dict) else v
    return md

configs = config_develop.configs
try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = to_mydict(configs)