#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import set_ns_svc, j2_to_file, shell_cmd, send_state_back


class AuthorizationPolicy:
    def __init__(self, settings_conf, global_info, policy_path):
        self.settings_conf = settings_conf
        self.global_info = global_info
        self.policy_path = policy_path
        self.logger = Logger("server")
        try:
            self.task_back_url = global_info['taskBackUrl']
            self.task_flow_id = global_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)

    def get_ap_svc_to_svc_info(self):
        self.logger.info("开始获取AuthorizationPolicy信息")
        try:
            from_sys_name = self.global_info['sysName']
            from_app_name = self.global_info['appName']

            to_sys_name = self.global_info['toSysName']
            to_app_name = self.global_info['toAppName']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
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
        policy_file_j2 = '%s/templates/policy/service-to-service-authorizationPolicy.yaml.j2' % sys.path[0]
        if not j2_to_file("server", policy_info, policy_file_j2, policy_file):
            self.logger.error("%s.yaml生成失败。" % policy_name)
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:%s.yaml生成失败。" % policy_name)
            abort(404)
        self.logger.info("%s.yaml生成失败。" % policy_name)
        return policy_name

    def deploy_svc_to_svc(self, policy_name):
        self.logger.info("%s.yaml已生成。" % policy_name)
        policy_file = '%s/%s.yaml' % (self.policy_path, policy_name)
        str_command = "kubectl apply -f %s" % policy_file
        if not shell_cmd("server", str_command):
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:COMMAND:%s执行出错" % str_command)
            abort(404)

    def delete_svc_to_svc(self, policy_info):
        policy_name = '%s-%s-from-%s-%s-policy' % (
            policy_info['to_service_name'], policy_info['to_namespace'],
            policy_info['from_service_name'], policy_info['from_namespace'])
        self.logger.info("删除%s配置" % policy_name)
        policy_file = '%s/%s.yaml' % (self.policy_path, policy_name)
        if os.path.exists(policy_file):
            str_command = "kubectl delete -f %s" % policy_file
            if not shell_cmd("server", str_command):
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:COMMAND:%s执行出错" % str_command)
                abort(404)
        else:
            self.logger.error("%s.yaml不存在。" % policy_name)
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:%s.yaml不存在。" % policy_name)
            abort(404)

    def get_ap_ns_to_svc_info(self):
        self.logger.info("开始获取AuthorizationPolicy信息")
        try:
            to_sys_name = self.global_info['sysName']
            to_app_name = self.global_info['appName']
            nginx_info = self.settings_conf['nginxInfo']['host']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
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
        policy_yaml_j2 = '%s/templates/policy/service-default-authorizationPolicy.yaml.j2' % sys.path[0]
        policy_yaml = '%s/authorizationPolicy.yaml' % self.policy_path

        if not j2_to_file("server", policy_info, policy_yaml_j2, policy_yaml):
            self.logger.error("authorizationPolicy.yaml生成失败")
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:authorizationPolicy.yaml生成失败")
            abort(404)
        self.logger.info("authorizationPolicy.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % policy_yaml]
        return apply_command_list
