#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc, send_state_back


class Gateway:
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

    def get_gateway_info(self):
        self.logger.info("开始获取gateway信息")
        try:
            sys_name = self.global_info['sysName']
            app_name = self.global_info['appName']
            service_name, namespace = set_ns_svc(sys_name, app_name)
            dc_name = self.global_info['dcName']
            is_pass_through = self.k8s_info['isPassThrough']
            if sys_name == "itsm" and app_name == "web":
                is_pass_through = "Y"
            """获取container信息"""
            container_info = self.k8s_info['container']
            port_info = container_info['portInfo']
            protocol = port_info['protocol']
            gateway_info = {
                'serviceName': service_name,
                'namespace': namespace,
                'dcName': dc_name,
                'isPassThrough': is_pass_through,
                'protocol': protocol
            }
            if protocol == "tcp":
                tcp_port_num = port_info['protocolContent']['tcpPortNum']
                gateway_info.update({
                    'tcpPortNum': tcp_port_num
                })
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.logger.info("获取gateway信息完成")
            return gateway_info

    def create_gateway_yaml(self, gateway_info):
        self.logger.info("开始创建gateway.yaml")
        self.logger.info("gateway配置如下：")
        self.logger.info(gateway_info)
        gateway_yaml_j2 = '%s/templates/k8s/gateway.yaml.j2' % sys.path[0]
        gateway_yaml = '%s/gateway.yaml' % self.k8s_path

        if not j2_to_file("server", gateway_info, gateway_yaml_j2, gateway_yaml):
            self.logger.error("gateway.yaml生成失败")
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:gateway.yaml生成失败")
            abort(404)
        self.logger.info("gateway.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % gateway_yaml]
        return apply_command_list
