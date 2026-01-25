# QA / Audit-ready — sisRUA

Este diretório organiza **testes** e **artefatos de evidência** para auditorias (ex.: ambiente regulado, ANEEL).

> Observação: certificação ISO (ex.: ISO 9001/27001) depende também de processos organizacionais (gestão de mudanças, riscos, treinamento, auditorias internas, etc.).  
> Aqui entregamos **testes + documentação + rastreabilidade** que costumam ser exigidos em auditorias.

## Estrutura

- `requirements.md`: requisitos (FR/NFR) com IDs.
- `traceability.csv`: matriz de rastreabilidade (Requisito → Teste → Evidência).
- `test-plan.md`: plano de testes (escopo, estratégia, critérios de aceite).
- `manual/`: suíte de testes manuais (AutoCAD + UI/UX) + templates de evidência.
- `out/`: saída gerada (relatórios, logs, evidências, ZIP). **Não versionar**.

## Evidências de testes manuais (AutoCAD)

Recomendação (audit-ready): cada execução manual cria um “RUN” auto-contido em:

- `qa/out/manual/<RUN_ID>/execution-record.md`
- `qa/out/manual/<RUN_ID>/artifacts-under-test.sha256.txt`
- `qa/out/manual/<RUN_ID>/evidence/` (screenshots)
- `qa/out/manual/<RUN_ID>/logs/` (cópias de logs relevantes)
- `qa/out/manual/<RUN_ID>/artifacts/` (DWGs/exportações, se aplicável)

O template para o registro e o checklist ficam em `qa/manual/`.

## Como rodar (automatizado)

### Backend (pytest)

Requisitos: Python 3.11+.

```bash
cd src/backend
python -m pip install -r requirements-ci.txt -r requirements-dev.txt
pytest -q
```

### Frontend (vitest)

Requisitos: Node.js LTS.

```bash
cd src/frontend
npm install
npm test -- --run
```

## Pacote de evidências (ZIP)

Gera um “evidence pack” com versão/commit, docs legais e relatórios de testes (se existirem):

```bash
python tools/generate_evidence_pack.py
```

