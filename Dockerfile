# 使用官方Python运行时作为父镜像
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器的/app目录
COPY . /app

RUN pip install --upgrade pip
# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露Flask默认端口
EXPOSE 5000

# 定义环境变量
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# 运行应用
CMD ["gunicorn", "-b", "0.0.0.0:5000", "web:app"]