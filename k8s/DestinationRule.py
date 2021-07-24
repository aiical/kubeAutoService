#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc, send_state_back


class DestinationRule:
    def __init__(self, global_info, k8s_info, k8s_path):
        self.logger = Logger("server")
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path
        try:
            self.task_back_url = global_info['taskBackUrl']
            self.task_flow_id = global_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)

    def get_destination_rule_info(self):
        self.logger.info("开始获取destinationRule信息")
        try:
            sys_name = self.global_info['sysName']
            app_name = self.global_info['appName']
            service_name, namespace = set_ns_svc(sys_name, app_name)
            version_count = int(self.k8s_info['versionCount'])
            rule_type = self.k8s_info['serverType']['istio']['destinationRule']['type']
            destination_rule_info = {
                'serviceName': service_name,
                'namespace': namespace,
                'ruleType': rule_type,
                'versionCount': int(version_count)
            }

            if rule_type == "httpCookie":
                http_cookie_info = self.k8s_info['serverType']['istio']['destinationRule']['httpCookie']
                http_cookie_name = http_cookie_info['name']
                http_cookie_ttl = http_cookie_info['ttl']
                destination_rule_info.update({
                    'httpCookieName': http_cookie_name,
                    'httpCookieTtl': http_cookie_ttl
                })
            elif rule_type == "httpHeaderName":
                http_header_name = self.k8s_info['serverType']['istio']['destinationRule']['httpHeaderName']['name']
                destination_rule_info.update({
                    'httpHeaderName': http_header_name
                })
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.logger.info("获取destinationRule信息完成")
            return destination_rule_info

    def create_destination_rule_yaml(self, destination_rule_info):
        self.logger.info("开始创建destinationRule.yaml")
        self.logger.info("destinationRule配置如下：")
        self.logger.info(destination_rule_info)
        destination_rule_yaml_j2 = '%s/templates/k8s/destinationRule.yaml.j2' % sys.path[0]
        destination_rule_yaml = '%s/destinationRule.yaml' % self.k8s_path

        if not j2_to_file("server", destination_rule_info, destination_rule_yaml_j2, destination_rule_yaml):
            self.logger.error("destinationRule.yaml生成失败")
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:destinationRule.yaml生成失败")
            abort(404)
        self.logger.info("destinationRule.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % destination_rule_yaml]
        return apply_command_list
