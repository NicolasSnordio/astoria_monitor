# Astoria Monitor

Sistema local de monitoramento das estacoes da rede Astoria.

Este projeto e independente: nao compartilha codigo, tabelas, migracoes ou
arquivos com outros sistemas internos. Em desenvolvimento, roda localmente com
SQLite; depois pode apontar para PostgreSQL no servidor ASTORIADADOS usando um
banco proprio.

## Primeiro uso local

No PowerShell, dentro desta pasta:

```powershell
.\scripts\run_dev.ps1
```

Depois acesse:

```text
http://127.0.0.1:8000
```

Login local inicial:

```text
usuario: admin
senha: admin
permissao: 100%
```

Para enviar um teste da propria maquina:

```powershell
.\scripts\send_heartbeat.ps1
```

Mantenha o `run_dev.ps1` aberto em um PowerShell. Para enviar a coleta local,
abra um segundo PowerShell na mesma pasta e execute o `send_heartbeat.ps1`.

## Banco local

Por padrao, o SQLite fica em:

```text
data/astoria_monitor.db
```

## Futuro PostgreSQL

Quando o MVP estiver validado, configure no servidor:

```text
DATABASE_URL=postgresql+psycopg://usuario:senha@ASTORIADADOS:5432/astoria_monitor
```

O banco do monitoramento deve permanecer separado de qualquer outro sistema.

## Cadastro inicial

Os dados genericos de demonstracao foram removidos. O cadastro inicial de ativos
deve ser carregado uma unica vez a partir da planilha administrativa:

```powershell
.\scripts\seed_assets_from_excel.ps1 "C:\caminho\para\planilha.xlsx"
```

O sistema nao possui tela de importacao de planilhas. Depois da carga inicial,
a planilha deve ser substituida pela consulta no Astoria Monitor.

## Agente via AD/GPO

O caminho recomendado para instalar o agente nos computadores reais e via
Active Directory/GPO. Consulte:

```text
docs/ad_gpo_agent_deployment.md
```

O instalador de dominio fica em:

```text
scripts/install_agent_gpo.ps1
```

Ele copia o coletor para `C:\ProgramData\AstoriaMonitor` e cria uma tarefa
agendada para enviar as coletas automaticamente.

## Versao

A versao atual e controlada em:

```text
backend/app/version.py
pyproject.toml
CHANGELOG.md
```

Ela tambem aparece no dropdown do usuario na interface web.
| `#c93c5b` | Linha vermelha inferior da navbar |
| `rgba(255,255,255,0.78)` | Vidro base dos paineis |
| `rgba(122,164,212,0.34)` | Borda glassmorphism |
| `#071a3b` | Sombra profunda do layout |
