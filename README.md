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
(SQLite) na mesma pasta do programa, já com as ocorrências padrão (REENTREGA,
MUDOU-SE, LOCALIZAÇÃO, ACOMPANHAR, COMPROVANTE, PRIORIZAR ENTREGA, AGENDAMENTO,
DEVOLUÇÃO, OUTROS) e as empresas parceiras padrão (Agex, Risso) cadastradas.

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
- Fluxo de "marcar como resolvido": o sistema calcula automaticamente os dias
  e horas que a NF ficou em tratativas (sem perguntar nada disso ao usuário)
  e pergunta apenas quem demorou mais para resolver o caso — Unidade
  (clique ou tecla `U`), Cliente (clique ou tecla `C`) ou Sem morosidade
  (`Enter`). O resultado é salvo no histórico (expiração automática de 60
  dias, podendo também ser apagado manualmente na tela de Relatório).
- Relatório com: **Unidades com mais ocorrências** (top 5, da maior para a
  menor), **Tempo médio para solução do caso** (em dias e horas),
  **Unidades mais morosas** (top 5, da mais para a menos morosa) e
  **Clientes mais morosos** (top 5). A tela de Relatório também permite
  **buscar no histórico pelo número da NF**, mostrando todas as vezes em que
  aquela NF foi resolvida, com o tempo (dias e horas) e quem foi apontado
  como mais moroso em cada caso.
- Cada sigla listada nos rankings "Unidades com mais ocorrências" e
  "Unidades mais morosas" é clicável: um clique abre a lista das notas do
  histórico que embasam aquela posição no ranking (no caso das mais
  morosas, somente as notas em que aquela unidade foi apontada como a mais
  demorada).
- Interface responsiva: a lista de notas (incluindo o texto de cada bloco e
  das atualizações de tratativa) se reajusta automaticamente à largura da
  janela, quebrando as linhas de forma legível mesmo quando a janela é
  estreitada. O formulário de cadastro, a busca e os filtros também se
  ajustam à largura disponível.
- A busca (`Ctrl+F`) localiza notas ativas não só pelo número da NF, mas
  também pelo nome do cliente/remetente ou pela sigla da unidade (busca
  parcial, sem diferenciar maiúsculas/minúsculas).
- Ao filtrar por ocorrência "AGENDAMENTO", a lista é organizada pela data do
  agendamento em ordem crescente (a mais próxima primeiro, a mais distante
  por último) — e não pela data em que a ocorrência foi inserida no sistema.
- Menu de contexto com a opção **"Copiar informações da nota"**: copia para
  a área de transferência todo o conteúdo do bloco (NF, cliente, ocorrência,
  sigla, data/hora, dias em tratativas, lembrete e agendamento, se houver)
  junto com todas as atualizações de tratativa já registradas.
- Categorias de ocorrência fixas: REENTREGA, MUDOU-SE, LOCALIZAÇÃO,
  ACOMPANHAR, COMPROVANTE, PRIORIZAR ENTREGA, AGENDAMENTO, DEVOLUÇÃO e
  OUTROS. Qualquer texto digitado que não corresponda a uma dessas
  categorias (por nome exato ou por prefixo, ex.: "prio" → "PRIORIZAR
  ENTREGA") é classificado automaticamente como **OUTROS**, tanto ao
  cadastrar quanto ao editar a ocorrência de uma nota — sem perguntas ou
  necessidade de cadastro prévio.
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
- Cliente/remetente e sigla/empresa são sempre convertidos para LETRAS
  MAIÚSCULAS automaticamente ao cadastrar uma nova nota, editar um campo
  existente ou cadastrar um novo remetente/empresa parceira pelas telas de
  Cadastros (a ocorrência é resolvida para uma das categorias oficiais, já
  em maiúsculas, conforme explicado acima).
- Atalhos de edição de texto nos campos NF, Cliente, Ocorrência, Sigla/Empresa,
  Data, Buscar NF e Filtrar por ocorrência: `Ctrl+Z` desfaz a última alteração,
  `Ctrl+Y` refaz, `Ctrl+Backspace` apaga a palavra anterior ao cursor e
  `Ctrl+Delete` apaga a palavra seguinte.
- Ao digitar uma ocorrência ou um remetente já cadastrado, a sugestão exibida
  agora é colada automaticamente no campo ao pressionar `Enter` ou `Tab`
  (antes de avançar para o próximo campo).
- O campo "Filtrar por ocorrência" agora é digitável: conforme o usuário
  digita, a lista de opções do combobox é reduzida aos tipos correspondentes,
  agilizando a localização do tipo desejado; `Enter` aplica o filtro.

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
3. Os "dias e horas em tratativas" salvos no histórico ao marcar uma nota como
   resolvida são sempre calculados automaticamente a partir da data/hora de
   inserção da nota até o momento da resolução — o sistema não pergunta mais
   esse valor ao usuário, apenas quem foi mais moroso (unidade, cliente ou
   ninguém).
4. O histórico de 60 dias é limpo automaticamente a cada abertura do sistema e
   a cada abertura da tela de Relatório, além de poder ser apagado
   manualmente a qualquer momento.
5. **Correção de travamento**: o pop-up de alerta automático (lembrete
   periódico, agendamento e prioridade) não aguardava corretamente a resposta
   do usuário antes de continuar a verificação. Quando várias notas tinham
   lembretes vencidos ao mesmo tempo (comum logo ao abrir o sistema após um
   tempo fechado), isso podia abrir várias janelas modais em sequência disputando
   o controle da interface, travando a aplicação e exigindo encerrar pelo
   Gerenciador de Tarefas. Agora cada pop-up aguarda ser fechado antes do
   próximo ser exibido, eliminando esse travamento.

## Próximos passos sugeridos

- Empacotar com PyInstaller para gerar um instalador único para os
  atendentes que não tenham Python instalado.
- Se a base de usuários crescer muito, considerar migrar de SQLite para um
  banco cliente/servidor (ex. PostgreSQL) — a camada `database.py` foi escrita
  de forma isolada exatamente para facilitar essa troca no futuro, sem
  precisar alterar a interface gráfica.
