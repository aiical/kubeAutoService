#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class DestinationRule:
    def __init__(self, global_info, k8s_info, k8s_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path

    def get_destination_rule_info(self):
        logger = Logger("server")
        logger.info("开始获取destinationRule信息")
        try:
            # run_env = self.global_info['runEnv']
            sys_name = self.global_info['sysName']
            app_name = self.global_info['appName']
            # sys_name, service_name, namespace = set_run_env(run_env, sys_name, app_name)
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
            logger.info("获取destinationRule信息完成")
            return destination_rule_info
        except Exception:
            logger.error(traceback.format_exc())

    def create_destination_rule_yaml(self, destination_rule_info):
        logger = Logger("server")
        logger.info("开始创建destinationrule.yaml")
        logger.info("destinationrule配置如下：")
        logger.info(destination_rule_info)
        destination_rule_yaml_j2 = '%s/templates/k8s/destinationrule.yaml.j2' % sys.path[0]
        destination_rule_yaml = '%s/destinationrule.yaml' % self.k8s_path

        j2_to_file("server", destination_rule_info, destination_rule_yaml_j2, destination_rule_yaml)
        logger.info("destinationrule.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % destination_rule_yaml]
        return apply_command_list
