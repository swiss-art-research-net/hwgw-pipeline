# Organizations Mapping

**Source:** `mapping/mapping-organizations.x3ml`  
**Output:** `mapping/output/organizations/organizations.ttl`

---

```text
E74_Group
├── P1_is_identified_by
│   └── E33_E41_Linguistic_Appellation
│       ├── P190_has_symbolic_content → Literal
│       └── P2_has_type → E55_Type
│
├── P1_is_identified_by
│   └── E33_E41_Linguistic_Appellation
│       ├── P190_has_symbolic_content → Literal
│       └── P2_has_type → E55_Type
│
├── crmdig:L54_is_same-as
│   └── E74_Group (GND URI)
│
├── P3_has_note → Literal
│
└── aaao:ZP26i_is_residence_subject_of
    └── aaao:ZE9_Residential_Status
        └── aaao:ZP27_acribes_residence_place
            └── E53_Place
```


| Source | CIDOC CRM / CRMdig / AAAo target |
|---|---|
| `//org` | `crm:E74_Group` |
| `orgName[@type='main']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| main organisation name | `crm:P190_has_symbolic_content → rdfs:Literal` |
| main organisation name | `crm:P2_has_type → crm:E55_Type` (`preferred terms`) |
| `orgName[@type='short']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| short organisation name | `crm:P190_has_symbolic_content → rdfs:Literal` |
| short organisation name | `crm:P2_has_type → crm:E55_Type` (`nonpreferred term`) |
| `idno[@type='GND']` | `crmdig:L54_is_same-as → crm:E74_Group` |
| `note` with text | `crm:P3_has_note → rdfs:Literal` |
| `placeName[@ref]` | `aaao:ZP26i_is_residence_subject_of → aaao:ZE9_Residential_Status` |
| `@ref` on `placeName` | `aaao:ZE9_Residential_Status` URI identifier |
| `placeName[@ref]` | `aaao:ZP27_acribes_residence_place → crm:E53_Place` |
| `@ref` on `placeName` | `crm:E53_Place` URI identifier |
| `placeName` text | `crm:E53_Place` label |

