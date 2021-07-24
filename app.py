#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import json
import math
import logging
from logging import handlers
from flask import Flask, request, jsonify, Response
from concurrent.futures import ThreadPoolExecutor
from publicClass.Logger import Logger
from publicClass.PublicFunc import read_yaml
from k8s.InitSystem import InitSystem
from k8s.InitApp import InitApp
from k8s.AuthorizationPolicy import AuthorizationPolicy
from k8s.InitPolicy import InitPolicy
from k8s.CheckOpera import CheckOpera


app = Flask(__name__)

fmt = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
log_path = sys.path[0] + "/logs/start.log"

logging.basicConfig(level=logging.INFO)
th = handlers.RotatingFileHandler(filename=log_path, maxBytes=10*1024*1024, backupCount=10, encoding='utf-8')
th.setFormatter(fmt)
th.setLevel('INFO')
logging.getLogger().addHandler(th)

executor = ThreadPoolExecutor(3)
file_settings = sys.path[0] + '/conf/settings.yaml'
setting_conf = read_yaml(file_settings)
api_server = "https://%s:%s" % (str(setting_conf['apiServer']['host']), str(setting_conf['apiServer']['port']))
harbor_ip = setting_conf['harborInfo']['host']
task_back_url = setting_conf['taskInfoBack']['url']


@app.route('/auto/runApp', methods=["POST"])
def run_auto_deploy_app_tasks():
    post_data = request.get_data()
    post_json_data = json.loads(post_data.decode("utf-8"))
    executor.submit(run_app_task, post_json_data)
    return 'task done!'


def run_app_task(post_json_data):
    app_task = InitApp(setting_conf, post_json_data)
    app_task.check()
    app_task.deploy()


@app.route('/auto/runSys', methods=["POST"])
def run_auto_deploy_sys_tasks():
    post_data = request.get_data()
    post_json_data = json.loads(post_data.decode("utf-8"))
    executor.submit(run_system_task, post_json_data)
    return 'task done!'


def run_system_task(post_json_data):
    system_task = InitSystem(setting_conf, post_json_data)
    system_task.deploy()


@app.route('/auto/opera', methods=["POST"])
def run_auto_opera_app_tasks():
    post_data = request.get_data()
    post_json_data = json.loads(post_data.decode("utf-8"))
    executor.submit(opera_app_task, post_json_data)
    return 'task done!'


def opera_app_task(post_json_data):
    app_task = InitApp(setting_conf, post_json_data)
    app_task.check()
    app_task.opera()


@app.route('/auto/setAccess', methods=["POST"])
def run_auto_set_access_strategy():
    post_data = request.get_data()
    post_json_data = json.loads(post_data.decode("utf-8"))
    executor.submit(set_access_strategy, post_json_data)
    return 'task done!'


def set_access_strategy(post_json_data):
    access_strategy = InitPolicy(setting_conf, post_json_data)
    access_strategy.check()
    access_strategy.deploy()


def run_redis_task(redis_data):
    global_config = redis_data['global']
    k8s_config = redis_data['kubernetes']
    pass


def run_rocket_mq_task(rocket_mq_data):
    pass


def check_pod(check_range, namespace, service, pod_name):
    check_state = CheckOpera(setting_conf)
    if check_range == 'all':
        url = "%s/api/v1/pods" % api_server
        svc_url = "%s/api/v1/services" % api_server
        service_info_list = check_state.get_service_status(svc_url, check_range)

    elif check_range == 'svc':
        svc_url = "%s/api/v1/namespaces/%s/services/%s" % (api_server, namespace, service)
        service_info = check_state.get_service_status(svc_url, check_range)
        service_info_list = [service_info]
        svc_selector = service_info['selector']
        label_selector = ""
        for key, value in svc_selector.items():
            label_selector += "%s=%s," % (key, value)
        if label_selector == "":
            label_selector = "serviceHasNoPod=yes"
        else:
            label_selector = label_selector[:-1]
        url = "%s/api/v1/namespaces/%s/pods?labelSelector=%s" % (api_server, namespace, label_selector)

    elif check_range == 'pod':
        url = "%s/api/v1/namespaces/%s/pods/%s" % (api_server, namespace, pod_name)
        svc_url = "%s/api/v1/namespaces/%s/services" % (api_server, namespace)
        service_info_list = check_state.get_service_status(svc_url, check_range)
    else:
        url = "%s/api/v1/namespaces/%s/pods" % (api_server, namespace)
        svc_url = "%s/api/v1/namespaces/%s/services" % (api_server, namespace)
        service_info_list = check_state.get_service_status(svc_url, check_range)

    check_result = check_state.get_pod_status(url, check_range, service_info_list)
    return check_result


def check_service(check_range, namespace, service):
    check_state = CheckOpera(setting_conf)
    if check_range == 'all':
        url = "%s/api/v1/services" % api_server
    elif check_range == 'svc':
        url = "%s/api/v1/namespaces/%s/services/%s" % (api_server, namespace, service)
    else:
        url = "%s/api/v1/namespaces/%s/services" % (api_server, namespace)
    check_result = check_state.get_service_status(url, check_range)
    return check_result


def check_namespace(check_range, namespace):
    check_state = CheckOpera(setting_conf)
    if check_range == 'ns':
        url = "%s/api/v1/namespaces/%s" % (api_server, namespace)
    else:
        url = "%s/api/v1/namespaces" % api_server
    check_result = check_state.get_namespace_status(url, check_range)
    return check_result


def check_node(check_range, node):
    check_state = CheckOpera(setting_conf)
    if check_range == 'all':
        url = "%s/api/v1/nodes" % api_server
        # check_result = check_state.get_node_status(url, check_range)
    else:
        # service_range == 'node':
        url = "%s/api/v1/nodes/%s" % (api_server, str(node))
    check_result = check_state.get_node_status(url, check_range)
    return check_result


def get_pod_logs(namespace, pod_name, container_name, is_previous, tail_lines):
    check_state = CheckOpera(setting_conf)
    url = "%s/api/v1/namespaces/%s/pods/%s/log?container=%s&previous=%s&tailLines=%s" % (
        api_server, namespace, pod_name, container_name, is_previous, tail_lines)
    check_txt = check_state.get_pod_log_tail(url)
    return Response(check_txt, mimetype='text/plain')


def check_component():
    check_state = CheckOpera(setting_conf)
    url = "%s/api/v1/componentstatuses" % api_server
    check_result = check_state.get_component_list(url)
    return check_result


def check_config_map(check_range, namespace):
    check_state = CheckOpera(setting_conf)
    if check_range == 'all':
        url = "%s/api/v1/configmaps" % api_server
    else:
        url = "%s/api/v1/namespaces/%s/configmaps" % (api_server, namespace)
    check_result = check_state.get_config_map_list(url)
    return check_result


def check_gateway(check_range, namespace, gateway):
    check_state = CheckOpera(setting_conf)
    if check_range == 'all':
        url = "%s/apis/networking.istio.io/v1beta1/gateways" % api_server
    elif check_range == 'gateway':
        url = "%s/apis/networking.istio.io/v1beta1/namespaces/%s/gateways/%s" % (api_server, namespace, gateway)
    else:
        # service_range == 'ns':
        url = "%s/apis/networking.istio.io/v1beta1/namespaces/%s/gateways" % (api_server, namespace)
    check_result = check_state.get_gateway_status(url, check_range)
    return check_result


@app.route('/auto/check', methods=["GET"])
def check_auto_cluster_info():
    # logger = Logger("check")
    # tz = timezone(timedelta(hours=+8))
    # logger.info("check_auto_cluster_info start: %s" % datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    check_type = request.args.get('checkType')
    if check_type == "pod":
        check_range = request.args.get('range')
        namespace = request.args.get('namespace')
        service = request.args.get('service')
        pod_name = request.args.get('pod')
        future = executor.submit(check_pod, check_range=check_range, namespace=namespace, service=service,
                                 pod_name=pod_name)
    elif check_type == "service":
        check_range = request.args.get('range')
        namespace = request.args.get('namespace')
        service = request.args.get('service')
        future = executor.submit(check_service, check_range=check_range, namespace=namespace, service=service)
    elif check_type == "namespace":
        check_range = request.args.get('range')
        namespace = request.args.get('namespace')
        future = executor.submit(check_namespace, check_range=check_range, namespace=namespace)
    elif check_type == "log":
        namespace = request.args.get('namespace')
        pod_name = request.args.get('pod')
        container_name = request.args.get('container')
        is_previous = request.args.get('previous')
        tail_lines = request.args.get('tail')
        future = executor.submit(get_pod_logs, namespace=namespace, pod_name=pod_name, container_name=container_name,
                                 is_previous=is_previous, tail_lines=tail_lines)
        return future.result()
    elif check_type == "node":
        check_range = request.args.get('range')
        node = request.args.get('node')
        future = executor.submit(check_node, check_range=check_range, node=node)
    # elif check_type == 'component':
    #     future = executor.submit(check_component)
    # elif check_type == 'configmap':
    #     check_range = request.args.get('range')
    #     namespace = request.args.get('namespace')
    #     future = executor.submit(check_config_map, check_range=check_range, namespace=namespace)
    # elif check_type == 'gateway':
    #     check_range = request.args.get('range')
    #     namespace = request.args.get('namespace')
    #     gateway = request.args.get('gateway')
    #     future = executor.submit(check_gateway, check_range=check_range, namespace=namespace, gateway=gateway)
    else:
        future = None

    # logger.info("check_auto_cluster_info end: %s" % datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    return jsonify(content_type='application/json;charset=utf-8',
                   reason='success',
                   charset='utf-8',
                   status='200',
                   content=future.result())


@app.route('/auto/harbor', methods=["GET"])
def get_auto_harbor_info():
    check_type = request.args.get('type')
    check_range = request.args.get('range')
    check_state = CheckOpera(setting_conf)
    result = []
    if check_type == 'artifacts':
        project = request.args.get('project')
        repository = request.args.get('repository')
        # url = "https://%s/api/repositories/%s%%2F%s/tags" % (harbor_ip, project, image_name)
        repo_url = "https://%s/api/v2.0/projects/%s/repositories/%s" % (harbor_ip, project, repository)
        repo_result = check_state.get_repositories_status(repo_url, "repositories")
        artifact_count = int(repo_result['artifactCount'])
        page = math.ceil(artifact_count / 10)
        for n in range(1, page + 1):
            url = "https://%s/api/v2.0/projects/%s/repositories/%s/artifacts" \
                  "?with_tag=true&with_label=true&with_scan_overview=true&page=%s&page_size=10" % (
                    harbor_ip, project, repository, str(n))
            tmp_result = check_state.get_artifacts_status(url, check_range)
            result.extend(tmp_result)

    elif check_type == 'projects':
        url = "https://%s/api/v2.0/projects?page_size=0" % harbor_ip
        result = check_state.get_projects_status(url, check_range)

    elif check_type == 'repositories':
        project = request.args.get('project')
        url = "https://%s/api/v2.0/projects/%s/repositories?page_size=0" % (harbor_ip, project)
        result = check_state.get_repositories_status(url, check_range)
    elif check_type == 'tags':
        project = request.args.get('project')
        repository = request.args.get('repository')
        artifact_digest = request.args.get('artifact_digest')

        url = "https://%s/api/v2.0/projects/%s/repositories/%s/artifacts/%s/tags?page_size=0" % (
            harbor_ip, project, repository, artifact_digest)
        result = check_state.get_tags_status(url, check_range)
    else:
        result = None

    return jsonify(content_type='application/json;charset=utf-8',
                   reason='success',
                   charset='utf-8',
                   status='200',
                   content=result)


@app.route('/auto/harbor', methods=["POST"])
def post_auto_harbor_info():
    pass


if __name__ == '__main__':
    logger = Logger("server")
    int_port = int(setting_conf['connectInfo']['port'])
    logger.info("等待连接...")
    app.run(host='0.0.0.0',
            threaded=True,
            debug=True,
            port=int_port)
