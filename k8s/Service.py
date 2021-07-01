#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class Service:
    def __init__(self, global_info, k8s_info, k8s_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path

    def get_service_info(self):
        logger = Logger("server")
        logger.info("开始获取service信息")
        # run_env = self.global_info['runEnv']
        sys_name = self.global_info['sysName']
        app_name = self.global_info['appName']
        service_name, namespace = set_ns_svc(sys_name, app_name)
        tmp_server_type = self.k8s_info['serverType']['type']
        # if_dubbo = self.global_info['ifDubbo']['flag']
        # dubbo_port = ""
        # if if_dubbo == "Y":
        #     dubbo_port = str(self.global_info['ifDubbo']['port'])
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
        service_info = {
            'ifHeadless': "N",
            'serviceName': service_name,
            'namespace': namespace,
            'serviceType': service_type,
            'nodePort': node_port,
            'protocol': protocol,
            'containerPort': container_port,
            # 'dubboPort': dubbo_port
        }
        logger.info("获取service信息完成")
        return service_info

    def create_service_yaml(self, service_info):
        if_headless = service_info['ifHeadless']
        if if_headless == "N":
            svc_str = "service"
        else:
            svc_str = "service-headless"
        logger = Logger("server")
        logger.info("开始创建%s.yaml" % svc_str)
        logger.info("%s配置如下：" % svc_str)
        logger.info(service_info)
        service_yaml_j2 = '%s/templates/k8s/service.yaml.j2' % sys.path[0]
        service_yaml = '%s/%s.yaml' % (self.k8s_path, svc_str)

        j2_to_file("server", service_info, service_yaml_j2, service_yaml)
        logger.info("%s.yaml已生成。" % svc_str)
        apply_command_list = ["kubectl apply -f %s" % service_yaml]
        return apply_command_list

