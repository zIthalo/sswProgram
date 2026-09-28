# Auxiliador de Processos Logísticos — SAC

Sistema desktop em Python para apoiar a rotina do setor de SAC de uma transportadora:
cadastro de notas fiscais (NF), acompanhamento de ocorrências, agendamentos,
histórico e relatórios.

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
(SQLite) na mesma pasta do programa, já com as categorias oficiais de ocorrência
e as empresas parceiras padrão (Agex, Risso) cadastradas.

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
- `app.py` — janela principal, formulário de cadastro, lista de notas, menus
  (Cadastros, Relatório, Histórico) e toda a interação do usuário.
- `dialogs.py` — janelas de pop-up (marcar como resolvido/morosidade, edição de
  campos, gerenciamento de listas de Cadastros).
- `database.py` — toda a camada de banco de dados (SQLite).
- `dateutils.py` — interpretação das datas digitadas e cálculo de dias/horas.
- `occorrencias.py` — categorias oficiais de ocorrência e lógica de
  sugestão/autocomplete.

## Funcionalidades implementadas

### Cadastro de notas

- Cadastro de NF, cliente/remetente e sigla da unidade ou nome da empresa
  parceira (Agex, Risso — editável em **Cadastros → Empresas parceiras**,
  permitindo incluir/excluir conforme novas parcerias).
- Tipos de ocorrência sugeridos por padrão: REENTREGA, MUDOU-SE, LOCALIZAÇÃO,
  ACOMPANHAR, COMPROVANTE, PRIORIZAR ENTREGA, AGENDAMENTO, DEVOLUÇÃO e
  OUTROS. Ao digitar, o sistema sugere o tipo por prefixo (ex.: "prio" →
  "PRIORIZAR ENTREGA"). Se o texto digitado não corresponder a nenhum tipo
  já cadastrado, o sistema pergunta se o usuário deseja cadastrar aquele
  novo tipo de ocorrência (tanto ao criar quanto ao editar a ocorrência de
  uma nota) — a lista de tipos também pode ser gerenciada diretamente em
  **Cadastros → Tipos de ocorrência**.
- A data de inserção da nota é sempre a data atual do sistema, definida
  automaticamente (não há mais campo de data manual no formulário).
- Sugestão automática de remetente: ao digitar no campo Cliente/Remetente
  (no formulário) ou no campo de busca, o sistema sugere o nome com base
  nos remetentes já cadastrados (prefixo). Pressionar `Enter` ou `Tab` cola
  a sugestão no campo. Ao inserir uma nota com um remetente novo, ele é
  **cadastrado automaticamente** para facilitar a sugestão em notas
  futuras — sem perguntar.
- Verificação de duplicidade (mesma NF + cliente + ocorrência) com aviso e
  destaque da nota já existente.
- Agendamento: ao usar a ocorrência "Agendamento", o sistema pede a data do
  agendamento (`0`=hoje, dia do mês, ou `ddmmaaaa`) e recusa datas iguais ou
  anteriores a hoje. A data agendada é exibida em negrito no bloco da nota
  (`AGENDAMENTO: dd/mm/aaaa`).
- Navegação pelo formulário usando apenas a tecla `Enter`: NF → Cliente →
  Ocorrência → Sigla/Empresa → (Enter na Sigla aciona o botão "Adicionar
  nota", exatamente como um clique). As setas ↑/↓ também navegam entre os
  campos e botões do topo da tela (formulário, busca e filtro), sem
  depender de `Tab`.
- Atalhos de edição de texto (`Ctrl+Z` desfazer, `Ctrl+Y` refazer,
  `Ctrl+Backspace` apaga a palavra anterior, `Ctrl+Delete` apaga a palavra
  seguinte) em todos os campos de texto/combobox editáveis.

### Visualização das notas

- Bloco de cada nota no formato `NF: ... / CLIENTE: ... / OCORRÊNCIA: ... /
  SIGLA UNIDADE: ... / DATA: dd/mm/aaaa HORA: hh:mm / DIAS EM TRATATIVAS:
  ...`, com **CLIENTE**, **OCORRÊNCIA** e **AGENDAMENTO** (quando houver)
  sempre exibidos em **negrito**, seguido das atualizações de tratativa
  (data/hora + texto).
- Clique em qualquer parte do bloco seleciona a nota (destaque azul); clique
  sobre o cabeçalho também copia o número da NF para a área de transferência
  ("Número copiado!"). Duplo clique (ou `Enter` com a nota selecionada) abre
  um campo para adicionar uma nova atualização de tratativa — o texto
  digitado é sempre salvo em **letras maiúsculas**.
- Navegação entre notas com as setas ↑/↓ do teclado; a tecla `Delete` marca
  a nota selecionada como resolvida.
- Menu de contexto (botão direito): marcar como resolvido, editar NF,
  remetente, ocorrência, sigla, e **"Copiar informações da nota"** (copia
  todo o conteúdo do bloco, incluindo as tratativas, para a área de
  transferência).
- Interface responsiva: a lista de notas se reajusta automaticamente à
  largura da janela, quebrando as linhas de forma legível mesmo quando a
  janela é estreitada.

### Busca e filtros

- Busca (`Ctrl+F` foca o campo, funcionando mesmo com o foco em outro campo
  de texto) localiza notas ativas pelo número da NF, pelo nome do
  cliente/remetente ou pela sigla da unidade (busca parcial, sem
  diferenciar maiúsculas/minúsculas). Assim como no cadastro, o sistema
  sugere o nome de um cliente já cadastrado enquanto o usuário digita, e
  `Enter`/`Tab` aceitam a sugestão.
  - Ao buscar por **número de NF**, o sistema localiza e destaca aquela
    nota específica na lista. Se o número não corresponder a nenhuma NF
    ativa, o sistema também procura esse número dentro das **atualizações
    de tratativa** já registradas (ex.: um protocolo ou telefone anotado em
    uma ocorrência) e, se encontrar, filtra a lista mostrando as notas
    correspondentes.
  - Ao buscar por **cliente ou sigla**, o sistema **filtra a lista**,
    mostrando todas as notas correspondentes àquele cliente/sigla,
    independente do número de NF ou do tipo de ocorrência. O filtro é
    removido ao limpar o campo de busca (ou pelo botão "Limpar filtro").
- O filtro "Filtrar por ocorrência" é digitável (agiliza a localização do
  tipo) e mostra **apenas as ocorrências que existem entre as notas ativas
  no momento** — se não houver nenhuma nota de Agendamento, por exemplo,
  essa opção não aparece na lista.
- Ao filtrar por "AGENDAMENTO", as notas são organizadas pela **data do
  agendamento em ordem crescente** (a mais próxima primeiro, a mais
  distante por último) — e não pela data em que a ocorrência foi inserida.

### Resolução de notas e histórico

- Fluxo de "marcar como resolvido": o sistema calcula automaticamente os
  dias e horas que a NF ficou em tratativas (sem perguntar isso ao usuário)
  e pergunta apenas **quem demorou mais para resolver o caso** — Unidade
  (clique ou tecla `U`), Cliente (clique ou tecla `C`) ou Sem morosidade
  (`Enter`). O resultado é salvo no histórico.
- **Aba Histórico** (menu superior): mostra todas as notas tratadas nos
  últimos 60 dias, sempre em **ordem decrescente** (da mais recente para a
  mais antiga), com filtros por nome do cliente, sigla da unidade e número
  de NF (os filtros funcionam em tempo real, conforme o usuário digita).
- O histórico expira automaticamente após 60 dias, e também pode ser
  apagado manualmente a qualquer momento pela tela de Relatório.

### Relatório

- **Notas pendentes de tratativa**: total de notas ainda não marcadas como
  resolvidas, além de um campo para digitar uma sigla/empresa e ver, em
  tempo real, quantas notas pendentes existem para ela (busca parcial, sem
  diferenciar maiúsculas/minúsculas).
- **Unidades com mais ocorrências** (top 5, da maior para a menor).
- **Tempo médio para solução do caso** (em dias e horas).
- **Unidades mais morosas** (top 5, da mais para a menos morosa).
- **Clientes mais morosos** (top 5).
- Cada sigla listada nos rankings "Unidades com mais ocorrências" e
  "Unidades mais morosas" é clicável: um clique abre a lista das notas do
  histórico que embasam aquela posição no ranking (no caso das mais
  morosas, somente as notas em que aquela unidade foi apontada como a mais
  demorada).

### Lógica de datas

- `0` = data atual do sistema.
- `1` a `31` (um ou dois dígitos) = dia informado, considerando mês/ano
  correntes.
- 8 dígitos = data completa `ddmmaaaa`.

## Observações e simplificações assumidas

1. O histórico de 60 dias é limpo automaticamente a cada abertura do
   sistema e a cada abertura das telas de Relatório/Histórico, além de
   poder ser apagado manualmente a qualquer momento.
2. Os "dias e horas em tratativas" salvos no histórico ao marcar uma nota
   como resolvida são sempre calculados automaticamente a partir da
   data/hora de inserção da nota até o momento da resolução.
3. **Correção de travamento (versão anterior)**: um pop-up de alerta
   automático não aguardava corretamente a resposta do usuário antes de
   continuar a verificação, o que podia travar a aplicação quando vários
   alertas disparavam ao mesmo tempo. Toda a lógica de lembretes/alertas
   automáticos foi removida do sistema nesta versão, eliminando de vez essa
   classe de problema.
4. A sigla de unidade aceita tanto siglas de 3 letras quanto o nome de uma
   empresa parceira cadastrada (Agex, Risso, etc.) — o campo é o mesmo, sem
   distinção de formato.
5. **Correção de bloco expandindo**: ao adicionar uma nova nota, o cabeçalho
   (que usa um campo de texto para permitir negrito em CLIENTE/OCORRÊNCIA/
   AGENDAMENTO) podia calcular a altura antes de o bloco ser efetivamente
   posicionado na tela, fazendo-o ocupar um espaço enorme até a janela ser
   redimensionada manualmente. Corrigido recalculando a altura sempre que a
   largura real do bloco é definida, sem depender de ação do usuário.
6. **Correção de barra de rolagem**: ao escolher, aplicar ou limpar o filtro
   por ocorrência, a lista agora sempre volta para o topo automaticamente,
   em vez de permanecer na posição de rolagem anterior (que podia deixar o
   único resultado filtrado fora da área visível).
7. **Correção de lentidão ao inserir notas/tratativas**: a lista de notas
   estava recalculando a geometria de cada bloco individualmente (uma
   operação cara) e consultando o banco de dados uma vez por nota para
   buscar as tratativas, o que deixava o sistema lento conforme a
   quantidade de notas ativas crescia. Agora as tratativas de todas as
   notas visíveis são buscadas em uma única consulta, e o recálculo de
   geometria é feito uma única vez para a lista inteira — a atualização
   volta a ser praticamente instantânea.
8. **Correção do atalho Ctrl+F**: os campos de texto do Tkinter têm um
   atalho padrão de Ctrl+F (mover o cursor) que interceptava o atalho antes
   dele chegar à busca. Agora o Ctrl+F funciona a partir de qualquer campo
   do formulário, não só quando nenhum campo está em foco.
9. **Correção de blocos "se movendo" ao rolar o mouse**: quando um filtro
   deixava poucas notas visíveis, a área rolável do canvas podia ficar
   maior que o conteúdo real (por causa dos ajustes de altura dos
   cabeçalhos acontecerem depois do cálculo de rolagem), fazendo o bloco
   parecer se deslocar ao rolar o mouse mesmo sem haver nada para rolar.
   Corrigido resincronizando a área rolável com o tamanho final da lista.
10. **Cópia de NF no Histórico e no Relatório**: os blocos de nota exibidos
    na aba Histórico e no detalhamento de unidades/clientes do Relatório
    agora também copiam o número da NF para a área de transferência ao
    serem clicados, assim como já acontecia com as notas ativas.
11. **Notas que pareciam "sumir"**: ao inserir uma nova nota ou editar a
    ocorrência de uma nota existente, se um filtro (por ocorrência ou por
    busca) estivesse ativo e não correspondesse à nota recém-alterada, o
    sistema agora limpa esse filtro automaticamente para garantir que a
    nota apareça imediatamente, sem precisar fechar e reabrir o sistema.
12. **Clique não rola mais a tela**: clicar sobre uma nota (para selecioná-la
    ou copiar a NF) não força mais a lista a rolar até ela — a rolagem
    automática continua existindo apenas na busca (Ctrl+F) e na navegação
    por teclado (setas ↑/↓), onde faz sentido trazer a nota para a área
    visível.
13. **Otimizações de velocidade na inserção de notas/tratativas e ao marcar
    como resolvido**: inserir uma nova nota, uma nova atualização de
    tratativa, ou marcar uma nota como resolvida não reconstrói mais a lista
    inteira — o sistema agora só acrescenta o bloco novo (ou remove o bloco
    resolvido) diretamente na tela, sem tocar nos demais (exceto ao inserir
    uma nota de Agendamento com o filtro "AGENDAMENTO" ativo, caso em que a
    lista precisa ser reordenada pela data). O banco de dados também passou
    a usar o modo WAL do SQLite, que acelera a gravação de cada
    nota/tratativa/resolução. Com essas mudanças, essas três ações deixam de
    depender da quantidade de notas já cadastradas — testes isolados do
    banco de dados (sem contar o tempo de desenho da tela, que varia
    conforme o computador) mostraram tempos na casa de 1 a 2 milissegundos,
    mesmo com 150 notas ativas simuladas. Não foi necessário remover nenhuma
    funcionalidade para atingir esse ganho.

## Próximos passos sugeridos

- Empacotar com PyInstaller para gerar um instalador único para os
  atendentes que não tenham Python instalado.
- Se a base de usuários crescer muito, considerar migrar de SQLite para um
  banco cliente/servidor (ex. PostgreSQL) — a camada `database.py` foi escrita
  de forma isolada exatamente para facilitar essa troca no futuro, sem
  precisar alterar a interface gráfica.
