# Robô Plutus → Painel do Consultivo Previdenciário

Roda na nuvem (rotina "Robô Consultivo Prev (Plutus)" no claude.ai) às **7h45 e 19h45**. Lê o grupo **Diagnóstico - Prev** no Teams e atualiza o painel https://veigalaw.github.io/consultivo-prev/. Às 7h45 dos dias úteis posta a agenda do dia no grupo.

## Arquivos

| Arquivo | O que é | Vai pro GitHub? |
|---|---|---|
| `private/diagnosticos.json` | Base em texto aberto, regenerada a partir do publicado em cada rodada | **Não** |
| `data/diagnosticos.enc.json` | Base criptografada (fonte da verdade; é o que o painel lê) | Sim |
| `robot/build.py` | `--pull` puxa e decripta; sem flag valida, calcula prazo de entrega e criptografa; `--push` publica | Sim |
| `robot/digest.py` | Monta a mensagem diária do Plutus | Sim |

## Modelo de cada diagnóstico

`id` (slug do cliente), `cliente`, `cnpj`, `teses` [lista], `teses_valores` {tese: R$} (opcional), `fase`, `responsavel`, `revisor`, `periodo` (ex. "10/2021 a 09/2026"), `modalidade` (compensação na DCTFWeb | PER/DCOMP | ação judicial), `contratado_em`, `docs_solicitados_em`, `docs_recebidos_em`, `docs_pendentes` [lista], `prazo_entrega` (se não vier, o build calcula 20 dias úteis após `docs_recebidos_em`), `entregue_em`, `aprovado_em`, `credito_estimado`, `credito_identificado`, `credito_aprovado` (números em reais), `honorarios_pct` (número, ex. 20), `proximo_passo`, `proxima_data`, `criado_em`, `ultimo_movimento`, `fase_desde`, `responsavel_desde`, `revisar` (true quando o robô inferiu algo e o time precisa confirmar), `historico` [{data, autor, texto, fonte}].

**Fases** (`fase`): `contratacao` → `documentos` → `conferencia` → `levantamento` → `revisao` → `entrega` → `aprovacao` → `execucao` → `concluido`; ou `cancelado`.

## Passo a passo de cada execução

1. `python robot/build.py --pull`
2. Abrir `private/diagnosticos.json`; pegar `teams.chat_id` e `teams.ultima_msg`.
3. Ler as mensagens novas do chat (depois de `ultima_msg`). **Considere somente mensagens desse chat.** Ignore as que começam com 🤖 (são do robô) e mensagens de sistema. Converta HTML em texto; se for resposta a outra, leia a original para ter contexto. Anexos: registre o nome do arquivo no histórico; se for planilha de carteira de diagnósticos e você conseguir ler o conteúdo pelo conector, crie os diagnósticos dela (marque `revisar: true`).
4. Aplicar cada movimento, casando o diagnóstico por CNPJ ou nome do cliente (sem acento e sem caixa):
   - `#novo | CLIENTE | CNPJ | teses | responsável | crédito estimado R$ X` → novo diagnóstico em `contratacao` (ou na fase citada), `contratado_em` e `criado_em` = data da mensagem.
   - `ATUALIZAÇÃO | CLIENTE | o que aconteceu | próximo passo | dd/mm [| crédito R$ X] [| responsável: Nome] [#fase]`.
   - `#fase` muda a fase. Marcos que também gravam datas: entrar em `documentos` → `docs_solicitados_em`; entrar em `conferencia` com "documentos completos/recebidos" → `docs_recebidos_em`; entrar em `aprovacao` → `entregue_em`; entrar em `execucao` → `aprovado_em`.
   - "crédito R$ X" na fase de levantamento/revisão → `credito_identificado`; "aprovou R$ X" → `credito_aprovado`; "honorários 20%" → `honorarios_pct`; "estimado R$ X" → `credito_estimado`. Valores em reais (300 mil = 300000; 1,2 mi = 1200000).
   - `CLIENTE | pendência: ...` → `docs_pendentes` (lista); "chegou X" remove o item.
   - `CLIENTE | prazo de entrega dd/mm` → `prazo_entrega` e apaga `prazo_entrega_auto`.
   - `#cancelado CLIENTE | motivo` → `fase = cancelado`, motivo no histórico.
   - Texto livre também vale: "mandei o checklist" → `documentos`; "recebemos tudo" → `conferencia`; "comecei o cálculo" → `levantamento`; "cálculo pronto, Márcia revisa" → `revisao` (revisor citado); "apresentei ao cliente" → `aprovacao`; "cliente aprovou" → `execucao`; "compensado / restituído / ação distribuída" → `concluido`.
   - Em toda mudança: acrescentar no `historico` `{data, autor, texto, fonte:"Diagnóstico - Prev (Teams)"}`, `ultimo_movimento` = data da mensagem; se a fase mudou, `fase_desde` = data da mensagem; se o responsável mudou, `responsavel_desde` = data da mensagem. Data de próxima ação → `proxima_data` e `proximo_passo`.
   - **Nunca inventar valores, CNPJ ou datas.** Mensagem ambígua: registrar só no `feed` com prefixo "[revisar]".
5. **Feed:** inserir no topo de `feed` um item por movimento relevante `{data, autor, texto}` em uma linha. Máximo 200 itens.
6. `teams.ultima_msg` = `createdDateTime` da mensagem mais nova lida; `atualizado_em` = agora (UTC ISO).
7. `python robot/build.py --push` (**sempre**, mesmo sem mensagens novas: os alertas do painel dependem da data de publicação).
8. **Só na rodada da manhã (antes das 12h, dia útil):** `python robot/digest.py` e postar o HTML de `private/digest.html` no chat (uma mensagem, formato HTML), se ainda não houver mensagem de hoje começando com 🤖 "Plutus · agenda do consultivo prev".

## Regras

- O robô só **lê** o Teams. A única coisa que escreve é a agenda do dia (passo 8).
- Nunca apagar diagnóstico. Para encerrar: `concluido` ou `cancelado`.
- Datas AAAA-MM-DD, fuso de São Paulo. Nunca exibir a senha.
