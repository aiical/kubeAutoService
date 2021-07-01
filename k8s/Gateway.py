#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class Gateway:
    def __init__(self, global_info, k8s_info, k8s_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path

    def get_gateway_info(self):
        logger = Logger("server")
        logger.info("开始获取gateway信息")
        # run_env = self.global_info['runEnv']
        sys_name = self.global_info['sysName']
        app_name = self.global_info['appName']
        service_name, namespace = set_ns_svc(sys_name, app_name)
        # sys_name, service_name, namespace = set_run_env(run_env, sys_name, app_name)
        dc_name = self.global_info['dcName']
        is_pass_through = self.k8s_info['isPassThrough']
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
            tcp_port_num = port_info['tcp']['tcpPortNum']
            gateway_info.update({
                'tcpPortNum': tcp_port_num
            })
        logger.info("获取gateway信息完成")
        return gateway_info

    def create_gateway_yaml(self, gateway_info):
        logger = Logger("server")
        logger.info("开始创建gateway.yaml")
        logger.info("gateway配置如下：")
        logger.info(gateway_info)
        gateway_yaml_j2 = '%s/templates/k8s/gateway.yaml.j2' % sys.path[0]
        gateway_yaml = '%s/gateway.yaml' % self.k8s_path

        j2_to_file("server", gateway_info, gateway_yaml_j2, gateway_yaml)
        logger.info("gateway.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % gateway_yaml]
        return apply_command_list
