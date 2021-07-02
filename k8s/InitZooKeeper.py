#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from docker.DockerImage import DockerImage
from publicClass.Logger import Logger
from publicClass.PublicFunc import set_ns_svc, j2_to_file


class InitZooKeeper:
    def __init__(self, settings_conf, zk_info):
        self.logger = Logger("server")
        self.zk_info = zk_info
        self.settings_conf = settings_conf
        try:
            self.task_back_url = self.settings_conf['taskInfoBack']['url']
            self.task_flow_id = self.zk_info['taskFlowId']
            self.sys_name = self.zk_info['sysName']
            self.app_name = self.zk_info['appName']
            self.deploy_base_path = self.settings_conf['pathInfo']['deployBasePath']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())

        self.service_name, self.namespace = set_ns_svc(self.sys_name, self.app_name)
        self.zk_path = "%s/%s/%s-zookeeper" % (self.deploy_base_path, self.sys_name, self.service_name)
        self.zk_path = self.zk_path.replace("//", "/")
        if not os.path.exists(self.zk_path):
            os.makedirs(self.zk_path)

    def deploy(self):
        try:
            docker_config = {
                'useType': self.zk_info['useType'],
                'existImage': self.zk_info['existImage']
            }
            harbor_info = self.settings_conf['harborInfo']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1
        image_info = {
            'dockerInfo': docker_config,
            'sysName': self.sys_name,
            'serviceName': self.service_name,
            'harborInfo': harbor_info
        }
        str_image_final = DockerImage.create_full_image_name(image_info)
        zk_conf = {
            'serviceName': self.service_name,
            'namespace': self.namespace,
            'imageFullName': str_image_final
        }

        flag = 0
        zk_sts_file_j2 = '%s/templates/zookeeper/statefulSet.yaml.j2' % sys.path[0]
        zk_sts_file = '%s/zk-statefulSet.yaml' % self.zk_path
        if j2_to_file("server", zk_conf, zk_sts_file_j2, zk_sts_file) == 1:
            self.logger.error("zk-statefulSet.yaml生成失败。")
            flag += 1
        self.logger.info("zk-statefulSet.yaml已生成。")

        zk_svc_file_j2 = '%s/templates/zookeeper/service.yaml.j2' % sys.path[0]
        zk_svc_file = '%s/zk-service.yaml' % self.zk_path
        if j2_to_file("server", zk_conf, zk_svc_file_j2, zk_svc_file) == 1:
            self.logger.error("zk-service.yaml生成失败。")
            flag += 1
        self.logger.info("zk-service.yaml已生成。")

        zk_cm_file_j2 = '%s/templates/zookeeper/configMap.yaml.j2' % sys.path[0]
        zk_cm_file = '%s/zk-configMap.yaml' % self.zk_path
        if j2_to_file("server", zk_conf, zk_cm_file_j2, zk_cm_file) == 1:
            self.logger.error("zk-configMap.yaml生成失败。")
            flag += 1
        self.logger.info("zk-configMap.yaml已生成。")

        zk_sa_file_j2 = '%s/templates/zookeeper/serviceAccount.yaml.j2' % sys.path[0]
        zk_sa_file = '%s/zk-serviceAccount.yaml' % self.zk_path
        if j2_to_file("server", zk_conf, zk_sa_file_j2, zk_sa_file) == 1:
            self.logger.error("zk-serviceAccount.yaml生成失败。")
            flag += 1
        self.logger.info("zk-serviceAccount.yaml已生成。")
        if flag > 0:
            return 1

        return 0
