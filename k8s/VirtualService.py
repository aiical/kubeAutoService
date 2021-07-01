#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc, calculate_weight


class VirtualService:
    def __init__(self, global_info, k8s_info, k8s_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path

    def get_virtual_service_info(self):
        logger = Logger("server")
        logger.info("开始获取virtualService信息")
        try:
            # run_env = self.global_info['runEnv']
            sys_name = self.global_info['sysName']
            app_name = self.global_info['appName']
            service_name, namespace = set_ns_svc(sys_name, app_name)
            dc_name = self.global_info['dcName']
            rule_type = self.k8s_info['serverType']['istio']['destinationRule']['type']
            is_pass_through = self.k8s_info['isPassThrough']
            """获取container信息"""
            container_info = self.k8s_info['container']
            port_info = container_info['portInfo']
            protocol = port_info['protocol']
            virtual_service_info = {
                'serviceName': service_name,
                'namespace': namespace,
                'dcName': dc_name,
                'isPassThrough': is_pass_through,
                'protocol': protocol,
                'ruleType': rule_type
            }
            if protocol == "tcp":
                tcp_port_num = port_info['protocolContent']['tcpPortNum']
                container_port = port_info['protocolContent']['portNum']
                virtual_service_info.update({
                    'containerPort': container_port,
                    'tcpPortNum': tcp_port_num
                })
            elif protocol == "http":
                container_port = port_info['protocolContent']['portNum']
                virtual_service_info.update({
                    'containerPort': container_port
                })

            # if rule_type == "roundRobin":
            version_count = int(self.k8s_info['versionCount'])
            # tmp_weight_list = self.k8s_info['serverType']['istio']['destinationRule']['roundRobin']['weight']
            tmp_weight_list = self.k8s_info['serverType']['istio']['destinationRule']['weight']

            weight_list = calculate_weight(tmp_weight_list, version_count)
            virtual_service_info.update({
                'versionCount': version_count,
                'weightList': weight_list
            })
            logger.info("获取virtualService信息完成")
            return virtual_service_info

        except Exception:
            logger.error(traceback.format_exc())

    def create_virtual_service_yaml(self, virtual_service_info):
        logger = Logger("server")
        logger.info("开始创建virtualservice.yaml")
        logger.info("virtualservice配置如下：")
        logger.info(virtual_service_info)
        virtual_service_yaml_j2 = '%s/templates/k8s/virtualservice.yaml.j2' % sys.path[0]
        virtual_service_yaml = '%s/virtualservice.yaml' % self.k8s_path

        j2_to_file("server", virtual_service_info, virtual_service_yaml_j2, virtual_service_yaml)
        logger.info("virtualservice.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % virtual_service_yaml]
        return apply_command_list