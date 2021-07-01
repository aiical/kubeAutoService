#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
"""
该日志类可以把不同级别的日志输出到不同的日志文件中
"""
import os
import sys
import logging
import time
from logging import handlers


class Logger:
    def __init__(self, log_name):
        self.log_name = log_name
        log_levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
            logging.NOTSET
        ]
        self.__loggers = {}
        fmt = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
        for level in log_levels:
            # 创建logger
            logger = logging.getLogger(str(level))

            logger.setLevel(level)
            logger.handlers.clear()
            if not os.path.exists(sys.path[0] + "/logs/"):
                os.mkdir(sys.path[0] + "/logs/")
            # 创建handler用于写日日志文件
            log_path = sys.path[0] + "/logs/%s.log" % self.log_name
            th = handlers.RotatingFileHandler(filename=log_path, maxBytes=10*1024*1024, backupCount=10, encoding='utf-8')
            th.setFormatter(fmt)
            th.setLevel(logging.INFO)
            logger.addHandler(th)
            logger.setLevel(level)
            self.__loggers.update({level: logger})

    def info(self, message):
        self.__loggers[logging.INFO].info(message)

    def error(self, message):
        self.__loggers[logging.ERROR].error(message)

    def warn(self, message):
        self.__loggers[logging.WARNING].warning(message)

    def debug(self, message):
        self.__loggers[logging.DEBUG].debug(message)

    def critical(self, message):
        self.__loggers[logging.CRITICAL].critical(message)


if __name__ == "__main__":
    loggers = Logger("test")
    while True:
        loggers.debug("debug")
        loggers = Logger("test")
        loggers.info("info")
        loggers = Logger("test")
        loggers.warn("warn")
        loggers = Logger("test")
        loggers.error("error")
        time.sleep(1)




