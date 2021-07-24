#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from flask import abort
from docker.DockerImage import DockerImage
from publicClass.Logger import Logger
from publicClass.PublicFunc import set_ns_svc, j2_to_file, send_state_back


class InitZooKeeper:
    def __init__(self, settings_conf, zk_info):
        self.logger = Logger("server")
        self.zk_info = zk_info
        self.settings_conf = settings_conf
        try:
            self.task_back_url = self.settings_conf['taskInfoBack']['url']
            self.task_flow_id = self.zk_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)
        else:
            try:
                self.sys_name = self.zk_info['sysName']
                self.app_name = self.zk_info['appName']
                self.deploy_base_path = self.settings_conf['pathInfo']['deployBasePath']
            except(KeyError, NameError):
                self.logger.error(traceback.format_exc())
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：%s" % traceback.format_exc())
                abort(404)
            else:
                self.service_name, self.namespace = set_ns_svc(self.sys_name, self.app_name)
                self.zk_path = "%s/%s/%s-zookeeper" % (self.deploy_base_path, self.sys_name, self.service_name)
                self.zk_path = self.zk_path.replace("//", "/")
                if not os.path.exists(self.zk_path):
                    os.makedirs(self.zk_path)
                self.command_list = []

    def deploy(self):
        try:
            docker_config = {
                'useType': self.zk_info['useType'],
                'existImage': self.zk_info['existImage']
            }
            harbor_info = self.settings_conf['harborInfo']
            image_name = self.zk_info['existImage']['imageName']
            if image_name != 'zookeeper':
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：发布所用镜像不是zookeeper镜像")
                abort(404)
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            image_info = {
                'taskBackUrl': self.task_back_url,
                'taskFlowId': self.task_flow_id,
                'dockerInfo': docker_config,
                'sysName': self.sys_name,
                'serviceName': self.service_name,
                'harborInfo': harbor_info
            }
            str_image_final = DockerImage.create_full_image_name(image_info)
            self.logger.info("本次发布应用zookeeper镜像全名为：%s" % str_image_final)
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "[INFO]：应用镜像名创建成功[%s]" % str_image_final)
            zk_conf = {
                'serviceName': self.service_name,
                'namespace': self.namespace,
                'imageFullName': str_image_final
            }

            zk_sts_file_j2 = '%s/templates/zookeeper/statefulSet.yaml.j2' % sys.path[0]
            zk_sts_file = '%s/zk-statefulSet.yaml' % self.zk_path
            if not j2_to_file("server", zk_conf, zk_sts_file_j2, zk_sts_file):
                self.logger.error("zk-statefulSet.yaml生成失败")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:zk-statefulSet.yaml生成失败")
                abort(404)
            self.logger.info("zk-statefulSet.yaml已生成。")
            self.command_list.append("kubectl apply -f %s" % zk_sts_file)

            zk_svc_file_j2 = '%s/templates/zookeeper/service.yaml.j2' % sys.path[0]
            zk_svc_file = '%s/zk-service.yaml' % self.zk_path
            if not j2_to_file("server", zk_conf, zk_svc_file_j2, zk_svc_file):
                self.logger.error("zk-service.yaml生成失败")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:zk-service.yaml生成失败")
                abort(404)
            self.logger.info("zk-service.yaml已生成。")
            self.command_list.append("kubectl apply -f %s" % zk_svc_file)

            zk_cm_file_j2 = '%s/templates/zookeeper/configMap.yaml.j2' % sys.path[0]
            zk_cm_file = '%s/zk-configMap.yaml' % self.zk_path
            if not j2_to_file("server", zk_conf, zk_cm_file_j2, zk_cm_file):
                self.logger.error("zk-configMap.yaml生成失败。")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:zk-configMap.yaml生成失败")
                abort(404)
            self.logger.info("zk-configMap.yaml已生成。")
            self.command_list.append("kubectl apply -f %s" % zk_cm_file)

            zk_sa_file_j2 = '%s/templates/zookeeper/serviceAccount.yaml.j2' % sys.path[0]
            zk_sa_file = '%s/zk-serviceAccount.yaml' % self.zk_path
            if j2_to_file("server", zk_conf, zk_sa_file_j2, zk_sa_file) == 1:
                self.logger.error("zk-serviceAccount.yaml生成失败")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:zk-serviceAccount.yaml生成失败")
                abort(404)
            self.logger.info("zk-serviceAccount.yaml已生成。")
            self.command_list.append("kubectl apply -f %s" % zk_sa_file)

            self.logger.info("生成appStart.sh")
            with open(self.zk_path + '/appStart.sh', "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n")
                """逐行执行部署命令"""
                for line in self.command_list:
                    f.write("%s\n" % line)
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "[INFO]：服务%s-%s下zookeeper资源清单yaml文件已生成生成" % (self.sys_name, self.app_name))
            send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                            "[FINISH]：服务%s-%s下zookeeper应用发布成功" % (self.sys_name, self.app_name))
