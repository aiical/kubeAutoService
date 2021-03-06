#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import set_ns_svc, j2_to_file, shell_cmd, send_state_back


class AuthorizationPolicy:
    def __init__(self, settings_conf, global_info, k8s_info, policy_path):
        self.settings_conf = settings_conf
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.policy_path = policy_path
        self.logger = Logger("server")
        try:
            self.task_back_url = global_info['taskBackUrl']
            self.task_flow_id = global_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)

    def get_ap_svc_to_svc_info(self):
        policy_info_list = []
        self.logger.info("开始获取AuthorizationPolicy信息")
        try:
            from_sys_name = self.global_info['sysName']
            from_app_name = self.global_info['appName']
            from_service_name, from_namespace = set_ns_svc(from_sys_name, from_app_name)
            if self.k8s_info["serverType"]['istio'].__contains__('accessService'):
                access_service_list = self.k8s_info["serverType"]['istio']['accessService']
                if access_service_list:
                    for access_service in access_service_list:
                        to_namespace = access_service['namespace']
                        to_service_name = access_service['toAppName']
                        policy_info = {
                            "toServiceName": to_service_name,
                            "toNamespace": to_namespace,
                            "fromServiceName": from_service_name,
                            "fromNamespace": from_namespace
                        }
                        policy_info_list.append(policy_info)
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            return policy_info_list

    def create_svc_to_svc_yaml(self, policy_info):
        self.logger.info("开始创建AuthorizationPolicy.yaml")
        self.logger.info("AuthorizationPolicy配置如下：")
        self.logger.info(policy_info)
        try:
            policy_name = '%s-%s-to-%s-%s-policy' % (
                policy_info['from_service_name'], policy_info['from_namespace'],
                policy_info['to_service_name'], policy_info['to_namespace'])
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            policy_file = '%s/%s.yaml' % (self.policy_path, policy_name)
            policy_file_j2 = '%s/templates/policy/service-to-service-authorizationPolicy.yaml.j2' % sys.path[0]
            if not j2_to_file("server", policy_info, policy_file_j2, policy_file):
                self.logger.error("%s.yaml生成失败。" % policy_name)
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:%s.yaml生成失败。" % policy_name)
                abort(404)
            self.logger.info("%s.yaml生成成功。" % policy_name)
            apply_command_list = ["kubectl apply -f %s" % policy_file]
            return apply_command_list

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

    def get_ap_ns_to_ns_info(self):
        self.logger.info("开始获取AuthorizationPolicy信息")
        policy_info_list = []
        try:
            from_sys_name = self.global_info['sysName']
            to_policy_info = self.k8s_info['to']
            to_namespace_list = to_policy_info['namespace']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            from_namespace = "%s-system" % from_sys_name
            if to_namespace_list:
                for to_namespace in to_namespace_list:
                    policy_info = {
                        'toNamespace': to_namespace,
                        'fromNamespace': from_namespace
                    }
                    policy_info_list.append(policy_info)
            return policy_info_list

    def create_ns_to_ns_yaml(self, policy_info):
        self.logger.info("开始创建AuthorizationPolicy.yaml")
        self.logger.info("AuthorizationPolicy配置如下：")
        self.logger.info(policy_info)
        try:
            policy_name = '%s-to-%s-policy' % (
                policy_info['from_namespace'],
                policy_info['to_namespace'])
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            policy_yaml_j2 = '%s/templates/policy/ns-to-ns-authorizationPolicy.yaml.j2' % sys.path[0]
            policy_yaml = '%s/%s.yaml' % (self.policy_path, policy_name)

            if not j2_to_file("server", policy_info, policy_yaml_j2, policy_yaml):
                self.logger.error("%s.yaml生成失败" % policy_name)
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:%s.yaml生成失败" % policy_name)
                abort(404)
            self.logger.info("%s.yaml已生成。" % policy_name)
            apply_command_list = ["kubectl apply -f %s" % policy_yaml]
            return apply_command_list
