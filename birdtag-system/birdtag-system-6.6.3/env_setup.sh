# python version
sudo apt install python3-pip -y

sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

sudo apt install python3.9 python3.9-venv python3.9-dev -y
sudo apt install python3.11 python3.11-venv python3.11-dev -y 



# aws
sudo apt install curl unzip -y
cd ~ && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# aws sam cli
cd ~ && wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# ==========
cd ~/fit5225a3/on_git/birdtag-system
chmod +x layers/build_layers.sh
./layers/build_layers.sh


# check after install
# python version
python3.9 --version
python3.11 --version

# ff
ls -l birdtag-system/layers/ffmpeg/opt/ffmpeg/ffmpeg 
sudo apt install ffmpeg
ffmpeg -version

# pickages
ls -l birdtag-system/layers/bird_detection/python/python3.9/site-packages/
ls -l birdtag-system/layers/birdnet_analyzer/python/python3.11/site-packages/

# model
ls -l birdtag-system/layers/bird_detection/model/
ls -l birdtag-system/layers/birdnet_analyzer/model/

# setup aws configure
aws configure

# build
cd birdtag-system/
sam build

# check after build
sam validate

# install docker
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

sudo usermod -aG docker $USER

sudo systemctl start docker
sudo systemctl enable docker

docker --version

# local test
sam local start-api
