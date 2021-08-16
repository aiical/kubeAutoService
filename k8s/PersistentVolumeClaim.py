#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import sys
import copy
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, send_state_back


class PersistentVolumeClaim:
    def __init__(self, global_info, controller_info, k8s_path):
        self.logger = Logger("server")
        self.global_info = global_info
        self.controller_info = controller_info
        self.k8s_path = k8s_path
        try:
            self.task_back_url = global_info['taskBackUrl']
            self.task_flow_id = global_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)

    def get_persistent_volume_claim_info(self):
        self.logger.info("开始获取PersistentVolumeClaim信息")
        try:
            replicas = self.controller_info['replicas']
            controller_type = self.controller_info['controllerType']
            announce_type = self.controller_info['announceType']
            volume_info_list = self.controller_info['volumeNfsInfoList']
            persistent_volume_info_list = []
            persistent_local_volume_info_list = []
            if volume_info_list:
                if announce_type == "permanent" and controller_type == "stateful":
                    local_volume_info_list = self.controller_info['volumeLocalInfoList']
                    for volume_info in local_volume_info_list:
                        for i in range(0, int(replicas)):
                            tmp_volume_info = volume_info
                            v_name = "%s-local-%s" % (volume_info['name'], str(i))
                            tmp_volume_info.update({
                                'name': v_name,
                                'localMkdir': volume_info['localPath']
                            })
                            persistent_local_volume_info_list.append(copy.deepcopy(tmp_volume_info))

                    for volume_info in volume_info_list:
                        if int(replicas) == 1 and volume_info['isNfsShare'] == "N":
                            persistent_volume_info_list.append(copy.deepcopy(volume_info))
                        else:
                            for i in range(0, int(replicas)):
                                tmp_volume_info = volume_info
                                v_name = "%s-%s" % (volume_info['name'], str(i))
                                v_path = "%s-%s" % (volume_info['path'], str(i))
                                v_local_mkdir = "%s-%s" % (volume_info['localMkdir'], str(i))
                                tmp_volume_info.update({
                                    'name': v_name,
                                    'path': v_path,
                                    'localMkdir': v_local_mkdir
                                })
                                persistent_volume_info_list.append(copy.deepcopy(tmp_volume_info))
                else:
                    for volume_info in volume_info_list:
                        persistent_volume_info_list.append(copy.deepcopy(volume_info))
                for item in persistent_volume_info_list:
                    if not os.path.exists(item['localMkdir']):
                        os.makedirs(item['localMkdir'])
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.logger.info("获取PersistentVolumeClaim信息完成")
            persistent_volume_info_list = persistent_volume_info_list.extend(persistent_local_volume_info_list)
            return persistent_volume_info_list

    def create_persistent_volume_claim_yaml(self, persistent_volume_info):
        self.logger.info("开始创建PersistentVolumeClaim.yaml")
        self.logger.info("PersistentVolumeClaim配置如下：")
        self.logger.info(persistent_volume_info)
        try:
            pvc_name = persistent_volume_info['name']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            pvc_yaml_j2 = '%s/templates/k8s/persistentVolumeClaim.yaml.j2' % sys.path[0]
            pvc_yaml = '%s/pvc-%s.yaml' % (self.k8s_path, pvc_name)

            if not j2_to_file("server", persistent_volume_info, pvc_yaml_j2, pvc_yaml):
                self.logger.error("pvc-%s.yaml生成失败" % pvc_name)
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]:pvc-%s.yaml生成失败" % pvc_name)
                abort(404)
            self.logger.info("pvc-%s.yaml已生成" % pvc_name)
            apply_command_list = ["kubectl apply -f %s" % pvc_yaml]
            return apply_command_list
