# GREENPROOF v3 BUILD STRATEGY

**The Government Waste Elimination Engine**

*"Same unbreakable physics. Now a sharpened weapon for energy dominance, waste elimination, and American competitiveness."*

---

## GROK RESPONSE PROCESSOR OUTPUT

### PHASE 1 — DIAGNOSTIC EXTRACTION

#### 1.1 Explicit Requests

| Phrase (Grok exact words) | Requirement |
|---------------------------|-------------|
| "Target EPA climate grants ($50B+ IRA allocations)" | Build DOGE audit integration for EPA/DOE spending |
| "Generate cryptographic receipts proving American energy cleaner than alleged" | Build CBAM defense module with export verification |
| "Create pre-verified 'American Energy' project templates" | Build permitting acceleration templates |
| "Calculate launch/satellite emissions vs. avoided terrestrial infrastructure" | Build SpaceX net benefit calculator |
| "Compression-test legacy automaker ESG claims" | Build competitor exposure scanner |
| "Kill Gold Standard Registry Integration entirely" | Remove Gold Standard from registry.py |
| "Kill all 'carbon/climate' phrasing in public outputs" | Rebrand all language to "fraud/waste" |
| "Pivot fully to compliance/enforcement markets" | Remove voluntary market focus |

#### 1.2 Hidden Nuggets

| Phrase | Hidden Meaning | Connection |
|--------|----------------|------------|
| "Physics-based (compression ratios undeniable)" | Compression is litigation-proof because it's math | Legal defense strategy |
| "Ruthless internal review—no 'green' language" | Language is attack surface for political opponents | Rebrand entire codebase |
| "Verify Before You Pay" | Executive order hook for mandatory adoption | Government procurement integration |
| "Late February 2025—post-DOGE initial cuts" | Timing with DOGE report maximizes visibility | Launch sequence |
| "Private demo to DOGE/Wright/Burgum first" | Inside track before public launch | Stakeholder sequencing |
| "Musk tweet amplification" | Single tweet = national news | Viral strategy |
| "Laptop-runnable for rapid audits" | No infrastructure dependencies = rapid deployment | Architecture constraint |
| "shared ledger potential with DOGE systems" | Receipt infrastructure can merge with DOGE | ProofPack integration |

#### 1.3 New Connections

| Grok Concept | GreenProof Mapping | Implementation Vector |
|--------------|-------------------|----------------------|
| "DOGE Fraud Audit Integration" | New module: doge.py | Audit EPA/DOE grants, emit waste_receipt |
| "CBAM Reciprocal Defense Tool" | New module: cbam.py | Export verification, tariff justification receipts |
| "Permitting Acceleration Templates" | New module: permit.py | Pre-verified project templates, NEPA bypass |
| "SpaceX/Starlink Net Benefit Module" | Expand ev.py → spacex.py | Launch emissions vs. avoided infrastructure |
| "Competitor Exposure Scanner" | Expand detect.py | Target GM/Ford/VW ESG claims |
| "Government Waste Elimination Engine" | Core rebrand | All "carbon" → "fraud/waste" |
| "Compliance/enforcement markets" | registry.py pivot | Remove voluntary, focus US compliance |

#### 1.4 Physics Validated

| Our Implementation | Grok's Physics Frame |
|--------------------|---------------------|
| Compression ratio ≥0.85 = verified | "Compression ratios undeniable" — confirmed as litigation-proof |
| Physics-based fraud detection | "Physics can't lie" — confirmed as apolitical |
| Receipts-native architecture | "Immutable receipts" — confirmed for DOGE alignment |
| Energy producer verification | Confirmed for Wright/Burgum, expand to LNG/nuclear/pipelines |

**GATE 1 CHECKPOINT:**
- [x] At least 1 explicit request extracted (8 extracted)
- [x] At least 3 hidden nuggets identified (8 identified)
- [x] At least 3 new connections mapped (7 mapped)
- [x] Physics validation documented (4 validations)

---

### PHASE 2 — BUILD REQUIREMENTS

#### 2.1 SOURCE (Grok exact words driving this build)

> "Target EPA climate grants ($50B+ IRA allocations, high fraud risk via unverified outcomes) and DOE clean energy loans/subsidies. Flag programs with weakest verification."

> "Kill Gold Standard Registry Integration entirely. Too European, activist-heavy, slow methodologies. No US enforcement leverage."

> "Kill all 'carbon/climate' phrasing in public outputs. Replace with 'fraud detection,' 'waste elimination,' 'energy efficiency proof.'"

> "Physics stays identical: Compression ratio exposes unverifiable claims as fraud/waste. Politics flips: No 'save the planet'—pure anti-grift tool."

> "PARADIGM SHIFT: Government Waste Elimination Engine"

#### 2.2 KILL

| Kill Target | Reason | Source |
|-------------|--------|--------|
| Gold Standard registry integration | "Too European, activist-heavy" | Grok STOP list |
| Voluntary market emphasis | "Pivot fully to compliance/enforcement markets" | Grok STOP list |
| All "carbon/climate" language | "Kill all phrasing in public outputs" | Grok STOP list |
| International registry focus (non-US Verra) | "Kill non-US elements" | Grok STOP list |
| data/registries/gold_standard.json | Gold Standard schema no longer needed | Grok STOP list |

#### 2.3 ADD

| Addition | Purpose | Source |
|----------|---------|--------|
| src/doge.py | DOGE fraud audit integration | Grok START #1 |
| src/cbam.py | CBAM reciprocal defense tool | Grok START #2 |
| src/permit.py | Permitting acceleration templates | Grok START #3 |
| src/spacex.py | SpaceX/Starlink net benefit module | Grok START #4 |
| src/expose.py | Competitor exposure scanner | Grok START #5 |
| data/doge/ | EPA/DOE grant datasets | Grok START #1 |
| data/cbam/ | EU CBAM rules and US export data | Grok START #2 |
| data/permits/ | Pre-verified project templates | Grok START #3 |
| 2 new simulation scenarios | DOGE_AUDIT, CBAM_DEFENSE | Grok EVOLVE |

#### 2.4 MODIFY

| File | Modification | Reason |
|------|--------------|--------|
| registry.py | Remove Gold Standard, remove non-US Verra, add US-only mode | Grok STOP list |
| detect.py | Add competitor exposure functions | Grok START #5 |
| energy.py | Expand to LNG, nuclear, pipelines | Grok CONTINUE |
| ev.py | Rename to vehicles.py, add legacy automaker exposure | Grok START #5 |
| sim.py | Add DOGE_AUDIT and CBAM_DEFENSE scenarios | Grok EVOLVE |
| cli.py | Add doge, cbam, permit, expose commands | New modules |
| ALL FILES | Replace "carbon/climate" → "fraud/waste/efficiency" | Grok STOP #3 |
| README.md | Rebrand as "Government Waste Elimination Engine" | Grok PARADIGM SHIFT |

#### 2.5 CONSTANTS

```python
# src/core.py — Rebranded constants
TENANT_ID = "greenproof-waste-elimination"  # Was "greenproof"
SYSTEM_NAME = "Government Waste Elimination Engine"  # NEW

# src/doge.py — New constants
EPA_GRANT_THRESHOLD = 50_000_000_000  # $50B+ IRA allocations
DOE_LOAN_THRESHOLD = 10_000_000_000   # $10B+ clean energy loans
WEAK_VERIFICATION_THRESHOLD = 0.60    # Below this = high fraud risk
DOGE_DASHBOARD_REFRESH_SEC = 3600     # Hourly updates

# src/cbam.py — New constants  
CBAM_EFFECTIVE_DATE = "2026-01-01"     # EU CBAM takes effect
US_EXPORT_SECTORS = ["oil_gas", "steel", "manufacturing", "lng"]
RECIPROCAL_TARIFF_THRESHOLD = 0.10    # 10% fraud triggers tariff justification

# src/permit.py — New constants
NEPA_BYPASS_THRESHOLD = 0.90          # Above this = pre-verified compliance
PROJECT_TYPES = ["lng_terminal", "pipeline", "nuclear_smr", "refinery"]
TEMPLATE_VALIDITY_YEARS = 5

# src/spacex.py — New constants
FALCON9_EMISSIONS_KG_CO2 = 425_000    # Per launch (kerosene)
STARLINK_SATELLITES_ACTIVE = 6000     # Current constellation
FIBER_AVOIDED_KG_CO2_PER_KM = 50      # Terrestrial infrastructure displaced
STARSHIP_EMISSIONS_KG_CO2 = 250_000   # Per launch (methane, cleaner)

# src/expose.py — New constants
LEGACY_AUTOMAKERS = ["gm", "ford", "vw", "stellantis", "toyota", "honda"]
ESG_CLAIM_SOURCES = ["annual_report", "sustainability_report", "sec_filing"]
EXPOSURE_THRESHOLD = 0.70             # Below this = likely fraudulent claims
```

#### 2.6 EMIT (New receipts per CLAUDEME LAW_1)

| Receipt Type | Module | Key Fields |
|--------------|--------|------------|
| waste_receipt | doge.py | grant_id, waste_amount_usd, verification_gap, recommendation |
| cbam_receipt | cbam.py | export_id, us_emissions, eu_claimed, discrepancy_pct, tariff_justified |
| permit_receipt | permit.py | project_id, template_type, compliance_ratio, nepa_bypass_eligible |
| spacex_receipt | spacex.py | mission_id, launch_emissions, avoided_emissions, net_benefit |
| exposure_receipt | expose.py | company, claim_type, compression_ratio, fraud_level, evidence |

#### 2.7 VALIDATE

| Validation | Command | Pass Criteria |
|------------|---------|---------------|
| DOGE audit accuracy | `pytest tests/test_doge.py` | ≥90% waste detection on known fraud cases |
| CBAM defense | `pytest tests/test_cbam.py` | Receipts generated for all US export sectors |
| Permit templates | `pytest tests/test_permit.py` | All 4 project types have valid templates |
| SpaceX net benefit | `pytest tests/test_spacex.py` | Net benefit calculation matches published data |
| Competitor exposure | `pytest tests/test_expose.py` | All 6 legacy automakers scanned |
| No "carbon/climate" language | `grep -r "carbon\|climate" src/` | Zero matches (except constants) |
| 8 scenarios pass | `pytest tests/test_sim_scenarios.py` | All 8 scenarios pass (6 existing + 2 new) |

#### 2.8 CONNECTIONS

| From | To | Mechanism |
|------|-----|-----------|
| doge.py | detect.py | Waste detection uses compression-based fraud detection |
| doge.py | prove.py | All waste findings anchored with merkle proof |
| cbam.py | energy.py | Export verification uses energy producer data |
| cbam.py | registry.py | Cross-reference with US registries only |
| permit.py | compress.py | Templates verified via compression ratio |
| permit.py | prove.py | Pre-verified templates anchored in ledger |
| spacex.py | energy.py | Launch emissions use energy calculation framework |
| spacex.py | compress.py | Net benefit claims compression-tested |
| expose.py | compress.py | ESG claims compression-tested for fraud |
| expose.py | detect.py | Exposure findings feed fraud detection |
| sim.py | ALL | New scenarios validate all new modules |

**GATE 2 CHECKPOINT:**
- [x] SOURCE cites Grok's exact words (5 quotes)
- [x] KILL has at least 1 item (5 items)
- [x] ADD has at least 2 items (9 items)
- [x] VALIDATE has testable criteria (7 validations)
- [x] CONNECTIONS table populated (11 connections)

---

## PART 1: ARCHITECTURE (v3 Evolution)

### 1.1 The Paradigm Shift

| v2 Frame | v3 Frame |
|----------|----------|
| "Carbon verification system" | **"Government Waste Elimination Engine"** |
| Targets ESG fraud | Targets taxpayer waste + trade cheating |
| Voluntary market focus | Compliance/enforcement focus |
| International registries | US-only enforcement |
| Climate language | Fraud/waste/efficiency language |

**The Physics Is Identical:**
- Compression ratio ≥0.85 = verified claim
- Compression ratio <0.70 = fraudulent/wasteful claim
- The compression ratio IS the fraud signal

**The Politics Flip:**
- No "save the planet"
- Pure anti-grift tool
- Proves billions in taxpayer waste
- Arms trade negotiations
- Accelerates permitting by proving compliance

### 1.2 Directory Structure (v3)

```
greenproof/
├── spec.md                    
├── ledger_schema.json         
├── cli.py                     
├── receipts.jsonl             
├── src/
│   ├── __init__.py
│   ├── core.py                # dual_hash, emit_receipt, StopRule, merkle
│   ├── compress.py            # Compression engine (UNCHANGED)
│   ├── registry.py            # US-ONLY registry integration (MODIFIED)
│   ├── detect.py              # Fraud detection + competitor exposure (MODIFIED)
│   ├── trading.py             # Trading layer infrastructure (UNCHANGED)
│   ├── energy.py              # Energy verification + LNG/nuclear/pipeline (EXPANDED)
│   ├── vehicles.py            # Tesla + legacy automaker exposure (RENAMED from ev.py)
│   ├── prove.py               # Receipt chain, merkle proof (UNCHANGED)
│   ├── sim.py                 # Monte Carlo harness (8 scenarios) (EXPANDED)
│   ├── doge.py                # DOGE fraud audit integration (NEW)
│   ├── cbam.py                # CBAM reciprocal defense (NEW)
│   ├── permit.py              # Permitting acceleration (NEW)
│   ├── spacex.py              # SpaceX/Starlink net benefit (NEW)
│   └── expose.py              # Competitor exposure scanner (NEW)
├── tests/
│   ├── test_compress.py
│   ├── test_registry.py
│   ├── test_detect.py
│   ├── test_trading.py
│   ├── test_energy.py
│   ├── test_vehicles.py       # RENAMED
│   ├── test_sim_scenarios.py
│   ├── test_doge.py           # NEW
│   ├── test_cbam.py           # NEW
│   ├── test_permit.py         # NEW
│   ├── test_spacex.py         # NEW
│   ├── test_expose.py         # NEW
│   └── conftest.py
├── data/
│   ├── fraud_cases/           
│   ├── registries/            # US-only (Gold Standard KILLED)
│   ├── synthetic/             
│   ├── doge/                  # EPA/DOE grant data (NEW)
│   ├── cbam/                  # EU CBAM rules + US exports (NEW)
│   ├── permits/               # Pre-verified templates (NEW)
│   └── competitors/           # Legacy automaker ESG claims (NEW)
├── gate_t2h.sh
├── gate_t24h.sh
├── gate_t48h.sh
└── MANIFEST.anchor
```

### 1.3 Module Dependency Graph (v3)

```
core.py (foundation)
    ↓
compress.py ← registry.py (US-only)
    ↓           ↓
detect.py ← trading.py ← energy.py ← vehicles.py
    ↓                         ↓
expose.py ← spacex.py    cbam.py ← permit.py
    ↓           ↓           ↓
    └───────────┴───────────┴───────→ doge.py
                                         ↓
                                      prove.py
                                         ↓
                                      sim.py (8 scenarios)
```

---

## PART 2: NEW MODULE SPECIFICATIONS

### 2.1 doge.py (NEW)

**Purpose:** DOGE fraud audit integration. Target $50B+ in EPA/DOE spending with weak verification.

**Functions:**

| Function | Signature | Behavior |
|----------|-----------|----------|
| audit_epa_grant | (grant: dict) → dict | Audit single EPA grant, return waste_receipt |
| audit_doe_loan | (loan: dict) → dict | Audit single DOE loan, return waste_receipt |
| batch_audit | (grants: list, source: str) → list | Batch audit EPA or DOE programs |
| calculate_waste | (grant: dict, verification_gap: float) → float | Calculate $ wasted based on gap |
| generate_dashboard | (receipts: list) → dict | Generate DOGE dashboard summary |
| flag_weak_verification | (grants: list) → list | Flag programs with verification < threshold |
| total_waste_estimate | (receipts: list) → float | Sum total waste across all audits |

**Receipt: waste_receipt**
```
{
    "receipt_type": "waste",
    "ts": "ISO8601",
    "tenant_id": "greenproof-waste-elimination",
    "grant_id": "str",
    "program": "epa|doe",
    "allocated_amount_usd": float,
    "verification_ratio": float,
    "waste_amount_usd": float,
    "waste_percentage": float,
    "verification_gap": "str (description of what's missing)",
    "recommendation": "investigate|suspend|terminate",
    "payload_hash": "sha256:blake3"
}
```

**SLOs:**
- Audit time ≤ 100ms per grant
- Waste detection accuracy ≥ 90% on known fraud
- Zero false positives on verified programs
- Dashboard generation ≤ 5s for 10,000 grants

### 2.2 cbam.py (NEW)

**Purpose:** CBAM reciprocal defense tool. Verify US exports aren't subject to fraudulent EU carbon penalties.

**Functions:**

| Function | Signature | Behavior |
|----------|-----------|----------|
| verify_us_export | (export: dict) → dict | Verify US export emissions, return cbam_receipt |
| calculate_us_emissions | (product: dict, sector: str) → float | Calculate actual US emissions |
| compare_eu_claims | (us_emissions: float, eu_claimed: float) → dict | Compare US vs EU claims |
| justify_reciprocal_tariff | (discrepancy: float) → bool | True if tariff justified |
| batch_verify_exports | (exports: list) → list | Batch verify all exports in sector |
| generate_trade_brief | (receipts: list, sector: str) → dict | Generate trade negotiation brief |

**Receipt: cbam_receipt**
```
{
    "receipt_type": "cbam",
    "ts": "ISO8601",
    "tenant_id": "greenproof-waste-elimination",
    "export_id": "str",
    "sector": "oil_gas|steel|manufacturing|lng",
    "product_type": "str",
    "us_verified_emissions_tco2e": float,
    "eu_claimed_emissions_tco2e": float,
    "discrepancy_percentage": float,
    "discrepancy_direction": "eu_overclaiming|accurate|eu_underclaiming",
    "reciprocal_tariff_justified": bool,
    "tariff_justification": "str|null",
    "payload_hash": "sha256:blake3"
}
```

**SLOs:**
- Verification time ≤ 200ms per export
- All 4 US export sectors covered
- Discrepancy calculation accuracy ≥ 95%

### 2.3 permit.py (NEW)

**Purpose:** Permitting acceleration templates. Create pre-verified project templates that bypass NEPA delays.

**Functions:**

| Function | Signature | Behavior |
|----------|-----------|----------|
| create_template | (project_type: str, parameters: dict) → dict | Create pre-verified template |
| verify_project | (project: dict, template: str) → dict | Verify project against template |
| check_nepa_bypass | (verification_ratio: float) → bool | True if project qualifies for bypass |
| generate_compliance_receipt | (project: dict) → dict | Generate permit_receipt |
| list_templates | () → list | List all available pre-verified templates |
| template_coverage | (project: dict) → float | Calculate how much of project is template-covered |

**Pre-Verified Project Types:**
1. `lng_terminal` — LNG export terminal
2. `pipeline` — Oil/gas pipeline
3. `nuclear_smr` — Small modular reactor
4. `refinery` — Oil refinery expansion

**Receipt: permit_receipt**
```
{
    "receipt_type": "permit",
    "ts": "ISO8601",
    "tenant_id": "greenproof-waste-elimination",
    "project_id": "str",
    "project_type": "lng_terminal|pipeline|nuclear_smr|refinery",
    "template_used": "str",
    "template_coverage_pct": float,
    "compliance_ratio": float,
    "nepa_bypass_eligible": bool,
    "expedited_timeline_days": int,
    "standard_timeline_days": int,
    "time_saved_days": int,
    "payload_hash": "sha256:blake3"
}
```

**SLOs:**
- Template verification ≤ 500ms
- NEPA bypass accuracy ≥ 95%
- All 4 project types have templates

### 2.4 spacex.py (NEW)

**Purpose:** SpaceX/Starlink net benefit module. Prove SpaceX is "net negative" through avoided infrastructure.

**Functions:**

| Function | Signature | Behavior |
|----------|-----------|----------|
| calculate_launch_emissions | (vehicle: str, payload_kg: float) → float | Calculate launch emissions |
| calculate_avoided_emissions | (service: str, coverage_area: dict) → float | Calculate avoided infrastructure |
| net_benefit | (launch_emissions: float, avoided_emissions: float) → dict | Calculate net benefit |
| verify_starlink_claim | (claim: dict) → dict | Verify Starlink displacement claim |
| batch_mission_analysis | (missions: list) → list | Analyze multiple missions |
| generate_regulatory_brief | (receipts: list) → dict | Generate brief for regulatory submission |

**Receipt: spacex_receipt**
```
{
    "receipt_type": "spacex",
    "ts": "ISO8601",
    "tenant_id": "greenproof-waste-elimination",
    "mission_id": "str",
    "vehicle": "falcon9|falcon_heavy|starship",
    "launch_emissions_kg_co2": float,
    "service_type": "starlink|rideshare|dedicated",
    "avoided_infrastructure": {
        "type": "fiber|cell_tower|data_center",
        "displaced_km": float,
        "avoided_emissions_kg_co2": float
    },
    "net_benefit_kg_co2": float,
    "net_status": "net_negative|net_neutral|net_positive",
    "payload_hash": "sha256:blake3"
}
```

**SLOs:**
- Calculation time ≤ 100ms per mission
- Net benefit accuracy within 5% of published data
- All SpaceX vehicles covered

### 2.5 expose.py (NEW)

**Purpose:** Competitor exposure scanner. Compression-test legacy automaker ESG claims.

**Functions:**

| Function | Signature | Behavior |
|----------|-----------|----------|
| scan_company | (company: str) → dict | Scan single company's ESG claims |
| extract_esg_claims | (report: dict, source: str) → list | Extract claims from report |
| compression_test_claim | (claim: dict) → dict | Run compression test on claim |
| classify_fraud_level | (ratio: float) → str | Return fraud level classification |
| batch_scan_industry | (companies: list) → list | Scan all companies in list |
| generate_exposure_report | (receipts: list) → dict | Generate public exposure report |
| compare_to_tesla | (company_receipts: list, tesla_receipts: list) → dict | Direct comparison |

**Receipt: exposure_receipt**
```
{
    "receipt_type": "exposure",
    "ts": "ISO8601",
    "tenant_id": "greenproof-waste-elimination",
    "company": "str",
    "claim_source": "annual_report|sustainability_report|sec_filing",
    "claim_type": "str",
    "claim_text": "str",
    "compression_ratio": float,
    "fraud_level": "verified|suspect|likely_fraud|confirmed_fraud",
    "evidence": ["str"],
    "tesla_comparison": {
        "tesla_ratio": float,
        "delta": float,
        "winner": "tesla|competitor|tie"
    },
    "payload_hash": "sha256:blake3"
}
```

**SLOs:**
- Scan time ≤ 500ms per company
- All 6 legacy automakers covered
- Fraud detection accuracy ≥ 90%

---

## PART 3: MODIFIED MODULE SPECIFICATIONS

### 3.1 registry.py (MODIFIED)

**Changes:**
- KILL Gold Standard integration
- KILL non-US Verra projects
- ADD US-only mode as default
- RENAME functions to remove "carbon" language

**Functions KILLED:**
- `fetch_gold_standard()` — KILLED
- `normalize_gold_standard()` — KILLED
- `cross_registry_scan()` — MODIFIED to US-only

**Functions ADDED:**
- `us_only_mode()` → bool — Returns True, always
- `filter_us_projects()` — Filter to US-only projects

### 3.2 detect.py (MODIFIED)

**Changes:**
- ADD competitor exposure integration
- RENAME "fraud" functions to "waste" where appropriate
- ADD `expose_competitor()` function

**Functions ADDED:**
- `detect_waste()` — Wrapper for fraud detection with waste language
- `expose_competitor()` — Call expose.py for competitor analysis
- `generate_waste_report()` — Generate waste-focused report

### 3.3 energy.py (EXPANDED)

**Changes:**
- ADD LNG lifecycle emissions
- ADD nuclear efficiency verification
- ADD pipeline emissions calculation
- EXPAND to cover Wright/Burgum priorities

**Functions ADDED:**
- `verify_lng_export()` — Verify LNG export emissions for CBAM
- `verify_nuclear_smr()` — Verify SMR efficiency claims
- `verify_pipeline()` — Verify pipeline emissions
- `compare_to_alternatives()` — Compare US energy to foreign alternatives

### 3.4 ev.py → vehicles.py (RENAMED)

**Changes:**
- RENAME file to vehicles.py
- ADD legacy automaker exposure
- KEEP Tesla verification
- ADD comparison functions

**Functions ADDED:**
- `scan_legacy_automaker()` — Scan GM/Ford/VW/etc. claims
- `compare_tesla_vs_legacy()` — Direct comparison
- `expose_credit_purchases()` — Expose questionable credit sources

### 3.5 sim.py (EXPANDED)

**Changes:**
- ADD 2 new scenarios: DOGE_AUDIT, CBAM_DEFENSE
- MODIFY existing scenarios to use waste language
- EXPAND validation to cover all new modules

---

## PART 4: THE 8 MANDATORY SCENARIOS

### Scenario 1: BASELINE (unchanged)
Standard operation, no fraud injection. 1000 cycles.

### Scenario 2: FRAUD_INJECTION (renamed to WASTE_INJECTION)
20% waste injection, ≥90% detection required.

### Scenario 3: DOUBLE_COUNTING (unchanged)
15% duplicates, ≥95% detection required.

### Scenario 4: TRADING_INTEGRITY (unchanged)
Zero fraud reaches listing.

### Scenario 5: ENERGY_VERIFICATION (expanded)
Now includes LNG, nuclear, pipeline verification.

### Scenario 6: STRESS (unchanged)
40% fraud, 25% duplicates, 10ms constraint.

### Scenario 7: DOGE_AUDIT (NEW)

**Purpose:** Validate DOGE fraud audit integration.

**Config:**
- n_cycles: 500
- Dataset: Synthetic EPA/DOE grants with known waste
- Waste injection rate: 30%

**Pass Criteria:**
- Waste detection ≥ 90%
- Dashboard generation ≤ 5s
- All waste_receipts valid
- Total waste estimate within 10% of actual

### Scenario 8: CBAM_DEFENSE (NEW)

**Purpose:** Validate CBAM reciprocal defense tool.

**Config:**
- n_cycles: 500
- Dataset: Synthetic US exports with EU overclaiming
- Overclaim rate: 25%

**Pass Criteria:**
- Discrepancy detection ≥ 95%
- All 4 export sectors covered
- Reciprocal tariff justification correct
- All cbam_receipts valid

---

## PART 5: LANGUAGE REBRAND

### Global Find/Replace

| Old Term | New Term |
|----------|----------|
| carbon verification | waste elimination |
| carbon claim | efficiency claim |
| carbon credit | efficiency credit |
| carbon offset | efficiency offset |
| climate fraud | government waste |
| ESG compliance | efficiency compliance |
| environmental impact | efficiency impact |
| green energy | American energy |
| sustainable | efficient |

### Files Requiring Rebrand

- README.md — Full rebrand to "Government Waste Elimination Engine"
- cli.py — All help text
- All docstrings in src/*.py
- All test descriptions
- spec.md
- MANIFEST.anchor

---

## PART 6: VERIFICATION PROTOCOL

### Phase 1 — Quick Validation (run immediately)

```bash
# Constants check
python -c "from src.core import TENANT_ID, SYSTEM_NAME; print(f'{SYSTEM_NAME}: {TENANT_ID}')"

# New modules exist
python -c "from src import doge, cbam, permit, spacex, expose; print('All new modules import OK')"

# No carbon/climate language
grep -r "carbon\|climate" src/ --include="*.py" | grep -v "# " | wc -l
# Should be 0 (except in constants/comments)

# 100-cycle smoke test
python -c "from src.sim import run_simulation, SimConfig; r = run_simulation(SimConfig(n_cycles=100)); print(f'100 cycles: {len(r.violations)} violations')"

# DOGE audit test
python -c "from src.doge import audit_epa_grant; r = audit_epa_grant({'grant_id': 'test', 'amount': 1000000}); assert 'waste_amount_usd' in r; print('DOGE audit OK')"
```

**⏸️ CHECKPOINT: Paste Phase 1 results. Wait for approval before Phase 2.**

### Phase 2 — Scenario Validation (only after Phase 1 approved)

```bash
# Run all 8 scenarios
python -m pytest tests/test_sim_scenarios.py -v --tb=short

# Scenario 7: DOGE_AUDIT
python -c "from src.sim import run_scenario; r = run_scenario('DOGE_AUDIT'); print(f'Waste detection rate: {r.detection_rate}')"

# Scenario 8: CBAM_DEFENSE
python -c "from src.sim import run_scenario; r = run_scenario('CBAM_DEFENSE'); print(f'Discrepancy detection: {r.detection_rate}')"

# Full test suite
python -m pytest tests/ -v --cov=src --cov-fail-under=80
```

---

## PART 7: WHAT NOT TO BUILD

| Exclusion | Reason |
|-----------|--------|
| Real EPA/DOE API integration | Use synthetic data. Real APIs are v4 scope. |
| Actual tariff filing | Infrastructure only. Real filing requires legal. |
| Satellite imagery | Partner with Planet Labs later. |
| Real SpaceX mission data | Use published estimates. Real data is v4. |
| Competitor legal action | Exposure only. Legal is external. |
| International CBAM filing | US-only for v3. EU filing is v4. |

---

## PART 8: WHAT CHANGED AND WHY

| Change | Why | Source |
|--------|-----|--------|
| KILLED Gold Standard | "Too European, activist-heavy" | Grok STOP |
| KILLED voluntary market focus | "Pivot to compliance/enforcement" | Grok STOP |
| KILLED carbon/climate language | "Replace with fraud/waste" | Grok STOP |
| ADDED doge.py | "Target EPA grants ($50B+)" | Grok START #1 |
| ADDED cbam.py | "CBAM reciprocal defense" | Grok START #2 |
| ADDED permit.py | "Pre-verified templates" | Grok START #3 |
| ADDED spacex.py | "Position as net negative" | Grok START #4 |
| ADDED expose.py | "Compression-test legacy automakers" | Grok START #5 |
| EXPANDED energy.py | "LNG, nuclear, pipelines" | Grok CONTINUE |
| RENAMED ev.py → vehicles.py | "Add legacy automaker exposure" | Grok START #5 |
| PARADIGM SHIFT | "Government Waste Elimination Engine" | Grok PARADIGM |
| 2 new scenarios | "DOGE_AUDIT, CBAM_DEFENSE" | Grok EVOLVE |

---

## PART 9: TIMELINE GATES

### Gate T+2h: SKELETON
- All new module files exist with stubs
- Constants defined in each module
- cli.py updated with new commands
- Language rebrand complete in core files

### Gate T+24h: MVP
- doge.py generates waste_receipt
- cbam.py generates cbam_receipt
- permit.py generates permit_receipt
- 100-cycle smoke test passes
- pytest tests/ passes with >80% coverage

### Gate T+48h: HARDENED
- All 8 scenarios pass
- spacex.py generates spacex_receipt
- expose.py generates exposure_receipt
- Language rebrand complete in ALL files
- Stoprules on all error paths
- SHIP IT

---

## PART 10: COMMIT MESSAGE

```
feat(greenproof): v3.0 Government Waste Elimination Engine

PARADIGM SHIFT:
  Same unbreakable physics. Different politics.
  No "save the planet"—pure anti-grift tool.
  Compression ratio exposes waste, not "carbon."

KILLED:
  - Gold Standard registry (too European)
  - Voluntary market focus (pivot to compliance)
  - All carbon/climate language (rebrand to waste/efficiency)
  - International registry focus (US-only)

ADDED:
  - doge.py: DOGE fraud audit ($50B+ EPA/DOE)
  - cbam.py: CBAM reciprocal defense
  - permit.py: Permitting acceleration templates
  - spacex.py: SpaceX/Starlink net benefit
  - expose.py: Competitor exposure scanner
  - 2 new scenarios: DOGE_AUDIT, CBAM_DEFENSE

TARGETING:
  - DOGE: Real-time waste dashboards
  - Wright/Burgum: LNG/nuclear/pipeline acceleration
  - Musk: Tesla vs. legacy automaker proof
  - Trade: CBAM reciprocal tariff justification

Receipt: waste, cbam, permit, spacex, exposure
SLO: detection ≥ 90%, waste_estimate ≤ 10% error
Gate: t48h
```

---

## PART 11: LAUNCH STRATEGY (from Grok)

**Optimal Timing:** Late February 2025 — post-DOGE initial cuts, aligned with energy emergency orders.

**Sequencing:**
1. **Private demo to DOGE/Wright/Burgum:** Audit of EPA grants exposing waste
2. **Musk tweet amplification:** Tesla/SpaceX proof
3. **Public launch:** Major fraud exposure (legacy automaker or EU import)
4. **Chamath endorsement:** Trading layer

**Goal:** National news in first 100 days.

---

## CHEF'S KISS

**The Old Question:** "Is this carbon offset real?"

**The New Question:** "Is this taxpayer dollar wasted?"

Same physics. Same compression ratio. Same fraud detection.

Different politics. Different language. Different targets.

GreenProof v2 caught carbon fraud. GreenProof v3 catches government waste.

Chamath asked for "companies that can count." DOGE needs to count $50B in EPA grants. Wright needs to prove American energy is cleanest. Burgum needs to accelerate permitting. Musk needs to prove Tesla's credits are real.

**All of them need the same thing: physics-based proof that can't be argued with.**

The compression ratio doesn't care about politics. It cares about entropy. Real physics compresses. Fake doesn't.

*Government Waste Elimination Engine: Same unbreakable physics. Now a sharpened weapon.*

---

**Hash of this document:** COMPUTE_ON_SAVE
**Version:** 3.0
**Status:** READY FOR EXECUTION

*No receipt → not real. Ship at T+48h or kill.*