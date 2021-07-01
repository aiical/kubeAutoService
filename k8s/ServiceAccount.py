#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class ServiceAccount:
    def __init__(self, global_info, k8s_info, k8s_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path

    def get_service_account_info(self):
        logger = Logger("server")
        logger.info("开始获取ServiceAccount信息")
        # run_env = self.global_info['runEnv']
        sys_name = self.global_info['sysName']
        app_name = self.global_info['appName']
        service_name, namespace = set_ns_svc(sys_name, app_name)

        service_account_info = {
            'serviceName': service_name,
            'namespace': namespace
        }

        logger.info("获取ServiceAccount信息完成")
        return service_account_info

    def create_service_account_yaml(self, service_account_info):
        logger = Logger("server")
        logger.info("开始创建serviceaccount.yaml")
        logger.info("ServiceAccount配置如下：")
        logger.info(service_account_info)
        service_account_yaml_j2 = '%s/templates/k8s/serviceaccount.yaml.j2' % sys.path[0]
        service_account_yaml = '%s/serviceaccount.yaml' % self.k8s_path

        j2_to_file("server", service_account_info, service_account_yaml_j2, service_account_yaml)
        logger.info("serviceaccount.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % service_account_yaml]
        return apply_command_list
