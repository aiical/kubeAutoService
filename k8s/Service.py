#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc, send_state_back


class Service:
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

    def get_service_info(self):
        self.logger.info("开始获取service信息")
        try:
            sys_name = self.global_info['sysName']
            app_name = self.global_info['appName']
            service_name, namespace = set_ns_svc(sys_name, app_name)
            tmp_server_type = self.k8s_info['serverType']['type']
            if not tmp_server_type:
                server_type = "istio"
            else:
                server_type = tmp_server_type

            if server_type == "nodePort":
                node_port = self.k8s_info['serverType']['nodePort']['port']
                service_type = "NodePort"
            else:
                node_port = ""
                service_type = "ClusterIP"

            container_info = self.k8s_info['container']
            port_info = container_info['portInfo']
            protocol = port_info['protocol']

            if protocol == "http":
                container_port = port_info['protocolContent']['portNum']
            elif protocol == "tcp":
                container_port = port_info['protocolContent']['portNum']
            else:
                container_port = 9999
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            service_info = {
                'ifHeadless': "N",
                'serviceName': service_name,
                'namespace': namespace,
                'serviceType': service_type,
                'nodePort': node_port,
                'protocol': protocol,
                'containerPort': container_port,
            }
            self.logger.info("获取service信息完成")
            return service_info

    def create_service_yaml(self, service_info, if_headless):
        if if_headless == "N":
            svc_str = "service"
        else:
            svc_str = "service-headless"
        self.logger.info("开始创建%s.yaml" % svc_str)
        self.logger.info("%s配置如下：" % svc_str)
        self.logger.info(service_info)
        service_yaml_j2 = '%s/templates/k8s/service.yaml.j2' % sys.path[0]
        service_yaml = '%s/%s.yaml' % (self.k8s_path, svc_str)

        if not j2_to_file("server", service_info, service_yaml_j2, service_yaml):
            self.logger.error("%s.yaml生成失败。" % svc_str)
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:%s.yaml生成失败。" % svc_str)
            abort(404)
        self.logger.info("%s.yaml已生成。" % svc_str)
        apply_command_list = ["kubectl apply -f %s" % service_yaml]
        return apply_command_list

