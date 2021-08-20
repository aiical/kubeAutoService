#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
from flask import abort
from k8s.InitProject import InitProject


class PatchLabel(InitProject):
    def __init__(self, settings_conf, info):
        InitProject.__init__(self, settings_conf, info)

    def deploy(self):
        pass
