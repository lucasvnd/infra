# Migração para Deploy via Portainer API

## Visão Geral

Este documento descreve a implementação da migração do sistema de deploy de Docker CLI direto para deploy via Portainer API, permitindo que todas as stacks sejam gerenciadas através da interface do Portainer.

## Motivação

**Problema anterior:** As stacks eram deployadas via Docker CLI (`docker stack deploy`), o que funcionava perfeitamente mas não aparecia no Portainer UI. Isso tornava inviável o gerenciamento centralizado via Portainer.

**Solução implementada:** Após o deploy do Portainer (stack 2), o sistema agora:
1. Gera credenciais seguras para o admin do Portainer
2. Obtém um JWT token via API
3. Deploya todas as stacks restantes (3-12) via Portainer API
4. Mantém fallback para Docker CLI em caso de falha

## Arquivos Modificados

### 1. **portainer_api.py** (NOVO)
Módulo Python contendo a classe `PortainerAPI` com os seguintes métodos:

- `wait_for_portainer()` - Aguarda Portainer ficar disponível
- `initialize_admin()` - Cria usuário admin inicial
- `authenticate()` - Autentica e obtém JWT token
- `get_endpoint_id()` - Obtém ID do endpoint Docker Swarm
- `deploy_stack()` - Deploya stack via API
- `check_stack_status()` - Verifica status de deployment
- `_update_stack()` - Atualiza stack existente
- `_get_stack_id()` - Obtém ID de stack por nome
- `_check_stack_services()` - Verifica saúde dos serviços

### 2. **install.py** (MODIFICADO)

#### Novas Constantes
```python
PORTAINER_CREDENTIALS_FILE = "portainer_credentials.txt"
```

#### Novos Imports
```python
from portainer_api import PortainerAPI
```

#### Novas Funções

**`generate_portainer_password()`**
- Gera senha segura de 32 caracteres alfanuméricos
- Utiliza `secrets.choice()` para geração criptograficamente segura

**`initialize_portainer_api(env_values)`**
- Executada automaticamente após deploy da stack 2 (Portainer)
- Aguarda Portainer ficar pronto (timeout: 120s)
- Inicializa usuário admin com senha auto-gerada
- Autentica e obtém JWT token
- Obtém endpoint ID do Swarm
- Salva credenciais em `portainer_credentials.txt`
- Retorna instância de `PortainerAPI` configurada

#### Modificações em `deploy_stacks(env_values)`

**Fluxo de Deployment:**

1. **Stacks 1-2 (Bootstrap):**
   - Traefik e Portainer são deployados via **Docker CLI**
   - Após stack 2, `initialize_portainer_api()` é chamada automaticamente

2. **Stacks 3-12 (Via API):**
   - Deploy via **Portainer API** (`portainer_api.deploy_stack()`)
   - Verificação de status em tempo real (`check_stack_status()`)
   - Fallback automático para Docker CLI em caso de falha
   - Retry logic com backoff exponencial (3 tentativas)

3. **Post-Deploy Hooks:**
   - Mantidos inalterados (Minio stack 7, Chatwoot stack 11)
   - Continuam usando Docker CLI para comandos `mc` e `docker exec`

**Melhorias de Robustez:**
- Fallback para Docker CLI se Portainer API falhar
- Retry automático com backoff exponencial
- Timeout configurável para verificação de status
- Mensagens de log detalhadas para troubleshooting

#### Modificações na função `main()`
- Display de credenciais do Portainer no final da instalação
- Exibição de `PORTAINER_ADMIN_USER` e `PORTAINER_ADMIN_PASSWORD`

## Fluxo de Deployment

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VPS Setup (Docker Swarm + Network + Volumes)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Collect Variables & Generate Secrets                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Deploy Stack 1: Traefik (Docker CLI)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Deploy Stack 2: Portainer (Docker CLI)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Initialize Portainer API                                │
│    ├─ Wait for Portainer readiness                         │
│    ├─ Create admin user                                    │
│    ├─ Authenticate & get JWT token                         │
│    ├─ Get endpoint ID                                      │
│    └─ Save credentials to file                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Deploy Stacks 3-12 (Portainer API)                      │
│    ├─ Stack 3: Redis                                       │
│    ├─ Stack 4: Redis CW                                    │
│    ├─ Stack 5: PostgreSQL                                  │
│    ├─ Stack 6: RabbitMQ                                    │
│    ├─ Stack 7: Minio → [Hook: Configure bucket & keys]     │
│    ├─ Stack 8: n8n Editor                                  │
│    ├─ Stack 9: n8n Webhook                                 │
│    ├─ Stack 10: n8n Worker                                 │
│    ├─ Stack 11: Chatwoot Admin → [Hook: db:chatwoot_prepare]│
│    └─ Stack 12: Chatwoot Sidekick                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Display Service URLs & Credentials                      │
└─────────────────────────────────────────────────────────────┘
```

## Formato da API do Portainer

### Endpoint de Deploy
```http
POST /api/stacks?type=1&method=string&endpointId={endpoint_id}
Headers:
  Authorization: Bearer {jwt_token}
  Content-Type: application/json
Body:
{
  "Name": "stack_name",
  "SwarmID": "swarm_cluster_id",
  "StackFileContent": "version: '3.8'\nservices:\n  ..."
}
```

### Resposta de Sucesso
```json
{
  "Id": 123,
  "Name": "3_redis",
  "Type": 1,
  "EndpointId": 1,
  "SwarmId": "abc123...",
  "Status": 1,
  ...
}
```

## Arquivo de Credenciais

O arquivo `portainer_credentials.txt` é criado automaticamente com o seguinte formato:

```
Username: admin
Password: AbCd1234EfGh5678IjKl9012MnOp3456
Endpoint ID: 1
```

**Importante:** Este arquivo contém credenciais sensíveis e deve ser protegido adequadamente.

## Vantagens da Implementação

### ✅ Gerenciamento Centralizado
- Todas as stacks visíveis no Portainer UI
- Fácil atualização, restart e remoção de stacks
- Visualização de logs e métricas

### ✅ Rastreabilidade
- Histórico de deployments
- Tracking de mudanças
- Auditoria de operações

### ✅ Rollback Facilitado
- Rollback via interface gráfica
- Comparação de versões
- Restauração rápida

### ✅ Robustez
- Fallback automático para Docker CLI
- Retry logic com backoff exponencial
- Verificação de status em tempo real

### ✅ Segurança
- Senha admin auto-gerada (32 chars)
- JWT token para autenticação
- Credenciais salvas localmente

### ✅ Compatibilidade
- Zero mudanças nos arquivos YAML das stacks
- Mantém todos os hooks pós-deploy
- Mantém geração automática de variáveis

## Troubleshooting

### Problema: Portainer API não responde
**Solução:** O sistema automaticamente faz fallback para Docker CLI

### Problema: Timeout ao aguardar Portainer
**Causa:** Portainer pode demorar em VPS com recursos limitados
**Solução:** Timeout configurável (padrão: 120s), pode ser aumentado

### Problema: Stack não aparece no Portainer
**Causa:** Deployada via Docker CLI antes da inicialização da API
**Solução:** Apenas stacks 1-2 usam CLI (bootstrap necessário)

### Problema: Erro 409 ao deployar stack
**Causa:** Stack já existe
**Solução:** Sistema automaticamente tenta atualizar via `PUT /api/stacks/{id}`

## Dependências

### Python Packages
- `requests` - Para chamadas HTTP à API do Portainer (já presente no projeto)

### Requisitos do Sistema
- Portainer CE 2.33.4+ (conforme `2_portainer.yaml`)
- Docker Swarm mode ativo
- Acesso à porta 9000 do Portainer

## Compatibilidade com Versões Anteriores

A implementação é **100% retrocompatível**:
- Todos os arquivos YAML das stacks permanecem inalterados
- Hooks pós-deploy mantidos
- Geração de variáveis mantida
- Se Portainer API falhar, continua via Docker CLI

## Testes Recomendados

### Teste 1: Deploy Completo
```bash
python3 install.py
```
Verificar que:
- [ ] Stacks 1-2 deployam via Docker CLI
- [ ] Portainer API é inicializada automaticamente
- [ ] Stacks 3-12 aparecem no Portainer UI
- [ ] Arquivo `portainer_credentials.txt` é criado
- [ ] Credenciais exibidas no final da instalação

### Teste 2: Fallback para CLI
Simular falha da API (ex: parar Portainer durante deploy stack 5):
- [ ] Sistema detecta falha
- [ ] Faz fallback para Docker CLI automaticamente
- [ ] Continua deployment das stacks restantes

### Teste 3: Update de Stack Existente
Rodar `install.py` novamente:
- [ ] Stacks existentes são atualizadas via API
- [ ] Nenhum erro 409
- [ ] Serviços reiniciados corretamente

## Próximos Passos (Opcional)

### Melhorias Futuras Possíveis
1. **API Token Persistente:** Salvar JWT token em arquivo para reutilização
2. **Stack Templates:** Usar Portainer Stack Templates para deploys recorrentes
3. **Environment Variables:** Usar sistema nativo de env vars do Portainer
4. **Webhooks:** Configurar webhooks para notificações de deployment
5. **RBAC:** Configurar roles e permissões via API

### Integração CI/CD
O módulo `portainer_api.py` pode ser usado independentemente para:
- Deploy via GitHub Actions
- Deploy via GitLab CI
- Deploy via Jenkins
- Automação com scripts externos

Exemplo:
```python
from portainer_api import PortainerAPI

api = PortainerAPI("http://portainer.example.com:9000")
api.authenticate("admin", "password")
api.get_endpoint_id()

with open("stack.yaml") as f:
    content = f.read()

api.deploy_stack("my_stack", content)
```

## Conclusão

A migração para Portainer API foi implementada com sucesso, mantendo total compatibilidade com a infraestrutura existente e adicionando capacidades de gerenciamento centralizado. O sistema é robusto, com fallbacks automáticos e retry logic, garantindo alta disponibilidade mesmo em cenários de falha.
