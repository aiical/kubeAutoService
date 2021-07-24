#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc, send_state_back


class ServiceAccount:
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
        else:
            try:
                self.sys_name = global_info['sysName']
                self.app_name = global_info['appName']
            except(KeyError, NameError):
                self.logger.error(traceback.format_exc())
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：%s" % traceback.format_exc())
                abort(404)

    def get_service_account_info(self):
        self.logger.info("开始获取ServiceAccount信息")
        service_name, namespace = set_ns_svc(self.sys_name, self.app_name)
        service_account_info = {
            'serviceName': service_name,
            'namespace': namespace
        }

        self.logger.info("获取ServiceAccount信息完成")
        return service_account_info

    def create_service_account_yaml(self, service_account_info):
        self.logger.info("开始创建serviceAccount.yaml")
        self.logger.info("ServiceAccount配置如下：")
        self.logger.info(service_account_info)
        service_account_yaml_j2 = '%s/templates/k8s/serviceAccount.yaml.j2' % sys.path[0]
        service_account_yaml = '%s/serviceAccount.yaml' % self.k8s_path

        if not j2_to_file("server", service_account_info, service_account_yaml_j2, service_account_yaml):
            abort(404)
        self.logger.info("serviceAccount.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % service_account_yaml]
        return apply_command_list
