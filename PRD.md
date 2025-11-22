# PRD - Script de Instalação Automática para Ambiente Chatwoot

## Objetivo
Automatizar a instalação e configuração completa das aplicações necessárias para rodar o Chatwoot, garantindo instalação “one-click”, coletando poucos dados do cliente e configurando serviços essenciais com segurança e performance.

---

## Escopo
- Instalar e configurar Traefik, Portainer, Redis (global e Chatwoot), Postgres, RabbitMQ, n8n, MinIO e Chatwoot.
- Gerar e gerenciar automaticamente credenciais e segredos.
- Criar bucket no MinIO com permissão pública específica para Chatwoot.
- Configurar SMTP para envio de emails via n8n e Chatwoot.
- Scripts de instalação sequenciais, idempotentes e com logs.

---

## Fluxo e Detalhamento das Etapas

### 1) Traefik
- Instalar Traefik via docker-compose ou container.
- Recolher email do cliente para emissão automática de certificados SSL.
- Configurar proxy reverso com domínio do cliente.

### 2) Portainer
- Instalar Portainer para gerenciamento das stacks Docker.

### 3) Redis (global)
- Instalação padrão, sem necessidade de configurações extras.

### 4) Postgres
- Gerar senha segura, sem caracteres especiais, garantindo complexidade e tamanho mínimo.
- Instalar Postgres.
- Criar dois bancos de dados: `n8n` e `cwdb`.
- Garantir que senha e banco estejam prontos para uso por aplicações dependentes.

### 5) Redis para Chatwoot
- Instalar sem configuração adicional.

### 6) RabbitMQ
- Gerar usuário e senha seguindo padrão do Postgres.
- Configurar permissões básicas para Chatwoot e n8n.

### 7) n8n
- Gerar secret key seguindo padrão da senha do Postgres.
- Coletar dados SMTP: host, porta, usuário, senha e remetente.
- Configurar SMTP para envio de emails.

### 8) MinIO
- Gerar automaticamente access key e secret key (usuário admin) no início do serviço via variáveis de ambiente.
- Instalar MinIO.
- Criar bucket chamado "chatwoot" automaticamente.
- Configurar bucket para acesso público (somente leitura pública).
- Registrar as credenciais geradas para uso pelo Chatwoot.

### 9) Chatwoot
- Instalar Chatwoot via container.
- Configurar Chatwoot para usar MinIO config (endpoint, access key e secret key) para armazenamento.
- Configurar o envio de emails usando SMTP configurado no n8n.
- Subir as stacks relacionadas no Docker.

---

## Dados a Coletar Para Automação

| Serviço    | Dados Necessários                                 | Validação/Fórmato                          |
|------------|--------------------------------------------------|-------------------------------------------|
| Traefik    | Email para emissão de certificados SSL            | Email válido                              |
| Domínio    | Domínio público para aplicação e proxy reverso    | Ex: dominio.com, dominio.com.br           |
| Postgres   | Nenhum (senha gerada automaticamente)             | Senha forte, sem caracteres especiais      |
| RabbitMQ   | Nenhum (usuário e senha gerados automaticamente) | Mesma regra de senha que Postgres         |
| n8n        | SMTP: host, porta, usuário, senha, remetente      | Dados válidos para SMTP                    |
| MinIO      | Nenhum (gerar access key e secret key automático) |                                            |

---

## Regras e Considerações

- Senhas geradas devem ter no mínimo 16 caracteres, conter letras maiúsculas, minúsculas e números.
- Senhas sem caracteres especiais para evitar problemas de parsing em variáveis de ambiente.
- Todos os containers devem iniciar de forma ordenada, respeitando dependências.
- Configurações sensíveis devem ser armazenadas em variáveis de ambiente e arquivos .env.
- Logs de cada etapa do processo devem ser gerados para auditoria e troubleshooting.
- Caso alguma etapa falhe, o script deve apontar erro claro e abortar ou tentar recuperação se possível.

---

## Tecnologias e Ferramentas

- Docker e Docker Compose para orquestração.
- MinIO Client (mc) para manipulação automatizada de buckets e usuários no MinIO.
- Shell Script / Bash para execução sequencial e controle do fluxo de instalação.
- OpenSSL ou utilitários semelhantes para geração de senhas seguras.
- Certbot ou integração com Let’s Encrypt via Traefik para SSL automático.

---

## Entregáveis

- Script shell ou conjunto de scripts para instalação completa com configuração automática.
- Arquivo de configuração que recebe as informações coletadas do cliente.
- Documentação clara para execução do script e provisionamento das variáveis de entrada.
- Estrutura de logging para acompanhar o status da instalação.
- Procedimento para atualização/rollback do ambiente instalado.

---

Este PRD serve como guia detalhado para desenvolvimento do script "one-click" para instalação e configuração do ambiente Chatwoot completo, incluindo todos os componentes e automações de geração e uso de credenciais.

