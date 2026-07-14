# Auxiliador de Processos Logísticos — SAC

Sistema desktop em Python para apoiar a rotina do setor de SAC de uma transportadora:
cadastro de notas fiscais (NF), acompanhamento de ocorrências, lembretes automáticos,
agendamentos e relatórios.

## Requisitos

- **Python 3.8** (recomendado para compatibilidade com **Windows 7**; versões do
  CPython a partir da 3.9 não oferecem mais suporte oficial ao Windows 7/8).
  Em Windows 10/11 ou Linux, qualquer Python 3.8+ funciona normalmente.
- Nenhuma biblioteca externa é necessária: o sistema usa apenas `tkinter` (interface
  gráfica) e `sqlite3` (banco de dados), ambos inclusos na biblioteca padrão do Python.
  Isso também é o que garante a portabilidade futura para Linux sem precisar reescrever nada.

## Como executar

```
python main.py
```

Na primeira execução, o sistema cria automaticamente o arquivo `sac_logistica.db`
(SQLite) na mesma pasta do programa, já com as ocorrências padrão (Reentrega,
Mudou-se, Localização, Acompanhar, Comprovante, Priorizar entrega, Agendamento,
Outros) e as empresas parceiras padrão (Agex, Risso) cadastradas.

## Gerando um .exe para Windows (opcional)

Caso queira distribuir como um executável único para quem não tem Python instalado:

```
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

O executável ficará em `dist/main.exe`. O arquivo `sac_logistica.db` será criado
ao lado do `.exe` na primeira execução.

## Estrutura dos arquivos

- `main.py` — ponto de entrada.
- `app.py` — janela principal, formulário de cadastro, lista de notas, menus e o
  laço que verifica lembretes/agendamentos/prioridades periodicamente.
- `dialogs.py` — janelas de pop-up (marcar como resolvido, lembretes, edição de
  campos, gerenciamento de listas).
- `database.py` — toda a camada de banco de dados (SQLite).
- `dateutils.py` — interpretação das datas digitadas e dos códigos de lembrete.
- `occorrencias.py` — constantes de negócio (ocorrências padrão, unidades filiais,
  regras de sugestão/autocomplete).

## Funcionalidades implementadas

- Cadastro de NF, cliente/remetente, ocorrência (com sugestão automática por
  prefixo, ex: digitar "prio" sugere "Priorizar entrega") e sigla da unidade ou
  nome da empresa parceira (Agex, Risso — editável em **Cadastros → Empresas
  parceiras**, permitindo incluir/excluir conforme novas parcerias).
- Verificação de duplicidade (mesma NF + cliente + ocorrência) com aviso e
  destaque da nota já existente.
- Bloco de visualização de cada nota conforme o layout solicitado, com as
  atualizações de tratativas (data/hora + texto) listadas abaixo.
- Clique simples sobre o cabeçalho da nota copia o número da NF para a área de
  transferência e mostra "Número copiado!". Duplo clique abre um campo para
  adicionar uma nova atualização de tratativa.
- Menu de contexto (botão direito): marcar como resolvido, adicionar/remover
  lembrete, editar NF, remetente, ocorrência e sigla.
- Fluxo de "marcar como resolvido": pergunta se a unidade entregadora foi ágil
  e, em seguida, se o remetente foi ágil, salvando os dias de tratativa no
  histórico/relatório (histórico com expiração automática de 60 dias, além de
  poder ser apagado manualmente na tela de Relatório).
- Relatório com "Unidades/siglas com mais ocorrências" e "Tempo médio para
  solução do caso".
- Cadastro de novos tipos de ocorrência, tanto ao digitar uma ocorrência não
  reconhecida (o sistema pergunta se deseja cadastrá-la) quanto pela tela
  **Cadastros → Tipos de ocorrência**.
- Lógica de datas: `0` = data atual; `1` a `31` (um ou dois dígitos) = dia do
  mês/ano correntes; 8 dígitos = data completa `ddmmaaaa`.
- Lógica de lembretes periódicos: sugerida automaticamente após inserir uma
  nota com ocorrência Reentrega, Mudou-se, Localização, Acompanhar ou
  Priorizar entrega. Números de 1 a 50 = minutos; acima de 50, o sistema
  arredonda para o código de hora válido mais próximo (100=1h, 130=1h30,
  200=2h, 230=2h30, 300=3h, 330=3h30, 400=4h — limite máximo).
- Agendamento: ao usar a ocorrência "Agendamento"/"Agenda", o sistema pede a
  data (mesma lógica de datas) e recusa datas iguais ou anteriores a hoje.
  Notas de unidades filiais (BLU, TUB, FLN, CRI, CWB, SAO, JVL) recebem alerta
  às 14:30 do dia anterior ao agendamento. Notas de empresas/siglas parceiras
  recebem alerta às 10h e às 16h para acompanhamento diário até serem
  marcadas como "nota já verificada" — a partir daí passam a alertar apenas
  às 14:30 do dia anterior, como as filiais.
- Prioridade: ocorrências de "Priorizar entrega" também disparam um alerta
  fixo às 10h e às 17h, além do lembrete periódico escolhido pelo usuário.
- Busca por NF com `Ctrl+F` (foca o campo de busca) e `Enter` para localizar e
  destacar a nota entre as ativas.
- Navegação pelo formulário de cadastro usando apenas a tecla `Enter`: NF →
  Cliente/Remetente → Ocorrência → Sigla/Empresa → Data → (Enter na Data
  adiciona a nota), sem depender de clique ou de `Tab`.
- Bloco de cada nota agora exibe `DATA: dd/mm/aaaa HORA: hh:mm`, mostrando a
  data (conforme a lógica de datas existente) e o horário em que a ocorrência
  foi inserida no sistema.
- Novo tipo de ocorrência padrão: **Devolução**.
- Filtro por tipo de ocorrência acima da lista principal (ex.: mostrar somente
  "Agendamento", somente "Devolução", etc.), com opção de limpar o filtro e
  voltar a ver todas as notas ativas.
- Sugestão automática de remetente: ao digitar no campo Cliente/Remetente, o
  sistema sugere o nome com base nos remetentes já cadastrados (mesma lógica
  de prefixo usada nas ocorrências). Após inserir uma nota com um remetente
  ainda não cadastrado, o sistema pergunta se deseja cadastrá-lo para
  facilitar a sugestão nas próximas notas. A lista de remetentes também pode
  ser gerenciada em **Cadastros → Remetentes**.
- Pressionar `Enter` no campo Data (último campo do formulário) aciona
  exatamente o botão "Adicionar nota" (via `invoke()`), sem exigir clique do
  mouse.
- Notas com ocorrência "Agendamento" mostram no próprio bloco a data em que
  ficaram agendadas (`AGENDAMENTO: dd/mm/aaaa`).
- Novo filtro "Somente notas com lembrete", ao lado do filtro por ocorrência,
  para localizar rapidamente as notas que têm lembrete configurado.
- Navegação por teclado entre as notas: um clique em qualquer parte do bloco
  seleciona a nota (destaque azul); as setas ↑/↓ movem a seleção entre as
  notas ativas; a tecla `Delete` marca a nota selecionada como resolvida
  (mesmo fluxo de perguntas do menu de contexto); pressionar `Enter` sobre a
  nota selecionada abre a inserção de uma nova atualização de tratativa —
  o mesmo comportamento do duplo clique.
- Navegação por setas ↑/↓ entre os campos e botões do topo da tela: NF →
  Cliente/Remetente → Ocorrência → Sigla/Empresa → Data → botão "Adicionar
  nota" → campo "Buscar NF" → botão "Buscar" → "Filtrar por ocorrência" →
  botão "Limpar filtro" → "Somente notas com lembrete".
- Cliente/remetente, ocorrência e sigla/empresa são sempre convertidos para
  LETRAS MAIÚSCULAS automaticamente ao cadastrar uma nova nota, editar um
  campo existente ou cadastrar um novo tipo de ocorrência/remetente/empresa
  parceira pelas telas de Cadastros.

## Observações e simplificações assumidas

Algumas regras do documento original tinham redação um pouco ambígua; as
seguintes interpretações foram adotadas e podem ser ajustadas no código
conforme necessário:

1. **Arredondamento do código de lembrete acima de 50**: foi implementado como
   "arredondar para o valor de hora válido mais próximo dentre 100, 130, 200,
   230, 300, 330, 400", limitado a 400 (4h). Se a régua de arredondamento
   desejada for diferente, ajuste a lista `CODIGOS_HORA_VALIDOS` em
   `dateutils.py`.
2. **"Priorizar entrega" vs "Prioridade"**: o documento cita "Priorizar
   entrega" na lista de ocorrências principais, mas depois menciona lembretes
   fixos às 10h/17h para a ocorrência "prioridade". O sistema trata ambos os
   nomes como sinônimos e aplica tanto o lembrete configurável quanto o
   alerta fixo de 10h/17h.
3. A quantidade de "dias em tratativas" é calculada automaticamente a partir
   da data de inserção da nota; ao marcar como resolvido, esse valor é
   sugerido e pode ser confirmado/ajustado pelo usuário quando a resposta for
   "não" (não ágil).
4. O histórico de 60 dias é limpo automaticamente a cada abertura do sistema e
   a cada abertura da tela de Relatório, além de poder ser apagado
   manualmente a qualquer momento.

## Próximos passos sugeridos

- Empacotar com PyInstaller para gerar um instalador único para os
  atendentes que não tenham Python instalado.
- Se a base de usuários crescer muito, considerar migrar de SQLite para um
  banco cliente/servidor (ex. PostgreSQL) — a camada `database.py` foi escrita
  de forma isolada exatamente para facilitar essa troca no futuro, sem
  precisar alterar a interface gráfica.
