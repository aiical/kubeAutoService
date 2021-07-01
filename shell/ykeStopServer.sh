#!/bin/bash
s_run_num=$(ps -ef |grep "kubeAutoService/app.py" |grep -v grep |wc -l)
if [ "${s_run_num}" != "0" ];then
  ps -ef |grep "kubeAutoService/app.py" |grep -v grep |awk '{print $2}' |xargs kill -9
else
  echo "自动发布服务未启动。"
fi
s_run_num=$(ps -ef |grep "kubeAutoService/app.py" |grep -v grep |wc -l)
if [ "${s_run_num}" == "0" ];then
  echo "自动发布服务已停止。"
else
  echo "自动发布服务停止失败。"
fi