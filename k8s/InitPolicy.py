#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os


class InitPolicy:
    def __init__(self, settings_conf, policy_info):
        self.settings_conf = settings_conf
        self.policy_info = policy_info

        sys_base_path = settings_conf['pathInfo']['deployBasePath']
        self.policy_path = "%s/policyFile" % sys_base_path
        self.policy_path = self.policy_path.replace("//", "/")
        if not os.path.exists(self.policy_path):
            os.makedirs(self.policy_path)

    def deploy(self):
        
        pass