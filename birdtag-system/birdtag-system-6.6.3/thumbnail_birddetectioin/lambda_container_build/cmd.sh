# sudo usermod -aG docker $USER
# newgrp docker

# pull docker
docker pull cjin0018/birddetectionlambdaimage:latest

# test
python test_model.py

# build
docker build -t birddetection-lambdaimage .

# url:591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/birddetection-lambdaimage

# tag & push
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com

docker tag birddetection-lambdaimage:latest 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/birddetection-lambdaimage:latest

docker push 591256669981.dkr.ecr.ap-southeast-2.amazonaws.com/birddetection-lambdaimage:latest
