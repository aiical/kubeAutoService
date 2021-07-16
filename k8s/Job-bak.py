#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class Job:
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path
        """读取settings设置"""
        conf = settings_conf
        """仓库信息"""
        self.harbor_ip = conf['harborInfo']['host']
        # self.app_repository = "%s/app" % self.harbor_ip
        self.library_repository = "%s/library" % self.harbor_ip
        self.file_beat_version = str(conf['filebeatDefaults']['version'])

    def get_job_info(self):
        logger = Logger("server")
        logger.info("开始获取job信息")
        job_info = {}
        # run_env = self.global_info['runEnv']
        sys_name = self.global_info['sysName']
        app_name = self.global_info['appName']
        file_beat_flag = self.global_info['fileBeatFlag']
        sky_walking_flag = self.global_info['skyWalking']['flag']
        """获取tag"""
        image_full_name = self.global_info['imageFullName']
        # tag = self.global_info['tag']
        """获取replicas"""
        replicas = self.k8s_info['replicas']
        """获取nodeSelector"""
        ori_node_select_list = self.k8s_info['nodeSelector']
        new_node_select_list = []
        for selector in ori_node_select_list:
            str_selector = "%s: %s" % (selector["name"], selector["value"])
            new_node_select_list.append(str_selector)
        """获取服务名和名称空间"""
        # sys_name, service_name, namespace = set_run_env(run_env, sys_name, app_name)
        service_name, namespace = set_ns_svc(sys_name, app_name)
        """获取/etc/hosts信息"""
        host_info = self.k8s_info['hostInfo']
        """获取container信息"""
        container_info = self.k8s_info['container']
        port_info = container_info['portInfo']
        protocol = port_info['protocol']
        if protocol == "http":
            container_port = port_info['http']['portNum']
        elif protocol == "tcp":
            container_port = port_info['tcp']['portNum']
        else:
            container_port = 9999
        """获取资源限制信息"""
        resource_info = container_info['resource']
        cpu = resource_info['cpu']
        memory = resource_info['memory']
        ephemeral_storage = resource_info['ephemeral-storage']
        """获取环境变量信息"""
        if container_info.__contains__("env"):
            env_list = container_info['env']
        else:
            env_list = []
        """获取volume信息"""
        tmp_empty_dir_list = container_info['volume']['emptyDir']
        empty_dir_list = []
        if tmp_empty_dir_list is not None:
            for item in tmp_empty_dir_list:
                v_mount = item['mountPath']
                v_dir = v_mount.split('/')[-1].lower()
                v_name = "%s-%s" % (service_name, v_dir)
                empty_dir_list.append({
                    'name': v_name,
                    'mountPath': v_mount
                })

        tmp_host_path_list = container_info['volume']['hostPath']
        host_path_list = []
        if tmp_host_path_list is not None:
            for item in tmp_host_path_list:
                v_mount = item['mountPath']
                v_dir = v_mount.split('/')[-1].lower()
                v_name = "%s-%s" % (service_name, v_dir)
                v_local = item['localPath']
                host_path_list.append({
                    'name': v_name,
                    'mountPath': v_mount,
                    'localPath': v_local
                })

        tmp_nfs_list = container_info['volume']['nfs']
        nfs_list = []
        if tmp_nfs_list is not None:
            for item in tmp_nfs_list:
                v_mount = item['mountPath']
                v_dir = v_mount.split('/')[-1].lower()
                v_name = "%s-%s" % (service_name, v_dir)
                v_nfs_server = item['server']
                v_nfs_base_path = item['path']
                v_is_file_share = item['isFileShare']
                v_nfs_final_path = "%s/%s/%s/%s" % (v_nfs_base_path, sys_name, service_name, v_dir)
                v_nfs_final_path = v_nfs_final_path.replace("//", "/")
                nfs_list.append({
                    'name': v_name,
                    'mountPath': v_mount,
                    'server': v_nfs_server,
                    'path': v_nfs_final_path,
                    'isFileShare': v_is_file_share
                })

        tmp_config_map_list = container_info['volume']['configMap']
        config_map_list = []
        if tmp_config_map_list is not None:
            for item in tmp_config_map_list:
                v_mount = item['mountPath']
                v_file = item['file']
                tmp_name = ''.join(list(filter(str.isalnum, v_file))).lower()
                v_name = "%s-%s" % (service_name, tmp_name)
                v_key = item['key']
                v_md5_code = item['md5Code']
                config_map_list.append({
                    'name': v_name,
                    'mountPath': v_mount,
                    'file': v_file,
                    'key': v_key,
                    'md5Code': v_md5_code
                })
        volume_count = len(empty_dir_list) + len(host_path_list) + len(nfs_list) + len(config_map_list)
        volume_info = {
            'volumeCount': int(volume_count),
            'emptyDir': empty_dir_list,
            'hostPath': host_path_list,
            'nfs': nfs_list,
            'configMap': config_map_list,
        }
        # """获取就绪检查信息"""
        # readiness = container_info['readinessProbe']
        # """获取存活检查信息"""
        # liveness = container_info['livenessProbe']
        # """获取容器生命周期信息，包括启动后钩子和销毁前钩子"""
        # lifecycle = container_info['lifecycle']
        """合并job部署config字典"""
        job_info.update({
            'fileBeatFlag': file_beat_flag,
            'filebeatVersion': self.file_beat_version,
            'serviceName': service_name,
            'namespace': namespace,
            'imageFullName': image_full_name,
            'replicas': replicas,
            'nodeSelectorList': new_node_select_list,
            'hostInfo': host_info,
            # 'appRepository': self.app_repository,
            'libraryRepository': self.library_repository,
            # 'tag': tag,
            'containerPort': container_port,
            'cpu': cpu,
            'memory': memory,
            'ephemeralStorage': ephemeral_storage,
            'envList': env_list,
            'volumeInfo': volume_info,
            # 'readiness': readiness,
            # 'liveness': liveness,
            # 'lifecycle': lifecycle,
            'skyWalkingFlag': sky_walking_flag,
        })
        logger.info("获取job信息完成")
        return job_info

    def create_job_yaml(self, job_info):
        logger = Logger("server")
        logger.info("开始创建job.yaml")
        logger.info("job配置如下：")
        logger.info(job_info)
        job_yaml_j2 = '%s/templates/k8s/job.yaml.j2' % sys.path[0]
        job_yaml = '%s/job.yaml' % self.k8s_path

        j2_to_file("server", job_info, job_yaml_j2, job_yaml)
        logger.info("job.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % job_yaml]
        return apply_command_list
