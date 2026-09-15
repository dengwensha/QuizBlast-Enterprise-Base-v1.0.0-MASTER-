# Sprint 2.2.6 — Import Pipeline Orchestrator

## Amaç

Şimdiye kadar üretilen bağımsız modülleri tek bir servis altında sıraya koymak.

## Önceki Modüller

1. QBDS Mapper
2. Validation Engine
3. Duplicate Detector
4. Import Report Engine
5. Import Preview Engine

## Bu Modül Ne Yapar?

Raw Excel rows verisini alır ve şu sıradan geçirir:

```text
Raw Rows
↓
QBDS Mapper
↓
Validation / Duplicate
↓
Import Report
↓
Import Preview
↓
Importable Legacy Payloads
```

## Önemli Not

Bu modül database'e yazmaz.
Ana sisteme bağlı değildir.
Integration Sprint öncesi bağımsız son pipeline katmanıdır.

## Manuel Test

```bash
python -m app.tests.test_import_pipeline_manual
```

## Sonraki Sprint

Sprint 2.3 — Integration Sprint

Bu sprintte pipeline gerçek Excel import akışına bağlanacak.
