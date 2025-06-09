# pull dockerhub
docker pull cjin0018/birdanalyzerlambdaimage:latest

# test
DDB_TABLE=your-dynamodb-table-name python test.py

# build
docker build -t birdnet-lambda .

# tag & push
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com
docker tag birdnet-lambda:latest 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/birdnetanalyzer-lambdaimage:latest
docker push 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/birdnetanalyzer-lambdaimage:latest
