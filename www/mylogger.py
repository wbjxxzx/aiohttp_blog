#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
__author__ = wbjxxzx
'''

import logging
import logging.config
import os
confpath = os.path.dirname(os.path.abspath(__file__))
logging.config.fileConfig(os.path.join(confpath, "conf", "logging.conf"))
logger = logging.getLogger("")