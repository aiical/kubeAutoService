#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import copy
import asyncio
from publicClass.HttpFunc import k8s_api_http_get, harbor_api_http_get


class CheckOpera:
    def __init__(self, settings_conf):
        """读取settings设置"""
        conf = settings_conf
        self.cluster_dns_domain = conf['connectInfo']['clusterDnsDomain']
        self.api_server = "https://%s:%s" % (str(conf['apiServer']['host']), str(conf['apiServer']['port']))
        self.token = conf['connectInfo']['token']

        self.harbor_ip = conf['harborInfo']['host']
        self.harbor_user = conf['harborInfo']['user']
        self.harbor_pwd = conf['harborInfo']['password']

    """获取pod信息"""
    @staticmethod
    def get_container_info(container_status_list, container_spec_list, config_map_list):
        container_statuses_list = []
        container_resource_list = []
        container_use_config_map_list = []
        for spec in container_spec_list:
            if spec.__contains__("volumeMounts"):
                volume_mounts_list = spec['volumeMounts']
                for volume in volume_mounts_list:
                    for config_map in config_map_list:
                        if volume['name'] == config_map['volumeName']:
                            container_use_config_map_list.append(copy.deepcopy({
                                'containerName': spec['name'],
                                'configMapName': config_map['configMapName'],
                                'detail': {
                                    'type': 'volume',
                                    'volumeName': volume['name'],
                                    'mountPath': volume['mountPath']
                                }
                            }))

            if spec.__contains__('env'):
                env_list = spec['env']
                for env in env_list:
                    if env.__contains__('valueFrom') and env['valueFrom'].__contains__('configMapKeyRef'):
                        container_use_config_map_list.append(copy.deepcopy({
                            'containerName': spec['name'],
                            'configMapName': env['valueFrom']['configMapKeyRef']['name'],
                            'detail': {
                                'type': 'env',
                                'envName': env['name'],
                                'envKey': env['valueFrom']['configMapKeyRef']['key']
                            }
                        }))

            container_resource_list.append(copy.deepcopy({
                'name': spec['name'],
                'resource': spec['resources']
            }))

        for status in container_status_list:
            container_status_info = status['state']
            state_reason = ""
            state = ""
            for key, value in container_status_info.items():
                state = key
                if key == 'running':
                    state_reason = ""
                elif key == 'waiting':
                    state_reason = value['reason']
                elif key == 'terminated':
                    state_reason = value['reason']

            container_name = status['name']
            container_resource = {}
            for resource in container_resource_list:
                if resource['name'] == container_name:
                    container_resource = resource['resource']
                    break

            single_container_config_map = []
            for config_map_info in container_use_config_map_list:
                if config_map_info['containerName'] == container_name:
                    single_container_config_map.append(copy.deepcopy({
                        'name': config_map_info['configMapName'],
                        'detail': config_map_info['detail']
                    }))

            container_statuses_list.append(copy.deepcopy({
                'name': container_name,
                'state': state,
                'resource': container_resource,
                'useConfigMap': single_container_config_map,
                'stateReason': state_reason,
                'ready': status['ready'],
                'restartCount': int(status['restartCount']),
                'image': status['image']
            }))
        return container_statuses_list

    @staticmethod
    def get_pod_info(pod_info, service_info_list):
        service_name_list = []
        pod_name = pod_info['metadata']['name']
        namespace = pod_info['metadata']['namespace']
        create_time = pod_info['metadata']['creationTimestamp']
        if pod_info['spec'].__contains__('nodeSelector'):
            node_selector = pod_info['spec']['nodeSelector']
        else:
            node_selector = {}
        if pod_info['status'].__contains__('hostIP'):
            host_ip = pod_info['status']['hostIP']
        else:
            host_ip = ""
        if pod_info['status'].__contains__('podIP'):
            pod_ip = pod_info['status']['podIP']
        else:
            pod_ip = ""
        pod_status = pod_info['status']['phase']
        labels_info = pod_info['metadata']['labels']
        set_labels_info = set(labels_info.items())
        for service_info in service_info_list:
            svc_selector = service_info['selector']
            set_svc_selector = set(svc_selector.items())
            if svc_selector != {} and set_svc_selector.issubset(set_labels_info):
                service_name_list.append(copy.deepcopy(service_info['name']))

        volume_list = pod_info['spec']['volumes']
        config_map_list = []
        for volume in volume_list:
            if volume.__contains__('configMap'):
                cm_info = {
                    'volumeName': volume['name'],
                    'configMapName': volume['configMap']['name']
                }
                config_map_list.append(copy.deepcopy(cm_info))

        if pod_info['status'].__contains__('initContainerStatuses'):
            tmp_init_container_statuses = pod_info['status']['initContainerStatuses']
        else:
            tmp_init_container_statuses = []
        if pod_info['spec'].__contains__('initContainers'):
            tmp_init_container_spec = pod_info['spec']['initContainers']
        else:
            tmp_init_container_spec = []
        init_container_statuses = CheckOpera.get_container_info(
            tmp_init_container_statuses, tmp_init_container_spec, config_map_list)

        if pod_info['status'].__contains__("containerStatuses"):
            tmp_container_statuses = pod_info['status']['containerStatuses']
            tmp_container_spec = pod_info['spec']['containers']
            container_statuses = CheckOpera.get_container_info(tmp_container_statuses, tmp_container_spec,
                                                               config_map_list)
        else:
            container_statuses = []

        container_cnt = len(container_statuses)
        if container_cnt == 0:
            ready_status = ""
        else:
            ready_cnt = 0
            for status in container_statuses:
                ready = str(status['ready'])
                if ready == "True":
                    ready_cnt += 1
            ready_status = "ready(%s/%s)" % (str(ready_cnt), str(container_cnt))
        pod_info = {
            'name': pod_name,
            'namespace': namespace,
            'serviceNameList': service_name_list,
            'creationTimestamp': create_time,
            'labels': labels_info,
            'nodeSelector': node_selector,
            'hostIP': host_ip,
            'podIP': pod_ip,
            'status': "%s  %s" % (pod_status, ready_status),
            'initContainerStatuses': init_container_statuses,
            'containerStatuses': container_statuses,
            # 'readyStatus': ready_status
        }
        return pod_info

    def get_pod_status(self, url, check_range, service_info):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))

        if check_range != "pod":
            pod_list = k8s_result['items']
            pod_status_list = []
            if pod_list:
                for pod_info in pod_list:
                    pod_status = CheckOpera.get_pod_info(pod_info, service_info)
                    pod_status_list.append(copy.deepcopy(pod_status))
            return pod_status_list
        else:
            pod_status = CheckOpera.get_pod_info(k8s_result, service_info)
            return pod_status

    """获取namespace信息"""
    @staticmethod
    def get_namespace_info(ns_info):
        ns_name = ns_info['metadata']['name']
        create_time = ns_info['metadata']['creationTimestamp']
        status_info = ns_info['status']['phase']
        ns_status = {
            'name': ns_name,
            'creationTimestamp': create_time,
            'status': status_info
        }
        return ns_status

    def get_namespace_status(self, url, check_range):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))

        if check_range != "ns":
            ns_list = k8s_result['items']
            ns_status_list = []
            if ns_list:
                for ns_info in ns_list:
                    ns_status = CheckOpera.get_namespace_info(ns_info)
                    ns_status_list.append(copy.deepcopy(ns_status))
            return ns_status_list
        else:
            ns_status = CheckOpera.get_namespace_info(k8s_result)
            return ns_status

    """获取service信息"""
    @staticmethod
    def get_service_info(service_info, cluster_dns_domain):
        service_name = service_info['metadata']['name']
        namespace = service_info['metadata']['namespace']
        fqdn = "%s.%s.svc.%s" % (service_name, namespace, cluster_dns_domain)
        create_time = service_info['metadata']['creationTimestamp']
        service_type = service_info['spec']['type']
        if service_info['spec'].__contains__('selector'):
            service_selector = service_info['spec']['selector']
        else:
            service_selector = {}
        if service_info['spec'].__contains__('externalIPs'):
            external_ips = service_info['spec']['externalIPs']
        else:
            external_ips = []
        service_cluster_ip = service_info['spec']['clusterIP']
        service_ports = service_info['spec']['ports']
        service_status = {
            'name': service_name,
            'fqdn': fqdn,
            'namespace': namespace,
            'creationTimestamp': create_time,
            'serviceType': service_type,
            'selector': service_selector,
            'clusterIp': service_cluster_ip,
            'externalIPs': external_ips,
            'ports': service_ports
        }
        return service_status

    def get_service_status(self, url, check_range):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))

        if check_range != "svc":
            service_list = k8s_result['items']
            service_status_list = []
            if service_list:
                for service_info in service_list:
                    service_status = CheckOpera.get_service_info(service_info, self.cluster_dns_domain)
                    service_status_list.append(copy.deepcopy(service_status))
            return service_status_list
        else:
            service_status = CheckOpera.get_service_info(k8s_result, self.cluster_dns_domain)
            return service_status

    """获取node信息"""
    @staticmethod
    def get_node_info(node_info):
        node_name = node_info['metadata']['name']
        node_ip = ""
        node_addresses = node_info['status']['addresses']
        for address in node_addresses:
            if address['type'] == "InternalIP":
                node_ip = address['address']
                break
        create_time = node_info['metadata']['creationTimestamp']
        labels = node_info['metadata']['labels']
        node_base_info = node_info['status']['nodeInfo']
        node_conditions = node_info['status']['conditions']
        node_capacity = node_info['status']['capacity']
        node_allocatable = node_info['status']['allocatable']
        node_status = {
            'name': node_name,
            'internalIp': node_ip,
            'creationTimestamp': create_time,
            'labels': labels,
            'nodeInfo': node_base_info,
            'nodeConditions': node_conditions,
            'nodeCapacity': node_capacity,
            'nodeAllocatable': node_allocatable
        }
        return node_status

    def get_node_status(self, url, check_range):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))

        if check_range != 'node':
            node_list = k8s_result['items']
            node_status_list = []
            if node_list:
                for node_info in node_list:
                    node_status = CheckOpera.get_node_info(node_info)
                    node_status_list.append(copy.deepcopy(node_status))
            return node_status_list
        else:
            node_status = CheckOpera.get_node_info(k8s_result)
            return node_status

    """获取componentStatus信息"""
    def get_component_list(self, url):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))
        component_list = k8s_result['items']
        component_status_list = []
        if component_list:
            component_status = {}
            for component_info in component_list:
                ns_name = component_info['metadata']['name']
                condition = component_info['conditions']
                component_status.update({
                    'name': ns_name,
                    'condition': condition
                })
                component_status_list.append(copy.deepcopy(component_status))
        return component_status_list

    """获取configMap信息"""
    @staticmethod
    def get_config_map_info(config_map_list):
        config_map_status_list = []
        if config_map_list:
            for config_map_info in config_map_list:
                name = config_map_info['metadata']['name']
                namespace = config_map_info['metadata']['namespace']
                create_time = config_map_info['metadata']['creationTimestamp']
                if config_map_info.__contains__('data'):
                    data = config_map_info['data']
                else:
                    data = {}
                config_map_status = {
                    'name': name,
                    'namespace': namespace,
                    'creationTimestamp': create_time,
                    'data': data
                }
                config_map_status_list.append(copy.deepcopy(config_map_status))
        return config_map_status_list

    def get_config_map_list(self, url):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))
        config_map_list = k8s_result['items']
        config_map_status_list = CheckOpera.get_config_map_info(config_map_list)
        return config_map_status_list

    """获取pod日志信息"""
    def get_pod_log_tail(self, url):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'text'))
        return k8s_result

    """获取gateway信息"""
    @staticmethod
    def get_gateway_info(gateway_info):
        gateway_name = gateway_info['metadata']['name']
        namespace = gateway_info['metadata']['namespace']
        selected_istio_ingress_gateway = gateway_info['spec']['selector']['istio']
        create_time = gateway_info['metadata']['creationTimestamp']
        gateway_server = gateway_info['spec']['servers']
        gateway_status = {
            'name': gateway_name,
            'namespace': namespace,
            'creationTimestamp': create_time,
            'selectedIngressGateway': selected_istio_ingress_gateway,
            'server': gateway_server
        }
        return gateway_status

    def get_gateway_status(self, url, check_range):
        resp_status, k8s_result = asyncio.run(k8s_api_http_get(url, self.token, 'json'))
        if check_range != 'gateway':
            gateway_list = k8s_result['items']
            gateway_status_list = []
            if gateway_list:
                for gateway_info in gateway_list:
                    gateway_status = CheckOpera.get_gateway_info(gateway_info)
                    gateway_status_list.append(copy.deepcopy(gateway_status))
            return gateway_status_list
        else:
            gateway_status = CheckOpera.get_gateway_info(k8s_result)
            return gateway_status

    @staticmethod
    def get_artifacts_bak_info(artifacts_info, harbor_ip):
        size = artifacts_info["size"]
        label_list = artifacts_info["labels"]
        tag_list = artifacts_info["tags"]
        artifacts_tags = []
        for tag in tag_list:
            artifacts_tags.append(copy.deepcopy({
                "id": tag["id"],
                "name": tag['name']
            }))
        artifacts_labels = []
        if label_list:
            for label in label_list:
                artifacts_labels.append(copy.deepcopy({
                    "name": label['name'],
                    "description": label["description"]
                }))
        image_artifacts_info = {
            "id": artifacts_info['id'],
            'projectId': artifacts_info['project_id'],
            'repositoryId': artifacts_info['repository_id'],
            'scanOverview': artifacts_info['scan_overview'],
            "harborHost": harbor_ip,
            "tags": artifacts_tags,
            "author": artifacts_info['extra_attrs']['author'],
            "createTime": artifacts_info['extra_attrs']['created'],
            "pushTime": artifacts_info['push_time'],
            "size": size,
            "labels": artifacts_labels
        }
        return image_artifacts_info

    @staticmethod
    def get_artifacts_info(artifacts_info, harbor_ip):
        size = round(artifacts_info["size"]/1024/1024)
        digest = artifacts_info["digest"]
        artifacts_id = artifacts_info["id"]
        project_id = artifacts_info["project_id"]
        repository_id = artifacts_info["repository_id"]
        if artifacts_info.__contains__("scan_overview"):
            scan_overview = artifacts_info["scan_overview"]
        else:
            scan_overview = {}
        author = artifacts_info['extra_attrs']['author']
        create_time = artifacts_info['extra_attrs']['created']
        push_time = artifacts_info['push_time']
        label_list = artifacts_info["labels"]
        tag_list = artifacts_info["tags"]
        artifacts_tags = []
        if tag_list:
            for tag in tag_list:
                artifacts_tags.append(copy.deepcopy({
                    "id": tag["id"],
                    "name": tag['name']
                }))
        artifacts_labels = []
        if label_list:
            for label in label_list:
                artifacts_labels.append(copy.deepcopy({
                    "name": label['name'],
                    "description": label["description"]
                }))
        image_artifacts_info = {
            "id": artifacts_id,
            "digest": digest,
            'projectId': project_id,
            'repositoryId': repository_id,
            'scanOverview': scan_overview,
            "harborHost": harbor_ip,
            "tags": artifacts_tags,
            "author": author,
            "createTime": create_time,
            "pushTime": push_time,
            "size": size,
            "labels": artifacts_labels
        }
        return image_artifacts_info

    def get_artifacts_status(self, url, check_range):
        # artifacts_list = curl_harbor_get_func(url, self.harbor_user, self.harbor_pwd)
        resp_status, artifacts_list = asyncio.run(harbor_api_http_get(url, self.harbor_user, self.harbor_pwd))
        if artifacts_list.__contains__("errors"):
            return None
        if check_range != 'artifacts':
            artifacts_detail_list = []
            if artifacts_list:
                for artifacts_info in artifacts_list:
                    artifacts_detail = CheckOpera.get_artifacts_info(artifacts_info, self.harbor_ip)
                    artifacts_detail_list.append(copy.deepcopy(artifacts_detail))
            return artifacts_detail_list
        else:
            artifacts_detail = CheckOpera.get_artifacts_info(artifacts_list, self.harbor_ip)
            return artifacts_detail

    @staticmethod
    def get_projects_info(projects_info, harbor_ip):
        name = projects_info["name"]
        project_id = projects_info["project_id"]
        if projects_info.__contains__("repo_count"):
            repo_count = projects_info["repo_count"]
        else:
            repo_count = 0
        creation_time = projects_info["creation_time"]
        update_time = projects_info["update_time"]

        projects_result = {
            "id": project_id,
            "name": name,
            "harborHost": harbor_ip,
            "repoCount": repo_count,
            "creationTime": creation_time,
            "updateTime": update_time
        }

        return projects_result

    def get_projects_status(self, url, check_range):
        # projects_list = curl_harbor_get_func(url, self.harbor_user, self.harbor_pwd)
        resp_status, projects_list = asyncio.run(harbor_api_http_get(url, self.harbor_user, self.harbor_pwd))
        if projects_list.__contains__("errors"):
            return None
        if check_range != 'projects':
            projects_detail_list = []
            if projects_list:
                for projects_info in projects_list:
                    projects_detail = CheckOpera.get_projects_info(projects_info, self.harbor_ip)
                    projects_detail_list.append(copy.deepcopy(projects_detail))
            return projects_detail_list
        else:
            projects_detail = CheckOpera.get_projects_info(projects_list, self.harbor_ip)
        return projects_detail

    @staticmethod
    def get_repositories_info(repositories_info, harbor_ip):
        repo_id = repositories_info["id"]
        name = repositories_info["name"]
        project_id = repositories_info["project_id"]
        artifact_count = repositories_info["artifact_count"]
        if repositories_info.__contains__("pull_count"):
            pull_count = repositories_info["pull_count"]
        else:
            pull_count = 0
        creation_time = repositories_info["creation_time"]
        update_time = repositories_info["update_time"]

        repositories_result = {
            "id": repo_id,
            "name": name,
            "projectId": project_id,
            "harborHost": harbor_ip,
            "artifactCount": artifact_count,
            "pullCount": pull_count,
            "creationTime": creation_time,
            "updateTime": update_time
        }

        return repositories_result

    def get_repositories_status(self, url, check_range):
        # repositories_list = curl_harbor_get_func(url, self.harbor_user, self.harbor_pwd)
        resp_status, repositories_list = asyncio.run(harbor_api_http_get(url, self.harbor_user, self.harbor_pwd))
        if repositories_list.__contains__("errors"):
            return None
        if check_range != 'repositories':
            repositories_detail_list = []
            if repositories_list:
                for repositories_info in repositories_list:
                    repositories_detail = CheckOpera.get_repositories_info(repositories_info, self.harbor_ip)
                    repositories_detail_list.append(copy.deepcopy(repositories_detail))
            return repositories_detail_list
        else:
            repositories_detail = CheckOpera.get_repositories_info(repositories_list, self.harbor_ip)
        return repositories_detail
    
    @staticmethod
    def get_tags_info(tags_info, harbor_ip):
        tag_id = tags_info["id"]
        name = tags_info["name"]
        artifact_id = tags_info["artifact_id"]
        repository_id = tags_info["repository_id"]
        push_time = tags_info["push_time"]

        tags_result = {
            "id": tag_id,
            "name": name,
            "artifactId": artifact_id,
            "repositoryId": repository_id,
            "harborHost": harbor_ip,
            "pushTime": push_time
        }

        return tags_result

    def get_tags_status(self, url, check_range):
        # tags_list = curl_harbor_get_func(url, self.harbor_user, self.harbor_pwd)
        resp_status, tags_list = asyncio.run(harbor_api_http_get(url, self.harbor_user, self.harbor_pwd))
        if tags_list.__contains__("errors"):
            return None
        if check_range != 'tags':
            tags_detail_list = []
            if tags_list:
                for tags_info in tags_list:
                    tags_detail = CheckOpera.get_tags_info(tags_info, self.harbor_ip)
                    tags_detail_list.append(copy.deepcopy(tags_detail))
            return tags_detail_list
        else:
            tags_detail = CheckOpera.get_tags_info(tags_list, self.harbor_ip)
        return tags_detail

