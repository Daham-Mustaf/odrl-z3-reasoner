# Output Design Specification

## 1. Output Structure

```json
{
  "policy_id": "ex:policy:001",
  "status": "INVALID",
  "summary": {
    "consistent": false,
    "inheritance_valid": null,
    "conflicts": 2,
    "redundancies": 1
  },
  "issues": [
    {
      "type": "INCONSISTENCY",
      "severity": "ERROR",
      "rule_id": "ex:permission:01",
      "constraint_ids": ["ex:constraint:01", "ex:constraint:02"],
      "message": "dateTime gteq 2025-01-01 AND dateTime lteq 2024-12-31",
      "counterexample": {
        "dateTime": "impossible - no valid value"
      }
    },
    {
      "type": "PERMISSION_PROHIBITION_CONFLICT",
      "severity": "ERROR",
      "permission_id": "ex:permission:02",
      "prohibition_id": "ex:prohibition:01",
      "overlapping_constraints": {
        "permission": "fileFormat eq JPEG",
        "prohibition": "fileFormat isAnyOf [JPEG, PNG]"
      },
      "counterexample": {
        "fileFormat": "JPEG"
      }
    },
    {
      "type": "REDUNDANCY",
      "severity": "WARNING",
      "rule_id": "ex:permission:03",
      "redundant_constraint": "ex:constraint:05",
      "implied_by": "ex:constraint:04",
      "message": "count lteq 100 implied by count lteq 50"
    }
  ]
}
```

---

## 2. Issue Types

### 2.1 Inconsistency
```json
{
  "type": "INCONSISTENCY",
  "severity": "ERROR",
  "rule_id": "ex:permission:01",
  "constraint_ids": ["c1", "c2"],
  "message": "count gt 100 AND count lt 50",
  "counterexample": "impossible"
}
```

### 2.2 Permission-Prohibition Conflict
```json
{
  "type": "PERMISSION_PROHIBITION_CONFLICT",
  "severity": "ERROR",
  "permission_id": "perm:01",
  "prohibition_id": "prohib:01",
  "overlap": {
    "permission": "action=distribute, fileFormat=JPEG",
    "prohibition": "action=distribute, fileFormat∈{JPEG,PNG}"
  },
  "counterexample": {
    "action": "distribute",
    "fileFormat": "JPEG"
  }
}
```

### 2.3 XONE Violation
```json
{
  "type": "XONE_VIOLATION",
  "severity": "ERROR",
  "rule_id": "duty:01",
  "constraint_id": "xone:01",
  "satisfied_count": 2,
  "expected_count": 1,
  "satisfied_constraints": [
    "spatial eq Germany",
    "spatial eq Europe"
  ],
  "counterexample": {
    "spatial": "Germany"
  }
}
```

### 2.4 Expansion Violation (Inheritance)
```json
{
  "type": "EXPANSION",
  "severity": "ERROR",
  "parent_policy_id": "policy:parent",
  "child_policy_id": "policy:child",
  "parent_constraint": "fileFormat eq JPEG",
  "child_constraint": "fileFormat isAnyOf [JPEG, PNG]",
  "counterexample": {
    "fileFormat": "PNG",
    "explanation": "child allows PNG, parent does not"
  }
}
```

### 2.5 Redundancy
```json
{
  "type": "REDUNDANCY",
  "severity": "WARNING",
  "rule_id": "perm:01",
  "redundant": "count lteq 100",
  "implied_by": "count lteq 50",
  "suggestion": "remove count lteq 100"
}
```

---

## 3. Status Codes

```
VALID             - No issues
INCONSISTENT      - Has logical contradictions
CONFLICT          - Permission-prohibition or XONE conflict
EXPANSION         - Child expands parent (inheritance)
REDUNDANT         - Has redundant constraints (warning only)
```

---

## 4. Severity Levels

```
ERROR   - Policy cannot be deployed
WARNING - Policy works but can be improved
INFO    - Informational note
```

---

## 5. Compact Output Format (CLI)

```
Policy: ex:policy:001
Status: INVALID ❌

Issues:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ERROR] INCONSISTENCY in ex:permission:01
  Constraints: ex:constraint:01, ex:constraint:02
  ├─ dateTime gteq 2025-01-01
  └─ dateTime lteq 2024-12-31
  → No valid dateTime value exists

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ERROR] PERMISSION_PROHIBITION_CONFLICT
  Permission: ex:permission:02 (action=distribute)
  Prohibition: ex:prohibition:01 (action=distribute)
  
  Overlap:
  ├─ Permission:  fileFormat eq JPEG
  └─ Prohibition: fileFormat isAnyOf [JPEG, PNG]
  
  Counterexample:
  └─ fileFormat = JPEG → both satisfied ⚠️

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[WARNING] REDUNDANCY in ex:permission:03
  Redundant:  count lteq 100
  Implied by: count lteq 50
  → Suggestion: remove count lteq 100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
  Errors:   2
  Warnings: 1
  Total constraints analyzed: 8
  Analysis time: 0.32s
```

---

## 6. Machine-Readable JSON (Full)

```json
{
  "policy_id": "ex:policy:001",
  "status": "INVALID",
  "timestamp": "2026-01-19T14:23:45Z",
  "analyzer_version": "1.0.0",
  
  "summary": {
    "total_rules": 5,
    "total_constraints": 12,
    "consistent": false,
    "inheritance_valid": null,
    "errors": 2,
    "warnings": 1,
    "analysis_time_ms": 324
  },
  
  "rules_analyzed": [
    {
      "rule_id": "ex:permission:01",
      "rule_type": "Permission",
      "action": "odrl:distribute",
      "target": "ex:asset:001",
      "constraint_count": 2,
      "status": "INCONSISTENT"
    },
    {
      "rule_id": "ex:permission:02",
      "rule_type": "Permission",
      "action": "odrl:distribute",
      "target": "ex:asset:002",
      "constraint_count": 3,
      "status": "CONFLICT"
    }
  ],
  
  "issues": [
    {
      "id": "issue-001",
      "type": "INCONSISTENCY",
      "severity": "ERROR",
      "rule_id": "ex:permission:01",
      "constraints": [
        {
          "id": "ex:constraint:01",
          "leftOperand": "odrl:dateTime",
          "operator": "odrl:gteq",
          "rightOperand": "2025-01-01"
        },
        {
          "id": "ex:constraint:02",
          "leftOperand": "odrl:dateTime",
          "operator": "odrl:lteq",
          "rightOperand": "2024-12-31"
        }
      ],
      "message": "dateTime gteq 2025-01-01 AND dateTime lteq 2024-12-31",
      "counterexample": {
        "explanation": "No valid dateTime value exists",
        "type": "impossible"
      }
    },
    
    {
      "id": "issue-002",
      "type": "PERMISSION_PROHIBITION_CONFLICT",
      "severity": "ERROR",
      "permission": {
        "rule_id": "ex:permission:02",
        "action": "odrl:distribute",
        "constraint": "fileFormat eq JPEG"
      },
      "prohibition": {
        "rule_id": "ex:prohibition:01",
        "action": "odrl:distribute",
        "constraint": "fileFormat isAnyOf [JPEG, PNG]"
      },
      "counterexample": {
        "fileFormat": "JPEG",
        "explanation": "JPEG satisfies both permission and prohibition"
      }
    },
    
    {
      "id": "issue-003",
      "type": "REDUNDANCY",
      "severity": "WARNING",
      "rule_id": "ex:permission:03",
      "redundant_constraint": {
        "id": "ex:constraint:05",
        "expression": "count lteq 100"
      },
      "implied_by_constraint": {
        "id": "ex:constraint:04",
        "expression": "count lteq 50"
      },
      "suggestion": "Remove ex:constraint:05"
    }
  ],
  
  "inheritance_check": null
}
```

---

## 7. Inheritance Check Output

```json
{
  "parent_policy_id": "policy:parent",
  "child_policy_id": "policy:child",
  "inheritance_valid": false,
  "violations": [
    {
      "type": "EXPANSION",
      "severity": "ERROR",
      "parent_rule_id": "perm:parent:01",
      "child_rule_id": "perm:child:01",
      "parent_constraint": {
        "leftOperand": "odrl:fileFormat",
        "operator": "odrl:eq",
        "rightOperand": "JPEG"
      },
      "child_constraint": {
        "leftOperand": "odrl:fileFormat",
        "operator": "odrl:isAnyOf",
        "rightOperand": ["JPEG", "PNG"]
      },
      "counterexample": {
        "fileFormat": "PNG",
        "child_satisfied": true,
        "parent_satisfied": false,
        "explanation": "Child allows PNG, parent does not"
      }
    }
  ]
}
```

---

## 8. Visual Representation (Optional Web UI)

```
┌─────────────────────────────────────────────┐
│ Policy Analysis Report                      │
│ Policy ID: ex:policy:001                    │
│ Status: INVALID ❌                          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Summary                                     │
├─────────────────────────────────────────────┤
│ Total Rules:       5                        │
│ Total Constraints: 12                       │
│ Errors:           2 ❌                      │
│ Warnings:         1 ⚠️                      │
│ Analysis Time:    324ms                     │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Issues                                      │
└─────────────────────────────────────────────┘

❌ ERROR: INCONSISTENCY
   Rule: ex:permission:01
   
   Conflicting constraints:
   • dateTime >= 2025-01-01
   • dateTime <= 2024-12-31
   
   → No valid value exists

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ ERROR: PERMISSION-PROHIBITION CONFLICT
   
   Permission (ex:permission:02):
   • action = distribute
   • fileFormat = JPEG
   
   Prohibition (ex:prohibition:01):
   • action = distribute
   • fileFormat ∈ {JPEG, PNG}
   
   Overlap when: fileFormat = JPEG

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  WARNING: REDUNDANCY
   Rule: ex:permission:03
   
   Redundant: count <= 100
   Implied by: count <= 50
   
   → Suggestion: Remove count <= 100
```

---

## 9. Minimal Output (Success Case)

```json
{
  "policy_id": "ex:policy:002",
  "status": "VALID",
  "summary": {
    "errors": 0,
    "warnings": 0,
    "total_constraints": 5,
    "analysis_time_ms": 145
  }
}
```

CLI:
```
Policy: ex:policy:002
Status: VALID ✓
Analysis time: 145ms
```

---

## 10. Output Format Selection

### JSON (default)
```bash
odrl-analyze policy.json
odrl-analyze policy.json --format json
```

### Compact CLI
```bash
odrl-analyze policy.json --format cli
```

### Full CLI (verbose)
```bash
odrl-analyze policy.json --format cli --verbose
```

### HTML Report
```bash
odrl-analyze policy.json --format html --output report.html
```

---

## 11. Key Principles

**DO**:
- Show exact constraint expressions
- Include rule IDs and constraint IDs
- Provide counterexamples when available
- Suggest fixes for warnings
- Group issues by type
- Show severity clearly

❌ **DON'T**:
- Long explanatory text
- Repeat policy structure
- Explain what ODRL is
- Show internal Z3 formulas
- Include debug information (unless --debug flag)

---

## 12. Output Examples by Scenario

### Scenario 1: Inconsistent Permission
```
[ERROR] INCONSISTENCY in perm:01
  count gt 100 AND count lt 50
  → impossible
```

### Scenario 2: XONE Violation
```
[ERROR] XONE_VIOLATION in duty:01
  Expected: exactly 1 constraint satisfied
  Actual: 2 satisfied
  
  Both satisfied:
  • spatial eq Germany
  • spatial eq Europe
  
  When: spatial = Germany
```

### Scenario 3: Expansion
```
[ERROR] EXPANSION
  Parent: fileFormat eq JPEG
  Child:  fileFormat isAnyOf [JPEG, PNG]
  
  Counterexample: fileFormat = PNG
  → Child allows PNG, parent doesn't
```

### Scenario 4: Redundancy
```
[WARNING] REDUNDANCY in perm:03
  count lteq 100 ← redundant
  count lteq 50  ← stronger
  
  → Remove count lteq 100
```

---

## 13. Implementation

```python
@dataclass
class AnalysisResult:
    policy_id: str
    status: PolicyStatus
    summary: Summary
    issues: List[Issue]
    inheritance_check: Optional[InheritanceCheck] = None

class OutputFormatter:
    def format_json(self, result: AnalysisResult) -> str:
        return json.dumps(asdict(result), indent=2)
    
    def format_cli(self, result: AnalysisResult, verbose: bool = False) -> str:
        lines = [
            f"Policy: {result.policy_id}",
            f"Status: {self._status_icon(result.status)} {result.status}",
            ""
        ]
        
        if result.issues:
            lines.append("Issues:")
            lines.append("━" * 60)
            for issue in result.issues:
                lines.append(self._format_issue(issue, verbose))
                lines.append("━" * 60)
        
        lines.extend([
            "",
            "Summary:",
            f"  Errors:   {result.summary.errors}",
            f"  Warnings: {result.summary.warnings}",
            f"  Analysis time: {result.summary.analysis_time_ms}ms"
        ])
        
        return "\n".join(lines)
    
    def _format_issue(self, issue: Issue, verbose: bool) -> str:
        severity_icon = "❌" if issue.severity == "ERROR" else "⚠️"
        
        if issue.type == IssueType.INCONSISTENCY:
            return f"""
{severity_icon} {issue.severity}: {issue.type}
  Rule: {issue.rule_id}
  
  Conflicting:
  {self._format_constraints(issue.constraints)}
  
  → {issue.counterexample.get('explanation', 'impossible')}
"""
        
        elif issue.type == IssueType.PERMISSION_PROHIBITION_CONFLICT:
            return f"""
{severity_icon} {issue.severity}: PERMISSION-PROHIBITION CONFLICT
  
  Permission ({issue.permission.rule_id}):
  {self._format_constraint(issue.permission.constraint)}
  
  Prohibition ({issue.prohibition.rule_id}):
  {self._format_constraint(issue.prohibition.constraint)}
  
  Overlap: {self._format_counterexample(issue.counterexample)}
"""
        
        # ... other issue types
    
    def _status_icon(self, status: PolicyStatus) -> str:
        return {
            PolicyStatus.VALID: "✓",
            PolicyStatus.INVALID: "❌",
            PolicyStatus.WARNING: "⚠️"
        }.get(status, "?")
```

---

## Final Output Design

**Format**: JSON (machine) + Compact CLI (human)

**Structure**:
1. Policy ID + Status
2. Summary (counts)
3. Issues (errors first, then warnings)
4. Each issue: type, severity, involved rules/constraints, counterexample
5. Analysis metadata (time, version)

**Verbosity**:
- Default: Concise, actionable
- `--verbose`: Include full constraint details
- `--debug`: Include SMT formulas, solver logs

