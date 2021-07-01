#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import os
import time
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, shell_cmd


class InitSystem:
    def __init__(self, settings_conf, sys_info):
        self.logger = Logger("server")
        self.sys_info = sys_info
        """生产k8s yaml文件存放地址"""
        try:
            self.sys_name = self.sys_info['global']['sysName']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
        """获取系统名和名称空间"""
        self.namespace = "%s-system" % self.sys_name

        """读取settings设置"""
        try:
            sys_base_path = settings_conf['pathInfo']['deployBasePath']
            self.sys_path = "%s/%s/SysFile" % (sys_base_path, self.sys_name)
            self.harbor_ip = settings_conf['harborInfo']['host']
            self.nfs_default_info = settings_conf['nfsDefaults']
            self.istio_version = str(settings_conf['istioInfo']['version'])
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
        self.sys_path = self.sys_path.replace("//", "/")

        if not os.path.exists(self.sys_path):
            os.makedirs(self.sys_path)

        self.library_repository = "%s/library" % self.harbor_ip
        self.istio_repository = "%s/istio" % self.harbor_ip

    def get_namespace_info(self):
        namespace = self.namespace
        namespace_info = {
            'namespace': namespace
        }
        return namespace_info

    def create_namespace_yaml(self, namespace_info):
        self.logger.info("开始创建namespace.yaml")
        self.logger.info("namespace配置如下：")
        self.logger.info(namespace_info)
        namespace_yaml_j2 = '%s/templates/sys/namespace.yaml.j2' % sys.path[0]
        namespace_yaml = '%s/namespace.yaml' % self.sys_path

        j2_to_file("server", namespace_info, namespace_yaml_j2, namespace_yaml)
        self.logger.info("namespace.yaml已生成。")
        apply_command = "kubectl apply -f %s" % namespace_yaml
        code = shell_cmd("server", apply_command)
        return code

    def get_nfs_provider_info(self):
        nfs_type = self.sys_info['nfsProviderInfo']['type']
        if nfs_type == "default":
            nfs_info = self.nfs_default_info
        elif nfs_type == "customize":
            nfs_info = self.sys_info['nfsProviderInfo']
        else:
            nfs_info = {}

        nfs_provider_info = {
            'nfsType': nfs_type,
            'sysName': self.sys_name,
            'namespace': self.namespace,
            'nfsInfo': nfs_info,
            'libraryRepository': self.library_repository
        }

        return nfs_provider_info

    def create_nfs_provider_yaml(self, nfs_provider_info):
        nfs_type = nfs_provider_info['nfsType']
        if nfs_type != "none":
            self.logger.info("开始创建nfs-provider.yaml")
            self.logger.info("nfs-provider配置如下：")
            self.logger.info(nfs_provider_info)
            nfs_provider_yaml_j2 = '%s/templates/sys/nfs-provider.yaml.j2' % sys.path[0]
            nfs_provider_yaml = '%s/nfs-provider.yaml' % self.sys_path

            j2_to_file("server", nfs_provider_info, nfs_provider_yaml_j2, nfs_provider_yaml)
            self.logger.info("nfs-provider.yaml已生成。")
            apply_command = "kubectl apply -f %s" % nfs_provider_yaml

            code = shell_cmd("server", apply_command)
            return code
        else:
            return 0

    def get_ingress_gateway_info(self):
        gateway_info = self.sys_info['gatewayInfo']
        traffic_info = self.sys_info['traffic']
        http_node_port = traffic_info['http']['nodePort']
        replicas = gateway_info['replicas']
        cpu = gateway_info['cpu']
        memory = gateway_info['memory']
        tcp_info = traffic_info['tcp']
        ingress_gateway_info = {
            'namespace': self.namespace,
            'istioVersion': self.istio_version,
            'istioRepository': self.istio_repository,
            'replicas': replicas,
            'cpu': cpu,
            'memory': memory,
            'httpNodePort': http_node_port,
            'tcpInfo': tcp_info
        }

        return ingress_gateway_info

    def create_ingress_gateway_yaml(self, ingress_gateway_info):
        self.logger.info("开始创建istio-ingressgateway-%s.yaml" % self.istio_version)
        self.logger.info("istio-ingressgateway配置如下：")
        self.logger.info(ingress_gateway_info)
        ingress_gateway_yaml_j2 = '%s/templates/sys/istio-ingressgateway-1.6.yaml.j2' % sys.path[0]
        ingress_gateway_yaml = '%s/istio-ingressgateway-%s.yaml' % (self.sys_path, self.istio_version)

        j2_to_file("server", ingress_gateway_info, ingress_gateway_yaml_j2, ingress_gateway_yaml)
        self.logger.info("istio-ingressgateway-%s.yaml已生成。" % self.istio_version)
        apply_command = "kubectl apply -f %s" % ingress_gateway_yaml
        code = shell_cmd("server", apply_command)
        return code

    def deploy(self):
        self.logger.info("接收系统json数据:'%r'" % self.sys_info)
        global_config = self.sys_info['global']
        mode = global_config['mode']
        if mode == "new":
            mode_info = "全新发布"
        elif mode == "update":
            mode_info = "更新发布"
        else:
            mode_info = "其他"
        self.logger.info("本次发布模式：【%s】" % mode_info)
        self.logger.info("本次发布类别：run sys")
        # system_task = InitSystem(setting_conf, post_json_data)
        """创建namespace"""
        namespace_info = self.get_namespace_info()
        code = self.create_namespace_yaml(namespace_info)
        if code == 1:
            return 1
        """创建系统所在名称空间的istio-ingressgateway"""
        ingress_gateway_info = self.get_ingress_gateway_info()
        code = self.create_ingress_gateway_yaml(ingress_gateway_info)
        if code == 1:
            return 1
        """若有需要，创建该名称空间下的nfs-provider"""
        nfs_provider_info = self.get_nfs_provider_info()
        code = self.create_nfs_provider_yaml(nfs_provider_info)
        if code == 1:
            return 1
        time.sleep(10)
        self.logger.info("本次发布完成...")
        return 0
