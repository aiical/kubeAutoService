#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import set_ns_svc, j2_to_file, shell_cmd


class AuthorizationPolicy:
    def __init__(self, settings_conf, global_info, policy_path):
        self.settings_conf = settings_conf
        self.global_info = global_info
        self.policy_path = policy_path
        self.logger = Logger("server")

    def get_ap_svc_to_svc_info(self):
        self.logger.info("开始获取AuthorizationPolicy信息")
        try:
            from_sys_name = self.global_info['sysName']
            from_app_name = self.global_info['appName']

            to_sys_name = self.global_info['toSysName']
            to_app_name = self.global_info['toAppName']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1

        from_service_name, from_namespace = set_ns_svc(from_sys_name, from_app_name)
        to_service_name, to_namespace = set_ns_svc(to_sys_name, to_app_name)
        policy_info = {
            "toServiceName": to_service_name,
            "toNamespace": to_namespace,
            "fromServiceName": from_service_name,
            "fromNamespace": from_namespace
        }
        return policy_info

    def create_svc_to_svc_yaml(self, policy_info):
        self.logger.info("开始创建AuthorizationPolicy.yaml")
        self.logger.info("AuthorizationPolicy配置如下：")
        self.logger.info(policy_info)

        policy_name = '%s-%s-from-%s-%s-policy' % (
            policy_info['to_service_name'], policy_info['to_namespace'],
            policy_info['from_service_name'], policy_info['from_namespace'])
        policy_file = '%s/%s.yaml' % (self.policy_path, policy_name)
        policy_file_j2 = '%s/templates/policy/service-to-service-authorizationpolicy.yaml.j2' % sys.path[0]
        if j2_to_file("server", policy_info, policy_file_j2, policy_file) == 1:
            self.logger.error("%s.yaml生成失败。" % policy_name)
            return 1
        return policy_name

    def deploy_svc_to_svc(self, policy_name):
        self.logger.info("%s.yaml已生成。" % policy_name)
        policy_file = '%s/%s.yaml' % (self.policy_path, policy_name)
        str_command = "kubectl apply -f %s" % policy_file
        code = shell_cmd("server", str_command)
        return code

    def delete_svc_to_svc(self, policy_info):
        policy_name = '%s-%s-from-%s-%s-policy' % (
            policy_info['to_service_name'], policy_info['to_namespace'],
            policy_info['from_service_name'], policy_info['from_namespace'])
        self.logger.info("删除%s配置" % policy_name)
        policy_file = '%s/%s.yaml' % (self.policy_path, policy_name)
        if os.path.exists(policy_file):
            str_command = "kubectl delete -f %s" % policy_file
            code = shell_cmd("server", str_command)
            return code
        else:
            self.logger.error("%s.yaml不存在。" % policy_name)
            return 1

    def get_ap_ns_to_svc_info(self):
        self.logger.info("开始获取AuthorizationPolicy信息")
        try:
            to_sys_name = self.global_info['sysName']
            to_app_name = self.global_info['appName']
            nginx_info = self.settings_conf['nginxInfo']['host']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1
        to_service_name, to_namespace = set_ns_svc(to_sys_name, to_app_name)
        policy_info = {
            'serviceName': to_service_name,
            'namespace': to_namespace,
            'nginxIpList': nginx_info
        }
        return policy_info

    def create_ns_to_svc_yaml(self, policy_info):
        self.logger.info("开始创建AuthorizationPolicy.yaml")
        self.logger.info("AuthorizationPolicy配置如下：")
        self.logger.info(policy_info)
        policy_yaml_j2 = '%s/templates/policy/namespace-authorizationpolicy.yaml.j2' % sys.path[0]
        policy_yaml = '%s/authorizationPolicy.yaml' % self.policy_path

        code = j2_to_file("server", policy_info, policy_yaml_j2, policy_yaml)
        if code == 1:
            return code
        self.logger.info("authorizationPolicy.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % policy_yaml]
        return apply_command_list
