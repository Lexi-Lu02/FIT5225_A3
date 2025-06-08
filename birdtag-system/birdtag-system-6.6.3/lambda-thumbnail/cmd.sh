# 本地构建并测试
docker build -t lambda-thumb-test .

# 启动容器并暴露端口
docker run --rm -d -p 9000:8080 lambda-thumb-test

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
        "Records":[
          {
            "s3":{
              "bucket":{"name":"your-test-bucket"},
              "object":{"key":"upload/image/test.jpg"}
            }
          }
        ]
      }'

# key
591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/thumbnail-test

aws ecr get-login-password --region ap-southeast-2 \
  | docker login --username AWS --password-stdin 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com

docker tag lambda-thumb-test:latest 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/thumbnail-test:latest

docker push 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/thumbnail-test:latest
