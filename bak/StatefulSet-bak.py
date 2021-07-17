# #!/usr/local/python374/bin/python3.7
# # -*- coding: utf-8 -*-
# import sys
# from publicClass.Logger import Logger
# from publicClass.PublicFunc import j2_to_file, set_ns_svc
#
#
# class StatefulSet:
#     def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
#         self.global_info = global_info
#         self.k8s_info = k8s_info
#         self.k8s_path = k8s_path
#         """读取settings设置"""
#         conf = settings_conf
#         """仓库信息"""
#         self.harbor_ip = conf['harborInfo']['host']
#         self.library_repository = "%s/library" % self.harbor_ip
#         self.file_beat_version = str(conf['fileBeatDefaults']['version'])
#         self.log_stash_host = conf['fileBeatDefaults']['logStashHost']
#         self.sky_walking_host = conf['skyWalkingDefaults']['host']
#         self.log_kafka_info = settings_conf['fileBeatDefaults']['kafkaInfo']
#
#     def get_statefulset_info(self):
#         logger = Logger("server")
#         logger.info("开始获取statefulset信息")
#         statefulset_info = {}
#         # run_env = self.global_info['runEnv']
#         sys_name = self.global_info['sysName']
#         app_name = self.global_info['appName']
#         file_beat_flag = self.global_info['fileBeatFlag']
#         sky_walking_flag = self.global_info['skyWalking']['flag']
#         """获取tag"""
#         image_full_name = self.global_info['imageFullName']
#         # if_dubbo = self.global_info['ifDubbo']['flag']
#         # dubbo_port = ""
#         # if if_dubbo == "Y":
#         #     dubbo_port = str(self.global_info['ifDubbo']['port'])
#         # tag = self.global_info['tag']
#         """获取replicas"""
#         replicas = self.k8s_info['replicas']
#         """获取nodeSelector"""
#         ori_node_select_list = self.k8s_info['nodeSelector']
#         new_node_select_list = []
#         for selector in ori_node_select_list:
#             str_selector = "%s: %s" % (selector["name"], selector["value"])
#             new_node_select_list.append(str_selector)
#         """获取服务名和名称空间"""
#         service_name, namespace = set_ns_svc(sys_name, app_name)
#         """获取/etc/hosts信息"""
#         host_info = self.k8s_info['hostInfo']
#         """获取container信息"""
#         container_info = self.k8s_info['container']
#         port_info = container_info['portInfo']
#         protocol = port_info['protocol']
#         if protocol == "http":
#             container_port = port_info['protocolContent']['portNum']
#         elif protocol == "tcp":
#             container_port = port_info['protocolContent']['portNum']
#         else:
#             container_port = 9999
#         """获取资源限制信息"""
#         resource_info = container_info['resource']
#         cpu = resource_info['cpu']
#         memory = resource_info['memory']
#         ephemeral_storage = resource_info['ephemeral-storage']
#         """获取环境变量信息"""
#         if container_info.__contains__("env"):
#             env_list = container_info['env']
#         else:
#             env_list = []
#         """获取volume信息"""
#
#         tmp_empty_dir_list = container_info['volume']['emptyDir']
#         empty_dir_list = []
#         if tmp_empty_dir_list is not None:
#             for item in tmp_empty_dir_list:
#                 v_mount = item['mountPath']
#                 v_dir = v_mount.split('/')[-1].lower()
#                 v_name = "%s-%s" % (service_name, v_dir)
#                 empty_dir_list.append({
#                     'name': v_name,
#                     'mountPath': v_mount
#                 })
#
#         tmp_host_path_list = container_info['volume']['hostPath']
#         host_path_list = []
#         if tmp_host_path_list is not None:
#             for item in tmp_host_path_list:
#                 v_mount = item['mountPath']
#                 v_dir = v_mount.split('/')[-1].lower()
#                 v_name = "%s-%s" % (service_name, v_dir)
#                 v_local = item['localPath']
#                 host_path_list.append({
#                     'name': v_name,
#                     'mountPath': v_mount,
#                     'localPath': v_local
#                 })
#
#         tmp_pvc_list = container_info['volume']['pvc']
#         pvc_list = []
#         if tmp_pvc_list is not None:
#             for item in tmp_pvc_list:
#                 v_mount = item['mountPath']
#                 v_dir = v_mount.split('/')[-1].lower()
#                 v_name = "%s-%s" % (service_name, v_dir)
#                 v_access_modes= item['accessModes']
#                 v_size = item['size']
#                 v_storage_class_name = item['storageClassName']
#                 pvc_list.append({
#                     'name': v_name,
#                     'mountPath': v_mount,
#                     'accessModes': v_access_modes,
#                     'size': v_size,
#                     'storageClassName': v_storage_class_name
#                 })
#
#         tmp_config_map_list = container_info['volume']['configMap']
#         config_map_list = []
#         if tmp_config_map_list is not None:
#             for item in tmp_config_map_list:
#                 v_mount = item['mountPath']
#                 v_file = item['file']
#                 tmp_name = ''.join(list(filter(str.isalnum, v_file))).lower()
#                 v_name = "%s-%s" % (service_name, tmp_name)
#                 v_key = item['key']
#                 v_md5_code = item['md5Code']
#                 config_map_list.append({
#                     'name': v_name,
#                     'mountPath': v_mount,
#                     'file': v_file,
#                     'key': v_key,
#                     'md5Code': v_md5_code
#                 })
#
#         mount_count = len(empty_dir_list) + len(host_path_list) + len(pvc_list) + len(config_map_list)
#         volume_count = len(empty_dir_list) + len(host_path_list) + len(config_map_list)
#         volume_info = {
#             'mountCount': int(mount_count),
#             'volumeCount': int(volume_count),
#             'emptyDir': empty_dir_list,
#             'hostPath': host_path_list,
#             'pvc': pvc_list,
#             'configMap': config_map_list,
#         }
#         """获取就绪检查信息"""
#         health_check_info = container_info['healthCheck']
#         startup = health_check_info['startupProbe']
#         readiness = health_check_info['readinessProbe']
#         liveness = health_check_info['livenessProbe']
#         """获取容器生命周期信息，包括启动后钩子和销毁前钩子"""
#         lifecycle = container_info['lifecycle']
#         """合并deployment部署config字典"""
#         statefulset_info.update({
#             'fileBeatFlag': file_beat_flag,
#             'fileBeatVersion': self.file_beat_version,
#             'serviceName': service_name,
#             'namespace': namespace,
#             'imageFullName': image_full_name,
#             'replicas': replicas,
#             'nodeSelectorList': new_node_select_list,
#             'hostInfo': host_info,
#             'libraryRepository': self.library_repository,
#             # 'dubboPort': dubbo_port,
#             'containerPort': container_port,
#             'cpu': cpu,
#             'memory': memory,
#             'ephemeralStorage': ephemeral_storage,
#             'envList': env_list,
#             'volumeInfo': volume_info,
#             'startup': startup,
#             'readiness': readiness,
#             'liveness': liveness,
#             'lifecycle': lifecycle,
#             'skyWalkingFlag': sky_walking_flag,
#         })
#         """若应用过istio，则加入istio白名单配置"""
#         tmp_server_type = self.k8s_info['serverType']['type']
#         if not tmp_server_type:
#             server_type = "istio"
#         else:
#             server_type = tmp_server_type
#         statefulset_info.update({
#             'serverType': server_type
#         })
#         if server_type == "istio":
#             istio_info = self.k8s_info["serverType"]['istio']
#             istio_white_ip_list = istio_info["whiteIpList"]
#             etc_host_ip = self.k8s_info['hostInfo']
#             str_istio_white_ip = ""
#             for ip in istio_white_ip_list:
#                 str_istio_white_ip += "%s/32," % str(ip)
#             if etc_host_ip:
#                 for item in etc_host_ip:
#                     str_istio_white_ip += "%s/32," % item['ip']
#             if sky_walking_flag == "Y":
#                 str_istio_white_ip += "%s/32," % self.sky_walking_host
#             if file_beat_flag == "Y":
#                 # for ip in self.log_stash_host:
#                 #     str_istio_white_ip += "%s/32," % str(ip)
#                 for item in self.log_kafka_info:
#                     str_istio_white_ip += "%s/32," % str(item["host"])
#             if str_istio_white_ip != "":
#                 str_istio_white_ip = str_istio_white_ip[:-1]
#             statefulset_info.update({
#                 "istioWhiteIp": str_istio_white_ip
#             })
#         logger.info("获取statefulset信息完成")
#         return statefulset_info
#
#     def create_statefulset_yaml(self, statefulset_info):
#         logger = Logger("server")
#         apply_command_list = []
#         server_type = statefulset_info['serverType']
#         logger.info("开始创建statefulset.yaml")
#         logger.info("statefulset配置如下：")
#         logger.info(statefulset_info)
#         statefulset_yaml_j2 = '%s/templates/k8s/statefulset.yaml.j2' % sys.path[0]
#         statefulset_yaml = '%s/statefulset.yaml' % self.k8s_path
#         code = j2_to_file("server", statefulset_info, statefulset_yaml_j2, statefulset_yaml)
#         if code == 1:
#             return code
#         logger.info("statefulset.yaml已生成。")
#         if server_type == "istio":
#             command = "istioctl kube-inject -f %s | kubectl apply -f -" % statefulset_yaml
#         else:
#             command = "kubectl apply -f %s" % statefulset_yaml
#         apply_command_list.append(command)
#         return apply_command_list
