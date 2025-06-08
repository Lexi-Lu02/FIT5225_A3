# 1. 选用官方 Lambda Python 3.9 运行时镜像
FROM public.ecr.aws/lambda/python:3.9

# 2. 拷贝并安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3. 拷贝函数代码
COPY app.py ${LAMBDA_TASK_ROOT}

# 4. 设置启动入口
CMD ["app.lambda_handler"]
