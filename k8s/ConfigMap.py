#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from publicClass.Logger import Logger
from publicClass.PublicFunc import j2_to_file, set_ns_svc, get_remote_file, compared_version


class ConfigMap:
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path, media_path):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.k8s_path = k8s_path
        self.media_path = media_path
        self.object_storage_conf = settings_conf['objectStorage']
        self.file_beat_version = str(settings_conf['filebeatDefaults']['version'])
        self.log_kafka_info = settings_conf['filebeatDefaults']['kafkaInfo']
        self.log_stash_host = settings_conf['filebeatDefaults']['logstashHost']

    def get_config_map_file_beat_info(self):
        logger = Logger("server")
        logger.info("开始获取filebeat-configmap信息")
        cluster_name = self.global_info['runEnv']
        sys_name = self.global_info['sysName']
        app_name = self.global_info['appName']
        """获取服务名和名称空间"""
        service_name, namespace = set_ns_svc(sys_name, app_name)
        # sys_name, service_name, namespace = set_run_env(run_env, sys_name, app_name)

        version_flag = compared_version(self.file_beat_version, "7.9.2")
        cm_file_beat = {
            'clusterName': cluster_name,
            'serviceName': service_name,
            'namespace': namespace,
            'sysName': sys_name,
            'appName': app_name,
            'versionFlag': version_flag,
            'kafkaList': self.log_kafka_info,
            'logstashList': self.log_stash_host
        }
        logger.info("获取filebeat-configmap信息完成")
        return cm_file_beat

    def get_config_map_app_info(self):
        logger = Logger("server")
        logger.info("开始获取应用-configmap信息")
        cm_app_list = []
        sys_name = self.global_info['sysName']
        app_name = self.global_info['appName']
        """获取服务名和名称空间"""
        service_name, namespace = set_ns_svc(sys_name, app_name)
        config_map_list = self.k8s_info['container']['volume']['configMap']
        for config_map in config_map_list:
            file_name = config_map['fileName']
            tmp_name = ''.join(list(filter(str.isalnum, file_name))).lower()
            name = "%s-%s" % (service_name, tmp_name)
            key = config_map['key']
            md5_code = config_map['md5Code']
            file_full_name = "%s/%s" % (self.media_path, file_name)
            file_full_name = file_full_name.replace("//", "/")
            logger.info("从对象存储获取configmap文件%s" % file_name)
            if get_remote_file("server", self.object_storage_conf, key, md5_code, file_full_name) == 1:
                return 1
            config_map_info = {
                'name': name,
                'namespace': namespace,
                'fileName': file_name,
                'fileFullName': file_full_name
            }
            cm_app_list.append(config_map_info)
        logger.info("获取应用-configmap信息完成")
        return cm_app_list

    def create_config_map_file_beat_yaml(self, cm_file_beat):
        logger = Logger("server")
        logger.info("开始创建configMap-fileBeat.yaml")
        logger.info("configMap-fileBeat配置如下：")
        logger.info(cm_file_beat)
        cm_file_beat_yaml_j2 = '%s/templates/k8s/configMap-fileBeat.yaml.j2' % sys.path[0]
        cm_file_beat_yaml = '%s/configMap-fileBeat.yaml' % self.k8s_path
        j2_to_file("server", cm_file_beat, cm_file_beat_yaml_j2, cm_file_beat_yaml)
        logger.info("configMap-fileBeat.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % cm_file_beat_yaml]
        return apply_command_list

    def create_config_map_app_yaml(self, cm_app_list):
        apply_command_list = []
        logger = Logger("server")
        for cm in cm_app_list:
            name = cm['name']
            logger.info("开始创建configMap-%s.yaml" % name)
            logger.info("configMap-%s配置如下：" % name)
            logger.info(cm)
            cm_yaml_j2 = '%s/templates/k8s/configMap-default.yaml.j2' % sys.path[0]
            cm_yaml = '%s/configMap-%s.yaml' % (self.k8s_path, name)
            j2_to_file("server", cm, cm_yaml_j2, cm_yaml)
            logger.info("configMap-%s.yaml已生成。" % name)
            apply_command_list.append("kubectl apply -f %s" % cm_yaml)
        return apply_command_list
