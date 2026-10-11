# 🚀 Study Reviewer — Manual de Operações e DevOps (Produção)

Este documento descreve a arquitetura de produção, o pipeline de integração e entrega contínua (CI/CD), a execução de migrações de banco de dados, gestão de segredos e os procedimentos de rollback e monitoramento do **Study Reviewer**.

---

## 1. 🏗️ Arquitetura de Produção (100% Custo R$ 0,00)

O Study Reviewer adota uma arquitetura Serverless moderna na AWS aproveitando os limites perpétuos do **AWS Free Tier** somados ao tier gratuito gerenciado da **Neon** (PostgreSQL Serverless) e **Google Cloud** (OAuth/Gemini):

```mermaid
flowchart TD
    subgraph GitHub["GitHub (CI/CD Automation)"]
        PR["Merge na branch main"]
        CI["CI: Linters, Testes e Tipagem"]
        CD["CD: Deploy Serverless AWS"]
        MIG["Alembic Migrations (upgrade head)"]
        ECR_PUSH["Build Docker & Push ECR (:production, :sha)"]
        CFN["CloudFormation Deploy Stack"]
        SMOKE["Smoke Test (/health)"]
    end

    subgraph AWS["AWS Cloud (sa-east-1)"]
        ECR["Amazon ECR (study-reviewer)"]
        LAMBDA["AWS Lambda (study-reviewer-production)\n+ aws-lambda-adapter + Uvicorn"]
        FURL["Lambda Function URL (HTTPS Público Gratuito)"]
        DDB["Amazon DynamoDB (study_events_production)\nPay-Per-Request + TTL 90d"]
        CW["Amazon CloudWatch Logs"]
    end

    subgraph External["Serviços Gerenciados Externos"]
        NEON["Neon Serverless PostgreSQL\n(15 Tabelas + Conexões SSL)"]
        GOOGLE["Google Identity (OAuth 2.0 / OIDC)\n+ Google Gemini 3.8 Flash AI"]
    end

    PR --> CI
    CI --> CD
    CD --> MIG
    MIG --> NEON
    CD --> ECR_PUSH
    ECR_PUSH --> ECR
    CD --> CFN
    CFN --> LAMBDA
    CFN --> DDB
    CFN --> FURL
    ECR --> LAMBDA
    LAMBDA --> NEON
    LAMBDA --> DDB
    LAMBDA --> GOOGLE
    LAMBDA --> CW
    CD --> SMOKE
    SMOKE --> FURL
```

---

## 2. ⚡ Pipeline de Deploy Contínuo (CD)

O workflow está configurado no arquivo [`.github/workflows/deploy-aws.yml`](file:///.github/workflows/deploy-aws.yml).

### Gatilhos de Execução:
1. **Merge na `main`**:
   - Qualquer commit ou Pull Request aprovado e mergeado na branch `main` dispara o deploy **diretamente para Produção** (`TARGET_ENV=production`).
2. **Merge na `staging`**:
   - Dispara o deploy para o ambiente de homologação (`TARGET_ENV=staging`).
3. **Workflow Dispatch Manual**:
   - Permite acionar manualmente pela interface do GitHub Actions (`Actions` -> `CD — Deploy Serverless AWS (Always Free)` -> `Run workflow`), escolhendo o ambiente desejado (`production` ou `staging`) ou apenas consultando logs do CloudWatch.

### Garantia de Execução de Migrações:
- O step **Execute Alembic Database Migrations** executa `uv run alembic upgrade head` antes de qualquer alteração na infraestrutura ou envio de nova imagem para o Lambda.
- Se a variável `DATABASE_URL` não estiver definida ou se qualquer script de migração falhar, o pipeline é **imediatamente interrompido com erro**, impedindo que a versão em produção rode com schema defasado.

---

## 3. 🔐 Matriz de Segredos (GitHub Secrets)

Para que o deploy funcione perfeitamente, configure os seguintes segredos no repositório (**Settings -> Secrets and variables -> Actions**):

| Segredo | Obrigatório? | Descrição | Exemplo |
| :--- | :---: | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | **Sim** | Access Key do usuário IAM com permissão para ECR, Lambda e CloudFormation | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | **Sim** | Secret Key correspondente da AWS | `wJalrXUtnFEMI...` |
| `AWS_REGION` | Não | Região da AWS (padrão: `sa-east-1` - São Paulo) | `sa-east-1` |
| `DATABASE_URL` | **Sim** | String de conexão PostgreSQL Neon Serverless com SSL | `postgresql://user:pass@ep-...sa-east-1.aws.neon.tech/neondb?sslmode=require` |
| `PROD_DATABASE_URL` | Opcional | URL específica de produção (se desejar isolar de staging) | `postgresql://...` |
| `SECRET_KEY` | **Sim** | Chave secreta de 32 bytes para criptografia AES-256-GCM das sessões | Gerar via `openssl rand -hex 16` |
| `GOOGLE_CLIENT_ID` | **Sim** | Client ID do Google Cloud Console para Login Social | `123...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | **Sim** | Client Secret do Google Cloud Console | `GOCSPX-...` |
| `GOOGLE_REDIRECT_URI` | Opcional | URI fixa de callback. Se omitida, o Lambda infere dinamicamente com base no host HTTPS | `https://<url-da-function>.lambda-url.sa-east-1.on.aws/auth/callback` |
| `GEMINI_API_KEY` | Recomendado | Chave da API do Google AI Studio para avaliações pedagógicas inteligentes | `AIzaSy...` |
| `REDIS_URL` | Opcional | URL do Redis Serverless (ex: Upstash) para cache e filas efêmeras | `redis://default:...@...upstash.io:6379` |

---

## 4. 🌐 Configuração do Google OAuth em Produção

Após a primeira execução do deploy em produção, a AWS gerará uma URL pública exclusiva para a Function URL de produção.

1. Acesse o **[Google Cloud Console](https://console.cloud.google.com/apis/credentials)**.
2. Selecione seu projeto e abra as configurações do seu **OAuth 2.0 Client ID**.
3. Em **URIs de redirecionamento autorizados** (*Authorized redirect URIs*), adicione:
   ```text
   https://<sua-url-de-producao>.lambda-url.sa-east-1.on.aws/auth/callback
   ```
4. Em **Origens JavaScript autorizadas** (*Authorized JavaScript origins*), adicione:
   ```text
   https://<sua-url-de-producao>.lambda-url.sa-east-1.on.aws
   ```
5. Clique em **Salvar**. A autenticação via Google OAuth funcionará imediatamente em produção.

---

## 5. 🔄 Procedimento de Rollback Imediato

Se uma nova versão em produção apresentar comportamento inesperado, o rollback pode ser feito em **menos de 30 segundos**:

### Opção A: Via AWS CLI
Cada deploy cria uma tag imutável no ECR com o SHA do commit (ex: `${{ github.sha }}`). Para reverter para uma versão anterior:
```bash
aws lambda update-function-code \
  --function-name study-reviewer-production \
  --image-uri "<ACCOUNT_ID>.dkr.ecr.sa-east-1.amazonaws.com/study-reviewer:<SHA_DO_COMMIT_ANTERIOR>" \
  --region sa-east-1
```

### Opção B: Via GitHub Actions
1. Vá na aba **Actions** do GitHub.
2. Selecione a execução anterior estável do workflow **CD — Deploy Serverless AWS**.
3. Clique em **Re-run all jobs**.

---

## 6. 📊 Observabilidade e Monitoramento

- **Health Check Público**: `GET https://<prod-url>/health`
  - Retorna `{"status": "healthy", "app": "Study Reviewer", "environment": "production", "storage": "dynamodb"}`.
- **Buffer de Telemetria e Logs**: `GET https://<prod-url>/health/logs`
  - Fornece inspeção imediata dos logs em tempo de execução sem latência do CloudWatch.
- **CloudWatch Logs via GitHub Actions**:
  - Para consultar logs diretamente pelo GitHub sem acessar o console AWS, acione o workflow com o input `fetch_logs_only: true`.
