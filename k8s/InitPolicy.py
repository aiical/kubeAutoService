#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import traceback
from publicClass.Logger import Logger
from k8s.InitProject import InitProject


class InitPolicy(InitProject):
    def __init__(self, settings_conf, policy_info):
        InitProject.__init__(self, settings_conf, policy_info)

    def deploy(self):
        pass
