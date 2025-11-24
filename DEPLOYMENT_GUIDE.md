# Guia de Deploy da Infraestrutura

## 📋 Pré-requisitos

- **VPS/Servidor:** Linux (Debian, Ubuntu, RHEL, Fedora, Alpine ou Arch)
- **Acesso:** Root ou sudo
- **GitHub Token:** Personal Access Token com permissão `repo` para repositórios privados

## 🚀 Deploy via One-Liner

### Opção 1: One-Liner Interativo (Recomendado)

Execute o comando abaixo como **root** e será solicitado o GitHub Token:

```bash
curl -sL https://raw.githubusercontent.com/lucasvnd/infra/main/setup_public.sh | bash
```

O script irá:
1. Solicitar seu GitHub Personal Access Token
2. Instalar dependências (git, python3)
3. Clonar o repositório privado
4. Executar o instalador Python
5. Limpar arquivos temporários

### Opção 2: One-Liner com Token (Automático)

Se preferir passar o token direto no comando (útil para automação):

```bash
GITHUB_TOKEN=your_token_here curl -sL https://raw.githubusercontent.com/lucasvnd/infra/main/setup.sh | sudo -E bash
```

**⚠️ AVISO:** Não exponha seu token em logs ou histórico de comandos!

### Opção 3: Clone Manual + Execução

```bash
# Clone o repositório
git clone https://github.com/lucasvnd/infra.git /opt/infra_installer

# Execute o instalador
cd /opt/infra_installer
python3 install.py
```

## 🔑 Como Obter o GitHub Token

1. Acesse: https://github.com/settings/tokens
2. Clique em **"Generate new token (classic)"**
3. Dê um nome descritivo (ex: "VPS Infrastructure Deploy")
4. Marque a permissão: **`repo`** (Full control of private repositories)
5. Clique em **"Generate token"**
6. **Copie o token** (ele só será mostrado uma vez!)

## 📝 Processo de Instalação

O instalador irá perguntar e configurar:

### 1. **VPS Setup** (opcional)
- Atualização do sistema
- Instalação do Docker
- Inicialização do Docker Swarm
- Criação de rede overlay

### 2. **Variáveis de Configuração**
O script coleta as seguintes informações:

#### Obrigatórias (você precisa fornecer):
- `DOMINIO` - Domínio principal (ex: example.com)
- `ACME_EMAIL` - Email para certificados SSL Let's Encrypt
- `SMTP_HOST` - Servidor SMTP
- `SMTP_PORT` - Porta SMTP (ex: 587)
- `SMTP_USER` - Usuário SMTP
- `SMTP_PASS` - Senha SMTP
- `SMTP_SENDER` - Email remetente
- `RABBITMQ_DEFAULT_USER` - Usuário RabbitMQ

#### Auto-geradas (senhas seguras criadas automaticamente):
- `POSTGRES_PASSWORD` - Senha PostgreSQL (32 chars)
- `MINIO_ROOT_USER` - Usuário Minio (16 chars)
- `MINIO_ROOT_PASSWORD` - Senha Minio (32 chars)
- `RABBITMQ_DEFAULT_PASS` - Senha RabbitMQ (32 chars)
- `RABBITMQ_ERLANG_COOKIE` - Cookie Erlang (48 chars)
- `N8N_ENCRYPTION_KEY` - Chave de criptografia n8n (32 chars)
- `SECRET_KEY_BASE` - Secret key Chatwoot (128 hex chars)
- `PORTAINER_ADMIN_PASSWORD` - Senha admin Portainer (32 chars)

#### Auto-configuradas (após deployments):
- `STORAGE_ACCESS_KEY_ID` - Minio access key (gerada após stack 7)
- `STORAGE_SECRET_ACCESS_KEY` - Minio secret key (gerada após stack 7)

### 3. **Stack Deployment**

As stacks são deployadas na seguinte ordem:

#### Bootstrap (Docker CLI):
1. **Traefik** - Reverse proxy e SSL
2. **Portainer** - Gerenciamento de containers
   - Após deploy: Inicializa API automaticamente

#### Via Portainer API (visível no Portainer UI):
3. **Redis** - Cache global
4. **Redis CW** - Cache Chatwoot
5. **PostgreSQL** - Banco de dados
6. **RabbitMQ** - Fila de mensagens
7. **Minio** - Object storage (S3-compatible)
   - Após deploy: Cria bucket "chatwoot" e gera access keys
8. **n8n Editor** - Interface de workflows
9. **n8n Webhook** - Receptor de webhooks
10. **n8n Worker** - Processador de jobs
11. **Chatwoot Admin** - Aplicação principal
    - Após deploy: Executa `db:chatwoot_prepare`
12. **Chatwoot Sidekick** - Worker background

## 🎯 Acesso aos Serviços

Após a instalação, os serviços estarão disponíveis em:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Portainer** | `https://manager.{DOMINIO}` | Gerenciamento de containers |
| **Chatwoot** | `https://crm.{DOMINIO}` | CRM e atendimento |
| **n8n Editor** | `https://automacao.{DOMINIO}` | Criação de workflows |
| **n8n Webhook** | `https://eventos.{DOMINIO}` | Recebimento de webhooks |
| **Minio Console** | `https://s3console.{DOMINIO}` | Interface do storage |
| **Minio API** | `https://s3storage.{DOMINIO}` | API S3 |
| **RabbitMQ** | `https://fila.{DOMINIO}` | Interface de gerenciamento |

## 🔐 Credenciais

### Localização das Credenciais

Todas as credenciais são exibidas no **final da instalação** e salvas em:

```bash
/root/portainer_credentials.txt
```

Para visualizar posteriormente:
```bash
cat /root/portainer_credentials.txt
```

### Credenciais Exibidas

O script exibe no final:
- ✅ **Portainer:** Usuário e senha admin
- ✅ **Minio:** Root user e password
- ✅ **PostgreSQL:** Senha do usuário postgres
- ✅ **RabbitMQ:** Usuário e senha

### ⚠️ IMPORTANTE: Salve as Credenciais!

**COPIE E SALVE** todas as credenciais exibidas no final da instalação, pois:
- São geradas aleatoriamente e não podem ser recuperadas
- O arquivo `/root/portainer_credentials.txt` contém apenas credenciais do Portainer
- Outras credenciais (Minio, PostgreSQL, RabbitMQ) são exibidas apenas uma vez

**Recomendação:** Use um gerenciador de senhas seguro para armazenar todas as credenciais.

## 📦 Gerenciamento via Portainer

### Primeira Vez Acessando Portainer

1. Acesse: `https://manager.{DOMINIO}`
2. Use as credenciais salvas em `/root/portainer_credentials.txt`
3. Você verá todas as stacks deployadas (exceto Traefik e Portainer que foram bootstrap)

### O que você pode fazer no Portainer:

✅ **Visualizar Stacks** - Ver todas as stacks deployadas
✅ **Editar Stacks** - Modificar compose files via UI
✅ **Restart Services** - Reiniciar serviços individuais
✅ **Ver Logs** - Acessar logs de containers
✅ **Métricas** - Monitorar CPU, memória, rede
✅ **Rollback** - Reverter mudanças
✅ **Update** - Atualizar stacks com novos compose files

### Stacks Visíveis no Portainer

Após a instalação, você verá no Portainer:
- `3_redis`
- `4_redis_cw`
- `5_postgres`
- `6_rabbitmq`
- `7_minio`
- `8_n8n_editor`
- `9_n8n_webhook`
- `10_n8n_worker`
- `11_chatwoot_admin`
- `12_chatwoot_sidekick`

**Nota:** As stacks `1_traefik` e `2_portainer` foram deployadas via Docker CLI (bootstrap) e não aparecem no Portainer, mas podem ser gerenciadas via CLI:
```bash
docker stack ls
docker service ls
```

## 🔄 Re-execução e Atualizações

### Re-executar o Instalador

Você pode re-executar o instalador para atualizar stacks:

```bash
curl -sL https://raw.githubusercontent.com/lucasvnd/infra/main/setup_public.sh | bash
```

O que acontece:
- Stacks existentes são **atualizadas** (não recriadas do zero)
- Variáveis são solicitadas novamente
- Senhas auto-geradas são **regeneradas** (cuidado!)
- Portainer tenta criar novo admin (erro 409 se já existir - ok!)

### Atualizar uma Stack Específica

Via Portainer UI:
1. Vá em **Stacks** → Selecione a stack
2. Clique em **Editor**
3. Modifique o compose file
4. Clique em **Update the stack**

Via CLI:
```bash
docker stack deploy -c stack.yaml nome_da_stack
```

## 🐛 Troubleshooting

### Problema: Portainer API timeout
**Sintoma:** Mensagem "Portainer did not become ready in time"
**Solução:** O script automaticamente faz fallback para Docker CLI. As stacks funcionarão normalmente, mas não aparecerão no Portainer UI.

### Problema: Stack não aparece no Portainer
**Causa 1:** Foi deployada via Docker CLI (stacks 1-2 são bootstrap)
**Causa 2:** Portainer API não estava disponível durante deploy
**Solução:** Re-execute o instalador ou deploy manualmente via Portainer UI

### Problema: Erro 409 ao criar admin Portainer
**Causa:** Admin já existe (comum em re-execução)
**Solução:** Isso é esperado e ok! O script continua normalmente e autentica com o admin existente.

### Problema: Erro "GITHUB_TOKEN required"
**Causa:** Token não foi fornecido ou expirou
**Solução:** Gere um novo token em https://github.com/settings/tokens

### Problema: Serviço não inicia
**Debug:**
```bash
# Ver status de todos os serviços
docker service ls

# Ver logs de um serviço específico
docker service logs <service_name>

# Ver tasks e erros
docker service ps <service_name> --no-trunc
```

### Problema: Certificado SSL não funciona
**Causa:** Let's Encrypt precisa de DNS apontando para o servidor
**Solução:**
1. Verifique se o domínio aponta para o IP do servidor
2. Aguarde propagação DNS (pode levar até 48h)
3. Reinicie o Traefik: `docker service update --force 1_traefik_traefik`

## 🔧 Comandos Úteis

### Verificar Status
```bash
# Listar stacks
docker stack ls

# Listar todos os serviços
docker service ls

# Verificar logs de um serviço
docker service logs -f 11_chatwoot_admin_chatwoot_admin

# Ver detalhes de um serviço
docker service inspect 11_chatwoot_admin_chatwoot_admin
```

### Gerenciar Stacks
```bash
# Remover uma stack
docker stack rm nome_da_stack

# Atualizar uma stack
docker stack deploy -c stack.yaml nome_da_stack

# Escalar um serviço
docker service scale 11_chatwoot_admin_chatwoot_admin=2
```

### Acessar Container
```bash
# Listar containers
docker ps

# Acessar shell de um container
docker exec -it <container_id> bash

# Executar comando em um container
docker exec <container_id> bundle exec rails console
```

## 🌐 Adicionar Worker Nodes (Opcional)

O instalador salva o comando de join do Swarm. Para adicionar workers:

1. No servidor manager, visualize o comando:
```bash
cat swarm_join_token.txt
```

2. No servidor worker, execute o comando exibido (exemplo):
```bash
docker swarm join --token SWMTKN-1-xxxxx manager-ip:2377
```

## 📚 Arquitetura

### Networking
- **Rede:** `network_swarm_public` (overlay)
- **Modo:** Docker Swarm (cluster mode)
- **Ingress:** Traefik gerencia todo tráfego HTTP/HTTPS
- **SSL:** Let's Encrypt automático via Traefik

### Persistência
Todos os dados são armazenados em Docker volumes:
- `traefik_certificates` - Certificados SSL
- `portainer_data` - Dados do Portainer
- `redis_data` - Cache Redis
- `redis_cw_data` - Cache Redis Chatwoot
- `postgres_data` - Banco de dados PostgreSQL
- `rabbitmq_data` - Dados RabbitMQ
- `minio_data` - Object storage
- `n8n_data` - Workflows n8n
- `chatwoot_storage` - Arquivos Chatwoot
- `chatwoot_public` - Assets públicos
- `chatwoot_mailer` - Templates email

### Deployment Strategy
- **Placement:** Todos os serviços no manager node
- **Replicas:** 1 por serviço (pode escalar depois)
- **Update:** Rolling update (zero downtime)
- **Restart:** On failure (auto-restart)

## 🔒 Segurança

### Senhas Auto-geradas
- Algoritmo: `secrets.choice()` (criptograficamente seguro)
- Comprimento: 16-128 caracteres dependendo do serviço
- Caracteres: Alfanuméricos (A-Z, a-z, 0-9)

### Recomendações
✅ Salve todas as credenciais em gerenciador de senhas
✅ Configure firewall (UFW) para permitir apenas portas 80, 443, 2377
✅ Habilite backup automático dos volumes Docker
✅ Configure SMTP com credenciais específicas (não use conta pessoal)
✅ Monitore logs regularmente
✅ Mantenha Docker e imagens atualizados

## 📞 Suporte

### Logs de Instalação
Todo output do instalador é exibido no terminal. Se precisar debugar:
```bash
# Re-executar com mais verbose
bash -x setup_public.sh
```

### Verificar Saúde dos Serviços
```bash
# Via Docker
docker service ls

# Via Portainer
# Acesse https://manager.{DOMINIO} → Services
```

## 🎓 Próximos Passos

Após instalação bem-sucedida:

1. ✅ **Acesse Portainer** e familiarize-se com a interface
2. ✅ **Configure Chatwoot** - Crie a conta admin inicial
3. ✅ **Configure n8n** - Configure workflows de automação
4. ✅ **Teste SMTP** - Verifique se emails estão sendo enviados
5. ✅ **Configure backup** - Implemente estratégia de backup dos volumes
6. ✅ **Monitore recursos** - Verifique uso de CPU/RAM no Portainer
7. ✅ **Documente** - Anote suas customizações e configurações

---

**Documentação criada em:** 2024
**Versão:** 2.0 (com Portainer API)
**Compatível com:** Debian, Ubuntu, RHEL, Fedora, Alpine, Arch
