#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import copy
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class Deployment:
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        logger = Logger("server")
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path
        """读取settings设置"""
        conf = settings_conf
        """仓库信息"""
        try:
            self.harbor_ip = conf['harborInfo']['host']
            self.library_repository = "%s/library" % self.harbor_ip
            self.file_beat_version = str(conf['filebeatDefaults']['version'])
            self.log_stash_host = conf['filebeatDefaults']['logstashHost']
            self.sky_walking_host = str(conf['skyWalkingDefaults']['host'])
            self.log_kafka_info = settings_conf['filebeatDefaults']['kafkaInfo']
        except Exception:
            logger.error(traceback.format_exc())

    def get_deployment_info(self):
        deployment_info = {}
        logger = Logger("server")
        try:
            logger.info("开始获取deployment信息")
            run_env = self.global_info['runEnv']
            sys_name = self.global_info['sysName']
            app_name = self.global_info['appName']
            file_beat_flag = self.global_info['fileBeatFlag']
            sky_walking_flag = self.global_info['skyWalking']['flag']
            """获取tag"""
            image_full_name = self.global_info['imageFullName']
            # if_dubbo = self.global_info['ifDubbo']['flag']
            # dubbo_port = ""
            # if if_dubbo == "Y":
            #     dubbo_port = str(self.global_info['ifDubbo']['port'])
            # tag = self.global_info['tag']
            """获取replicas"""
            replicas = self.k8s_info['replicas']
            """获取版本个数"""
            version_count = int(self.k8s_info['versionCount'])
            """获取nodeSelector"""
            ori_node_select_list = self.k8s_info['nodeSelector']
            new_node_select_list = []
            if ori_node_select_list:
                for selector in ori_node_select_list:
                    str_selector = "%s: %s" % (selector["name"], selector["value"])
                    new_node_select_list.append(str_selector)
            """获取服务名和名称空间"""
            # sys_name, service_name, namespace = set_run_env(run_env, sys_name, app_name)
            service_name, namespace = set_ns_svc(sys_name, app_name)
            logger.info("testdeploy")
            """获取/etc/hosts信息"""
            host_info = self.k8s_info['hostInfo']
            """获取container信息"""
            container_info = self.k8s_info['container']
            port_info = container_info['portInfo']
            protocol = port_info['protocol']
            if protocol == "http":
                container_port = port_info['protocolContent']['portNum']
            elif protocol == "tcp":
                container_port = port_info['protocolContent']['portNum']
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
                    v_file = item['fileName']
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

            """获取就绪检查信息"""
            health_check_info = container_info['healthCheck']
            startup = health_check_info['startupProbe']
            readiness = health_check_info['readinessProbe']
            liveness = health_check_info['livenessProbe']
            """获取容器生命周期信息，包括启动后钩子和销毁前钩子"""
            lifecycle = container_info['lifecycle']
            """合并deployment部署config字典"""
            deployment_info.update({
                'fileBeatFlag': file_beat_flag,
                'filebeatVersion': self.file_beat_version,
                'serviceName': service_name,
                'namespace': namespace,
                'imageFullName': image_full_name,
                'replicas': replicas,
                'nodeSelectorList': new_node_select_list,
                'hostInfo': host_info,
                'libraryRepository': self.library_repository,
                # 'dubboPort': dubbo_port,
                'containerPort': container_port,
                'cpu': cpu,
                'memory': memory,
                'ephemeralStorage': ephemeral_storage,
                'envList': env_list,
                'volumeInfo': volume_info,
                'startup': startup,
                'readiness': readiness,
                'liveness': liveness,
                'lifecycle': lifecycle,
                'skyWalkingFlag': sky_walking_flag,
            })

            """若应用过istio，则加入istio白名单配置"""
            tmp_server_type = self.k8s_info['serverType']['type']
            if not tmp_server_type:
                server_type = "istio"
            else:
                server_type = tmp_server_type
            deployment_info.update({
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
                if sky_walking_flag == "Y":
                    str_istio_white_ip += "%s/32," % self.sky_walking_host
                if file_beat_flag == "Y":
                    # for ip in self.log_stash_host:
                    #     str_istio_white_ip += "%s/32," % str(ip)
                    for item in self.log_kafka_info:
                        str_istio_white_ip += "%s/32," % str(item["host"])
                if str_istio_white_ip != "":
                    str_istio_white_ip = str_istio_white_ip[:-1]

                deployment_info.update({
                    "istioWhiteIp": str_istio_white_ip
                })
            deployment_list = []
            cnt_range = int(version_count + 1)
            for i in range(1, cnt_range):
                version = "v%s" % str(i)
                deployment_info.update({
                    'version': version
                })
                """此处对列表中的某个字典做update，会导致所有字典的值都被覆盖，需要用到copy模块的深拷贝来解决copy.deepcopy"""
                deployment_list.append(copy.deepcopy(deployment_info))
            logger.info("获取deployment信息完成")
            return deployment_list
        except Exception:
            logger.error(traceback.format_exc())

    def create_deployment_yaml(self, deployment_list):
        logger = Logger("server")
        apply_command_list = []
        for deployment_info in deployment_list:
            version = deployment_info["version"]
            server_type = deployment_info['serverType']
            logger.info("开始创建deployment-%s.yaml" % version)
            logger.info("deployment-%s配置如下：" % version)
            logger.info(deployment_info)
            deployment_yaml_j2 = '%s/templates/k8s/deployment.yaml.j2' % sys.path[0]
            deployment_yaml = '%s/deployment-%s.yaml' % (self.k8s_path, version)
            j2_to_file("server", deployment_info, deployment_yaml_j2, deployment_yaml)
            logger.info("deployment-%s.yaml已生成。" % version)
            if server_type == "istio":
                command = "istioctl kube-inject -f %s | kubectl apply -f -" % deployment_yaml
            else:
                command = "kubectl apply -f %s" % deployment_yaml
            apply_command_list.append(command)
        return apply_command_list
