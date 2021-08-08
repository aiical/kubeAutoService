#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import os
import time
import traceback
from flask import abort
from k8s.InitProject import InitProject
from k8s.AuthorizationPolicy import AuthorizationPolicy
from publicClass.PublicFunc import j2_to_file, shell_cmd, send_state_back


class InitSystem(InitProject):
    def __init__(self, settings_conf, info):
        InitProject.__init__(self, settings_conf, info)
        try:
            self.harbor_ip = settings_conf['harborInfo']['host']
            self.nfs_default_info = settings_conf['nfsDefaults']
            self.istio_version = str(settings_conf['istioInfo']['version'])
            self.sys_base_path = settings_conf['pathInfo']['deployBasePath']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.library_repository = "%s/library" % self.harbor_ip
            self.istio_repository = "%s/istio" % self.harbor_ip
            self.sys_path = ""

    def create_sys_path(self):
        try:
            sys_name = self.para_config['global']['sysName']

        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.sys_path = "%s/%s/SysFile" % (self.sys_base_path, sys_name)
            self.sys_path = self.sys_path.replace("//", "/")
            if not os.path.exists(self.sys_path):
                os.makedirs(self.sys_path)

    def get_namespace_info(self):
        try:
            sys_name = self.para_config['global']['sysName']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            namespace = "%s-system" % sys_name
            namespace_info = {
                'namespace': namespace
            }
            return namespace_info

    def create_namespace_yaml(self, namespace_info):
        self.logger.info("开始创建namespace.yaml")
        self.logger.info("namespace配置如下：")
        self.logger.info(namespace_info)
        namespace = namespace_info['namespace']
        namespace_yaml_j2 = '%s/templates/sys/namespace.yaml.j2' % sys.path[0]
        namespace_yaml = '%s/namespace.yaml' % self.sys_path

        if not j2_to_file("server", namespace_info, namespace_yaml_j2, namespace_yaml):
            self.logger.error("namespace.yaml生成失败")
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:namespace.yaml生成失败")
            abort(404)
        self.logger.info("namespace.yaml已生成[%s]" % namespace)
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "[INFO]：namespace.yaml已生成[%s]" % namespace)
        apply_command = "kubectl apply -f %s" % namespace_yaml
        if not shell_cmd("server", apply_command):
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:COMMAND:%s执行出错" % apply_command)
            abort(404)
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "[INFO]：创建namespace成功[%s]" % namespace)

    def get_nfs_provider_info(self):
        try:
            sys_name = self.para_config['global']['sysName']
            nfs_type = self.para_config['nfsProviderInfo']['type']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            namespace = "%s-system" % sys_name
            if nfs_type == "default":
                nfs_info = self.nfs_default_info
            elif nfs_type == "customize":
                nfs_info = self.para_config['nfsProviderInfo']
            else:
                nfs_info = {}

            nfs_provider_info = {
                'nfsType': nfs_type,
                'sysName': sys_name,
                'namespace': namespace,
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

            if not shell_cmd("server", apply_command):
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:COMMAND:%s执行出错" % apply_command)
                abort(404)
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "[INFO]：创建nfs-provider成功")

    def get_ingress_gateway_info(self):
        try:
            sys_name = self.para_config['global']['sysName']
            gateway_info = self.para_config['gatewayInfo']
            traffic_info = self.para_config['traffic']
            http_node_port = traffic_info['http']['nodePort']
            replicas = gateway_info['replicas']
            cpu = gateway_info['cpu']
            memory = gateway_info['memory']
            tcp_info = traffic_info['tcp']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            namespace = "%s-system" % sys_name
            ingress_gateway_info = {
                'namespace': namespace,
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

        if not j2_to_file("server", ingress_gateway_info, ingress_gateway_yaml_j2, ingress_gateway_yaml):
            self.logger.error("istio-ingressgateway-%s.yaml生成失败。" % self.istio_version)
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:istio-ingressgateway-%s.yaml生成失败。" % self.istio_version)
            abort(404)
        self.logger.info("istio-ingressgateway-%s.yaml已生成。" % self.istio_version)
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "[INFO]：istio-ingressgateway-%s.yaml已生成。" % self.istio_version)
        apply_command = "kubectl apply -f %s" % ingress_gateway_yaml
        if not shell_cmd("server", apply_command):
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]:COMMAND:%s执行出错" % apply_command)
            abort(404)
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "[INFO]：创建系统所在名称空间的istio-ingressgateway成功")

    def deploy(self):
        try:
            global_info = self.para_config['global']
            mode = global_info['mode']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            if mode == "new":
                mode_info = "全新发布"
            elif mode == "update":
                mode_info = "更新发布"
            else:
                mode_info = "其他"
            self.logger.info("本次发布模式：【%s】" % mode_info)
            self.logger.info("本次发布类别：run sys")
            # system_task = InitSystem(setting_conf, post_json_data)
            self.create_sys_path()
            """创建namespace"""
            namespace_info = self.get_namespace_info()
            self.create_namespace_yaml(namespace_info)

            """创建系统所在名称空间的istio-ingressgateway"""
            ingress_gateway_info = self.get_ingress_gateway_info()
            self.create_ingress_gateway_yaml(ingress_gateway_info)

            """若有需要，创建该名称空间下的nfs-provider"""
            nfs_provider_info = self.get_nfs_provider_info()
            self.create_nfs_provider_yaml(nfs_provider_info)

            policy_info = self.para_config['policy']
            ap = AuthorizationPolicy(self.settings_conf, global_info, policy_info, self.sys_path)
            ap_policy_list = ap.get_ap_ns_to_ns_info()
            if ap_policy_list:
                for ap_policy in ap_policy_list:
                    apply_command_list = ap.create_ns_to_ns_yaml(ap_policy)
                    for apply_command in apply_command_list:
                        if not shell_cmd("server", apply_command):
                            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                            "[ERROR]:COMMAND:%s执行出错" % apply_command)
                            abort(404)
                        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                        "[INFO]：创建nfs-provider成功")

            time.sleep(2)
            self.logger.info("本次系统发布完成...")
            send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                            "[FINISH]：本次系统发布完成")

