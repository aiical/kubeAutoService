#!/bin/bash

s_run_num=$(ps -ef |grep "kubeAutoService/app.py" |grep -v grep |wc -l)
if [ "${s_run_num}" != "0" ];then
  ps -ef |grep "kubeAutoService/app.py" |grep -v grep
  echo "自动发布服务已启动"
else
  echo "自动发布服务未启动"
fi