FROM python:3.9

WORKDIR /opt/program

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY inference.py .
COPY model.pt /opt/ml/model/model.pt

# 设置环境变量
ENV MODEL_PATH=/opt/ml/model/model.pt

EXPOSE 8080

CMD ["python", "inference.py"]