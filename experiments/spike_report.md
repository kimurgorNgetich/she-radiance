# SR-001 API Feasibility Spike Report

## Local baseline (MobileNetV2)

### Accuracy per class
- Acne_Mild: 7/12 (58.3%)
- Acne_Severe: 2/12 (16.7%)
- Clear_Skin: 1/12 (8.3%)
- Hyperpigmentation: 0/12 (0.0%)

### Accuracy per Fitzpatrick bucket
- I-III: 4/24 (16.7%)
- IV-VI: 6/24 (25.0%)

### Confusion matrix

| true \ pred | Acne_Mild | Acne_Severe | Clear_Skin | Hyperpigmentation |
|---|---|---|---|---|
| Acne_Mild | 7 | 4 | 0 | 1 |
| Acne_Severe | 10 | 2 | 0 | 0 |
| Clear_Skin | 8 | 1 | 1 | 2 |
| Hyperpigmentation | 8 | 4 | 0 | 0 |

### p95 latency: 120.1 ms

## API — claude-haiku-4-5

### Status breakdown
- ok: 48/48 (100.0%)

### Accuracy per class
- Acne_Mild: 11/12 (91.7%)
- Acne_Severe: 10/12 (83.3%)
- Clear_Skin: 8/12 (66.7%)
- Hyperpigmentation: 6/12 (50.0%)

### Accuracy per Fitzpatrick bucket
- I-III: 18/24 (75.0%)
- IV-VI: 17/24 (70.8%)

### Confusion matrix (status=ok only)

| true \ pred | Acne_Mild | Acne_Severe | Clear_Skin | Hyperpigmentation | Uncertain_Refer |
|---|---|---|---|---|---|
| Acne_Mild | 11 | 1 | 0 | 0 | 0 |
| Acne_Severe | 0 | 10 | 0 | 1 | 1 |
| Clear_Skin | 1 | 0 | 8 | 1 | 2 |
| Hyperpigmentation | 3 | 2 | 0 | 6 | 1 |

### p95 latency: 3058.5 ms

### Cost per 100 inferences: $0.14

## SR-001 gate — claude-haiku-4-5

- IV-VI accuracy: API 70.8% vs local 25.0% (delta +45.8pp, need >= 15pp): PASS
- p95 latency 3058.5ms < 4000ms: PASS
- 100% status=ok on final prompt version: PASS

**Verdict: PASS**
