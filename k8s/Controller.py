#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import copy
import traceback
from flask import abort
from k8s.PersistentVolumeClaim import PersistentVolumeClaim
from publicClass.Logger import Logger
from publicClass.PublicFunc import compared_version, set_ns_svc, send_state_back


class Controller:
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        self.logger = Logger("server")
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path
        self.controller_info = {}
        try:
            self.task_back_url = self.global_info['taskBackUrl']
            self.task_flow_id = self.global_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)
        else:
            try:
                self.sys_name = self.global_info['sysName']
                self.app_name = self.global_info['appName']
                self.service_name, self.namespace = set_ns_svc(self.sys_name, self.app_name)
                self.container_info = self.k8s_info['container']
                self.harbor_ip = settings_conf['harborInfo']['host']
                self.library_repository = "%s/library" % self.harbor_ip
                self.file_beat_flag = self.global_info['fileBeatFlag']
                self.file_beat_version = str(settings_conf['fileBeatDefaults']['version'])
                self.log_stash_host = settings_conf['fileBeatDefaults']['logStashHost']
                self.sky_walking_host = str(settings_conf['skyWalkingDefaults']['host'])
                self.sky_walking_flag = self.global_info['skyWalking']['flag']
                if self.sky_walking_flag == "Y":
                    self.sky_walking_home = self.global_info['skyWalkingHome']
                else:
                    self.sky_walking_home = ""
                self.log_kafka_info = settings_conf['fileBeatDefaults']['kafkaInfo']
            except(KeyError, NameError):
                self.logger.error(traceback.format_exc())
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：%s" % traceback.format_exc())
                abort(404)

    def get_controller_share_info(self):
        try:
            announce_type = self.k8s_info['announceType']
            controller_type = self.k8s_info['controllerType']
            """获取tag"""
            image_full_name = self.global_info['imageFullName']
            """获取replicas"""
            replicas = self.k8s_info['replicas']
            """获取nodeSelector"""
            ori_node_select_list = self.k8s_info['nodeSelector']
            new_node_select_list = []
            if ori_node_select_list:
                for selector in ori_node_select_list:
                    str_selector = "%s: %s" % (selector["name"], selector["value"])
                    new_node_select_list.append(str_selector)
            """获取/etc/hosts信息"""
            host_info = self.k8s_info['hostInfo']
            port_info = self.container_info['portInfo']
            protocol = port_info['protocol']
            if protocol == "http":
                container_port = port_info['protocolContent']['portNum']
            elif protocol == "tcp":
                container_port = port_info['protocolContent']['portNum']
            else:
                container_port = 9999
            """获取资源限制信息"""
            resource_info = self.container_info['resource']
            cpu = resource_info['cpu']
            memory = resource_info['memory']
            ephemeral_storage = resource_info['ephemeral-storage']
            """获取环境变量信息"""
            if self.container_info.__contains__("env"):
                env_list = self.container_info['env']
            else:
                env_list = []
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.controller_info.update({
                'fileBeatFlag': self.file_beat_flag,
                'fileBeatVersion': self.file_beat_version,
                'skyWalkingFlag': self.sky_walking_flag,
                'skyWalkingHome': self.sky_walking_home,
                'serviceName': self.service_name,
                'namespace': self.namespace,
                'imageFullName': image_full_name,
                'replicas': replicas,
                'controllerType': controller_type,
                'announceType': announce_type,
                'nodeSelectorList': new_node_select_list,
                'hostInfo': host_info,
                'libraryRepository': self.library_repository,
                'containerPort': container_port,
                'cpu': cpu,
                'memory': memory,
                'ephemeralStorage': ephemeral_storage,
                'envList': env_list,
            })

    def get_pod_live_info(self):
        try:
            """获取就绪检查信息"""
            health_check_info = self.container_info['healthCheck']
            startup = health_check_info['startupProbe']
            readiness = health_check_info['readinessProbe']
            liveness = health_check_info['livenessProbe']
            """获取容器生命周期信息，包括启动后钩子和销毁前钩子"""
            lifecycle = self.container_info['lifecycle']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.controller_info.update({
                'startup': startup,
                'readiness': readiness,
                'liveness': liveness,
                'lifecycle': lifecycle,
            })

    def get_volume_info(self):
        try:
            """获取volume信息"""
            volume_dir_nfs_info_list = []
            volume_dir_local_info_list = []
            volume_file_info_list = []
            local_volume_list = self.container_info['volume']['hostPath']
            nfs_volume_list = self.container_info['volume']['nfs']
            config_volume_list = self.container_info['volume']['configMap']
            controller_type = self.k8s_info['controllerType']
            if local_volume_list:
                for volume in local_volume_list:
                    v_mount = volume['mountPath']
                    if v_mount[-1] == "/":
                        v_mount = v_mount[:-1]
                    v_size = volume['pvcSize']
                    v_dir = v_mount[1:].replace("/", "-").replace("_", "-").lower()
                    v_name = "%s-%s" % (self.service_name, v_dir)
                    v_claim_name = "pvc-%s" % v_dir
                    v_local = volume['localPath']
                    volume_dir_local_info_list.append(copy.deepcopy(
                        {
                            'type': "dir-local",
                            'name': v_name,
                            'claimName': v_claim_name,
                            'size': v_size,
                            'mountPath': v_mount,
                            'localPath': v_local,
                            'controller': controller_type,
                            'serviceName': self.service_name,
                        }
                    ))
            if config_volume_list:
                for volume in config_volume_list:
                    v_mount = volume['mountPath']
                    v_file = volume['fileName']
                    tmp_name = ''.join(list(filter(str.isalnum, v_file))).lower()
                    v_name = "%s-%s" % (self.service_name, tmp_name)
                    v_key = volume['key']
                    v_md5_code = volume['md5Code']
                    volume_file_info_list.append(copy.deepcopy(
                        {
                            'type': "file",
                            'name': v_name,
                            'mountPath': v_mount,
                            'file': v_file,
                            'key': v_key,
                            'md5Code': v_md5_code
                        }
                    ))
            if nfs_volume_list:
                for volume in nfs_volume_list:
                    v_mount = volume['mountPath']
                    if v_mount[-1] == "/":
                        v_mount = v_mount[:-1]
                    v_dir = v_mount[1:].replace("/", "-").replace("_", "-").lower()
                    v_name = "%s-%s" % (self.service_name, v_dir)
                    v_claim_name = "pvc-%s" % v_dir
                    v_nfs_server = volume['server']
                    v_nfs_base_path = volume['path']
                    v_size = volume['pvcSize']
                    v_local_mount_path = volume['nodePath']
                    v_is_file_share = volume['isFileShare']
                    v_is_nfs_share = volume['isNfsShare']
                    if v_is_nfs_share == "1":
                        v_nfs_final_path = "%s/%s/%s/%s" % (
                            v_nfs_base_path, self.sys_name, self.service_name, v_dir)
                        v_local_need_mkdir_path = "%s/%s/%s/%s" % (
                            v_local_mount_path, self.sys_name, self.service_name, v_dir)
                        v_local_need_mkdir_path = v_local_need_mkdir_path.replace("//", "/")
                        # if not os.path.exists(v_local_need_mkdir_path):
                        #     os.makedirs(v_local_need_mkdir_path)
                    else:
                        v_local_need_mkdir_path = v_nfs_base_path
                        v_nfs_final_path = v_nfs_base_path
                    v_nfs_final_path = v_nfs_final_path.replace("//", "/")
                    volume_dir_nfs_info_list.append(copy.deepcopy(
                        {
                            'type': "dir-nfs",
                            'name': v_name,
                            'claimName': v_claim_name,
                            'serviceName': self.service_name,
                            'namespace': self.namespace,
                            'size': v_size,
                            'mountPath': v_mount,
                            'server': v_nfs_server,
                            'path': v_nfs_final_path,
                            'isFileShare': v_is_file_share,
                            'isNfsShare': v_is_nfs_share,
                            'localMkdir': v_local_need_mkdir_path,
                            'controller': controller_type
                        }
                    ))

            self.controller_info.update({
                'volumeLocalInfoList': volume_dir_local_info_list,
                'volumeNfsInfoList': volume_dir_nfs_info_list,
                'configMapList': volume_file_info_list
            })
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)

    def get_if_istio_ip(self):
        try:
            tmp_server_type = self.k8s_info['serverType']['type']

            if not tmp_server_type:
                server_type = "istio"
            else:
                server_type = tmp_server_type
            self.controller_info.update({
                'serverType': server_type
            })
            if server_type == "istio":
                istio_info = self.k8s_info["serverType"]['istio']
                user_set_istio_white_ip_list = istio_info["whiteIpList"]
                etc_host_ip = self.k8s_info['hostInfo']
                str_istio_white_ip = ""
                tmp_total_istio_white_ip_list = []
                if user_set_istio_white_ip_list is not None:
                    tmp_total_istio_white_ip_list.extend(user_set_istio_white_ip_list)
                    # for ip in istio_white_ip_list:
                    #     str_istio_white_ip += "%s/32," % str(ip)
                if etc_host_ip:
                    for item in etc_host_ip:
                        tmp_total_istio_white_ip_list.append(copy.deepcopy(item['ip']))
                        # str_istio_white_ip += "%s/32," % item['ip']
                if self.sky_walking_flag == "Y":
                    tmp_total_istio_white_ip_list.append(self.sky_walking_host)
                    # str_istio_white_ip += "%s/32," % self.sky_walking_host
                if self.file_beat_flag == "Y":
                    if compared_version(self.file_beat_version, "7.9.2") == -1:
                        for item in self.log_stash_host:
                            tmp_total_istio_white_ip_list.append(copy.deepcopy(str(item["host"])))
                            # str_istio_white_ip += "%s/32," % str(item["host"])
                    else:
                        for item in self.log_kafka_info:
                            tmp_total_istio_white_ip_list.append(copy.deepcopy(str(item["host"])))
                            # str_istio_white_ip += "%s/32," % str(item["host"])

                total_istio_white_ip_list = list(set(tmp_total_istio_white_ip_list))
                if total_istio_white_ip_list:
                    for ip in total_istio_white_ip_list:
                        str_istio_white_ip += "%s/32," % ip
                if str_istio_white_ip != "":
                    str_istio_white_ip = str_istio_white_ip[:-1]
                self.controller_info.update({
                    "istioWhiteIp": str_istio_white_ip
                })
        except(KeyError, NameError, ValueError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)

    def get_cron_job_schedule(self):
        try:
            """获取schedule"""
            schedule = self.k8s_info['schedule']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            self.controller_info.update({
                'schedule': schedule,
            })

    def create_pvc_yaml(self):
        apply_command_list = []
        pvc = PersistentVolumeClaim(self.global_info, self.controller_info, self.k8s_path)
        pvc_info_list = pvc.get_persistent_volume_claim_info()
        for pvc_info in pvc_info_list:
            self.logger.info(pvc_info)
            tmp_command_list = pvc.create_persistent_volume_claim_yaml(pvc_info)
            apply_command_list.extend(tmp_command_list)
        return apply_command_list
