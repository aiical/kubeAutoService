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
            self.logger.info(volume_info_list)
            persistent_volume_info_list = []
            persistent_local_volume_info_list = []
            if volume_info_list:
                if announce_type == "permanent" and controller_type == "stateful":
                    local_volume_info_list = self.controller_info['volumeLocalInfoList']
                    for volume_info in local_volume_info_list:
                        tmp_volume_info = volume_info
                        tmp_name = volume_info['name']
                        v_local = volume_info['localPath']
                        for i in range(0, int(replicas)):
                            v_name = "%s-local-%s" % (tmp_name, str(i))
                            tmp_volume_info.update({
                                'name': v_name,
                                'localMkdir': v_local
                            })
                            persistent_local_volume_info_list.append(copy.deepcopy(tmp_volume_info))

                    for volume_info in volume_info_list:
                        tmp_share = volume_info['isNfsShare']
                        if int(replicas) == 1 and tmp_share == "0":
                            tmp_volume_info = volume_info
                            tmp_name = volume_info['name']
                            v_name = "%s-0" % tmp_name
                            tmp_volume_info.update({
                                'name': v_name,
                            })
                            persistent_volume_info_list.append(copy.deepcopy(tmp_volume_info))
                        else:
                            tmp_name = volume_info['name']
                            tmp_path = volume_info['path']
                            if tmp_path[-1] == "/":
                                tmp_path = tmp_path[:-1]
                            tmp_local = volume_info['localMkdir']
                            if tmp_local[-1] == "/":
                                tmp_local = tmp_local[:-1]
                            for i in range(0, int(replicas)):
                                tmp_volume_info = volume_info
                                v_name = "%s-%s" % (tmp_name, str(i))
                                # if tmp_share == "1":
                                v_path = "%s-%s" % (tmp_path, str(i))
                                v_local_mkdir = "%s-%s" % (tmp_local, str(i))
                                # else:
                                #     v_path = tmp_path
                                #     v_local_mkdir = tmp_local
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
                    self.logger.info("localMkdir:%s" % item['localMkdir'])
                    if not os.path.exists(item['localMkdir']):
                        os.makedirs(item['localMkdir'])

            self.logger.info("获取PersistentVolumeClaim信息完成")
            persistent_volume_info_list += persistent_local_volume_info_list
            self.logger.info(persistent_volume_info_list)
        except Exception:
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
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
