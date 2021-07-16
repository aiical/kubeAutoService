#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import compared_version, set_ns_svc


class Controller:
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        self.logger = Logger("server")
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path
        self.controller_info = {}
        try:
            self.sys_name = self.global_info['sysName']
            self.app_name = self.global_info['appName']
            self.service_name, self.namespace = set_ns_svc(self.sys_name, self.app_name)
            self.container_info = self.k8s_info['container']
            self.harbor_ip = settings_conf['harborInfo']['host']
            self.library_repository = "%s/library" % self.harbor_ip
            self.file_beat_flag = self.global_info['fileBeatFlag']
            self.file_beat_version = str(settings_conf['filebeatDefaults']['version'])
            self.log_stash_host = settings_conf['filebeatDefaults']['logstashHost']
            self.sky_walking_host = str(settings_conf['skyWalkingDefaults']['host'])
            self.sky_walking_flag = self.global_info['skyWalking']['flag']
            self.log_kafka_info = settings_conf['filebeatDefaults']['kafkaInfo']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())

    def get_controller_share_info(self):
        try:
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
        else:
            self.controller_info.update({
                'fileBeatFlag': self.file_beat_flag,
                'filebeatVersion': self.file_beat_version,
                'skyWalkingFlag': self.sky_walking_flag,
                'serviceName': self.service_name,
                'namespace': self.namespace,
                'imageFullName': image_full_name,
                'replicas': replicas,
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
        else:
            self.controller_info.update({
                'startup': startup,
                'readiness': readiness,
                'liveness': liveness,
                'lifecycle': lifecycle,
            })

    def get_volume_info(self, controller_type):
        try:
            """获取volume信息"""
            tmp_empty_dir_list = self.container_info['volume']['emptyDir']
            empty_dir_list = []
            if tmp_empty_dir_list is not None:
                for item in tmp_empty_dir_list:
                    v_mount = item['mountPath']
                    v_dir = v_mount.split('/')[-1].lower()
                    v_name = "%s-%s" % (self.service_name, v_dir)
                    empty_dir_list.append({
                        'name': v_name,
                        'mountPath': v_mount
                    })

            tmp_host_path_list = self.container_info['volume']['hostPath']
            host_path_list = []
            if tmp_host_path_list is not None:
                for item in tmp_host_path_list:
                    v_mount = item['mountPath']
                    v_dir = v_mount.split('/')[-1].lower()
                    v_name = "%s-%s" % (self.service_name, v_dir)
                    v_local = item['localPath']
                    host_path_list.append({
                        'name': v_name,
                        'mountPath': v_mount,
                        'localPath': v_local
                    })

            tmp_config_map_list = self.container_info['volume']['configMap']
            config_map_list = []
            if tmp_config_map_list is not None:
                for item in tmp_config_map_list:
                    v_mount = item['mountPath']
                    v_file = item['fileName']
                    tmp_name = ''.join(list(filter(str.isalnum, v_file))).lower()
                    v_name = "%s-%s" % (self.service_name, tmp_name)
                    v_key = item['key']
                    v_md5_code = item['md5Code']
                    config_map_list.append({
                        'name': v_name,
                        'mountPath': v_mount,
                        'file': v_file,
                        'key': v_key,
                        'md5Code': v_md5_code
                    })

            pvc_list = []
            nfs_list = []
            if controller_type == "stateful":
                tmp_pvc_list = self.container_info['volume']['pvc']
                if tmp_pvc_list is not None:
                    for item in tmp_pvc_list:
                        v_mount = item['mountPath']
                        v_dir = v_mount.split('/')[-1].lower()
                        v_name = "%s-%s" % (self.service_name, v_dir)
                        v_access_modes = item['accessModes']
                        v_size = item['size']
                        v_storage_class_name = item['storageClassName']
                        pvc_list.append({
                            'name': v_name,
                            'mountPath': v_mount,
                            'accessModes': v_access_modes,
                            'size': v_size,
                            'storageClassName': v_storage_class_name
                        })
                mount_count = len(empty_dir_list) + len(host_path_list) + len(pvc_list) + len(config_map_list)
                volume_count = len(empty_dir_list) + len(host_path_list) + len(config_map_list)
                volume_info = {
                    'mountCount': int(mount_count),
                    'volumeCount': int(volume_count),
                    'emptyDir': empty_dir_list,
                    'hostPath': host_path_list,
                    'pvc': pvc_list,
                    'configMap': config_map_list,
                }
            else:
                tmp_nfs_list = self.container_info['volume']['nfs']

                if tmp_nfs_list is not None:
                    for item in tmp_nfs_list:
                        v_mount = item['mountPath']
                        v_dir = v_mount.split('/')[-1].lower()
                        v_name = "%s-%s" % (self.service_name, v_dir)
                        v_nfs_server = item['server']
                        v_nfs_base_path = item['path']
                        v_is_file_share = item['isFileShare']
                        v_nfs_final_path = "%s/%s/%s/%s" % (v_nfs_base_path, self.sys_name, self.service_name, v_dir)
                        v_nfs_final_path = v_nfs_final_path.replace("//", "/")
                        nfs_list.append({
                            'name': v_name,
                            'mountPath': v_mount,
                            'server': v_nfs_server,
                            'path': v_nfs_final_path,
                            'isFileShare': v_is_file_share
                        })

                volume_count = len(empty_dir_list) + len(host_path_list) + len(nfs_list) + len(config_map_list)
                volume_info = {
                    'volumeCount': int(volume_count),
                    'emptyDir': empty_dir_list,
                    'hostPath': host_path_list,
                    'nfs': nfs_list,
                    'configMap': config_map_list,
                }
            self.controller_info.update({
                'volumeInfo': volume_info,
            })
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())

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
                istio_white_ip_list = istio_info["whiteIpList"]
                etc_host_ip = self.k8s_info['hostInfo']
                str_istio_white_ip = ""
                if istio_white_ip_list is not None:
                    for ip in istio_white_ip_list:
                        str_istio_white_ip += "%s/32," % str(ip)
                if etc_host_ip:
                    for item in etc_host_ip:
                        str_istio_white_ip += "%s/32," % item['ip']
                if self.sky_walking_flag == "Y":
                    str_istio_white_ip += "%s/32," % self.sky_walking_host
                if self.file_beat_flag == "Y":
                    if compared_version(self.file_beat_flag, "7.9.2") == -1:
                        for item in self.log_stash_host:
                            str_istio_white_ip += "%s/32," % str(item["host"])
                    else:
                        for item in self.log_kafka_info:
                            str_istio_white_ip += "%s/32," % str(item["host"])
                if str_istio_white_ip != "":
                    str_istio_white_ip = str_istio_white_ip[:-1]
                self.controller_info.update({
                    "istioWhiteIp": str_istio_white_ip
                })
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())

    def get_cron_job_schedule(self):
        try:
            """获取schedule"""
            schedule = self.k8s_info['schedule']
            self.controller_info.update({
                'schedule': schedule,
            })
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
