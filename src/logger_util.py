#!/usr/bin/env python
# _*_ coding: utf-8 _*_
################################################################################
#
# Copyright (c) 2014  All Rights Reserved
#
################################################################################
"""
This module realizes different level logging output to different files.

Author: weileizhe
Date: 2014/12/24 00:00:06
"""

import logging
import logging.handlers
import os


def init_logger(log_path, log_level=logging.INFO, log_split_interval="D", backup_num=7,
                 log_format="%(levelname)s: %(asctime)s: %(filename)s:%(lineno)d * \
                 %(thread)d %(message)s",
                 date_format="%m-%d %H:%M:%S"):
    """ Initialize logging module for mini spider.

    Args:
      log_path: Log file path prefix.
      log_level: Message above the level will be displayed(DEBUG < INFO < WARNING < ERROR < CRITICAL),
             the default value is logging.INFO.
      log_split_interval: The log file split time interval.
                          'S' : Seconds
                          'M' : Minutes
                          'H' : Hours
                          'D' : Days
                          'W' : Week day
                          default value: 'D'
      log_format: The format of the log.
                  default format:
                  %(levelname)s: %(asctime)s: %(filename)s:%(linenum)d * %(thread)d %(message)s
                  INFO: 12-25 21:33:42: bd_logging.py:60 * 134814749989899 Hello log.
      backup_num: The backup file number to keep,default value: 7.

    Raises:
        OSError: Fail to create log directories.
        IOError: Fail to open log files.
    """
    log_formatter = logging.Formatter(log_format, date_format)
    logger = logging.getLogger()
    logger.setLevel(log_level)

    log_directory = os.path.dirname(log_path)
    if not os.path.isdir(log_directory):
        os.makedirs(log_directory)

    handler = logging.handlers.TimedRotatingFileHandler(log_path + ".log",
                                                        when=log_split_interval,
                                                        backupCount=backup_num)
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)

    handler = logging.handlers.TimedRotatingFileHandler(log_path + ".log.wf",
                                                        when=log_split_interval,
                                                        backupCount=backup_num)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)
