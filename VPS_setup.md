# Atualizando o Servidor Debian 12
1 - sudo apt update && sudo apt full-upgrade

# Comandos de Instalação do Docker
2 - apt install -y sudo gnupg2 wget ca-certificates apt-transport-https curl gnupg nano htop
3 - sudo install -m 0755 -d /etc/apt/keyrings
4 - curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
5 - sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Adicionando as FONTES do Docker
6 - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
7 - sudo apt-get update

# Instalação dos Pacotes Docker
8 - sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Conferindo instalação do Docker
9 - sudo docker --version

# Criando inicialização automática do Docker ao reiniciar o servidor
10 - sudo systemctl enable docker.service
11 - sudo systemctl enable containerd.service

# Inicia o Swarm
12 - docker swarm init --advertise-addr=#[IP Primário do Manager]

# Configurar a rede do Docker Swarm
13 - docker network create --driver=overlay network_swarm_public

# Instalando o CTOP
# https://github.com/bcicen/ctop

14 - sudo apt-get install ca-certificates curl gnupg lsb-release
15 - curl -fsSL https://azlux.fr/repo.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/azlux-archive-keyring.gpg
16 - echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/azlux.list >/dev/null
17 - sudo apt-get update
18 - sudo apt-get install -y docker-ctop
