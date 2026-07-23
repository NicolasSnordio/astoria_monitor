# Distribuicao do agente via AD/GPO

Este e o caminho recomendado para a Astoria quando o agente sair do piloto e
passar a ser instalado nas estacoes do dominio.

## Fluxo

1. Carregar o cadastro inicial de ativos no banco do Astoria Monitor.
2. Publicar o agente em um compartilhamento interno somente leitura.
3. Criar um script de instalacao silenciosa.
4. Distribuir o script por GPO para as OUs das estacoes.
5. Acompanhar no painel quais maquinas coletaram e quais seguem sem coleta.

## Cadastro inicial

Use a planilha apenas uma vez, como fonte administrativa:

```powershell
.\scripts\seed_assets_from_excel.ps1 "C:\caminho\para\planilha.xlsx"
```

Depois disso, a consulta deve ser feita pelo Astoria Monitor.

## Coleta real

O agente deve coletar automaticamente:

- hostname;
- usuario logado;
- IP;
- Windows e versao;
- fabricante;
- modelo;
- serial/service tag;
- CPU;
- memoria;
- disco e espaco livre;
- uptime.

Dados como setor, responsavel, patrimonio, compra, garantia, monitor e Office
continuam como cadastro administrativo do ativo.

## Estrategia segura

- Comecar com uma OU piloto de 2 a 5 computadores.
- Usar token do agente em `AGENT_SHARED_TOKEN`.
- Rodar a coleta em intervalo controlado, por exemplo 5 ou 10 minutos.
- Registrar versao do agente em cada coleta quando o agente definitivo existir.
- So ampliar a GPO depois que a tela mostrar as maquinas piloto corretamente.

## Instalacao por GPO

1. Criar um compartilhamento interno somente leitura, por exemplo:

```text
\\ASTORIADADOS\AstoriaMonitorAgent
```

2. Copiar para esse compartilhamento os arquivos:

```text
scripts\send_heartbeat.ps1
scripts\install_agent_gpo.ps1
```

3. Criar uma GPO de computador para a OU piloto e executar o instalador como
script de inicializacao:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "\\ASTORIADADOS\AstoriaMonitorAgent\install_agent_gpo.ps1" -ServerUrl "http://ASTORIADADOS:8000" -Token "TOKEN_DO_AGENTE" -IntervalMinutes 5
```

O instalador copia o coletor para `C:\ProgramData\AstoriaMonitor`, grava a
configuracao local com permissao apenas para `SYSTEM` e administradores, cria a
tarefa agendada `Astoria Monitor Agent` e executa uma primeira coleta.

4. Validar no painel:

- maquinas da OU piloto devem sair de `Sem coleta`;
- maquinas fora da OU devem continuar como `Sem coleta`;
- divergencias de hostname ou maquinas nao cadastradas devem aparecer como
  `Atencao`.

## Estados esperados no painel

- `Sem coleta`: ativo cadastrado, mas agente ainda nao reportou.
- `Atencao`: ativo coletado com alerta ou divergencia.
- `Offline`: ativo parou de reportar dentro da janela configurada.
- `Online`: ativo coletando sem alerta.
