#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import set_ns_svc, j2_to_file, shell_cmd


class InitPolicy:
    def __init__(self, settings_conf, policy_info):
        self.logger = Logger("server")
        self.settings_conf = settings_conf
        self.policy_info = policy_info
        try:
            global_config = self.policy_info['global']
            self.from_sys_name = global_config['sysName']
            self.from_app_name = global_config['appName']
            self.to_sys_name = global_config['toSysName']
            self.to_app_name = global_config['toAppName']
            self.sys_base_path = settings_conf['pathInfo']['deployBasePath']
            self.mode = global_config['mode']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
        self.policy_path = "%s/policyFile" % self.sys_base_path
        self.policy_path = self.policy_path.replace("//", "/")
        self.from_service_name, self.from_namespace = set_ns_svc(self.from_sys_name, self.from_app_name)
        self.to_service_name, self.to_namespace = set_ns_svc(self.to_sys_name, self.to_app_name)
        self.policy_name = '%s-%s-from-%s-%s-policy' % (
            self.to_service_name, self.to_namespace, self.from_service_name, self.from_namespace)
        self.policy_file = '%s/%s.yaml' % (self.policy_path, self.policy_name)
        if not os.path.exists(self.policy_path):
            os.makedirs(self.policy_path)

    def deploy(self):
        policy_info = {
            "toServiceName": self.to_service_name,
            "toNamespace": self.to_namespace,
            "fromServiceName": self.from_service_name,
            "fromNamespace": self.from_namespace
        }

        policy_file_j2 = '%s/templates/policy/service-to-service-authorizationpolicy.yaml.j2' % sys.path[0]
        if j2_to_file("server", policy_info, policy_file_j2, self.policy_file) == 1:
            self.logger.error("%s.yaml生成失败。" % self.policy_name)

        self.logger.info("%s.yaml已生成。" % self.policy_name)
        str_command = "kubectl apply -f %s" % self.policy_file
        code = shell_cmd("server", str_command)
        return code

    def delete(self):
        if os.path.exists(self.policy_file):
            str_command = "kubectl delete -f %s" % self.policy_file
            code = shell_cmd("server", str_command)
            return code
        else:
            self.logger.error("%s.yaml不存在。" % self.policy_name)
            return 1
