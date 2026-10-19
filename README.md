# Consultivo Previdenciário (Plutus 🧚‍♀️💰)

Painel de gestão dos diagnósticos de créditos previdenciários da Veiga: agenda de ações e entregas, esteira por fase (contrato → documentos → levantamento → revisão → entrega → aprovação → execução), carga por pessoa, crédito identificado e aprovado, custo do atraso (decadência de 5 anos) e manual do consultivo.

**Acesso:** https://veigalaw.github.io/consultivo-prev/ (senha do time).

- Dados criptografados em `data/diagnosticos.enc.json` (AES-256-GCM). O repo é público, mas sem a senha ninguém lê cliente, valores ou histórico.
- O robô **Plutus** roda na nuvem às 7h45 e 19h45: lê o grupo "Diagnóstico - Prev" no Teams, atualiza os diagnósticos e, às 7h45 dos dias úteis, posta a agenda do dia. Detalhes em [`robot/ROBO.md`](robot/ROBO.md).
