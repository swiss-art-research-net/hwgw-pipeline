# Places Mapping

**Source:** `mapping/mapping-places.x3ml`  
**Output:** `mapping/output/places/places.ttl`

---

```text
E53_Place
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
│   └── E53_Place (GND URI)
│
└── P3_has_note → Literal
```


| Source | CIDOC CRM / CRMdig target |
|---|---|
| `//place` | `crm:E53_Place` |
| `placeName[@type='main']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| main place name | `crm:P190_has_symbolic_content → rdfs:Literal` |
| main place name | `crm:P2_has_type → crm:E55_Type` (`preferred terms`) |
| `placeName[@type='alternative']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| alternative place name | `crm:P190_has_symbolic_content → rdfs:Literal` |
| alternative place name | `crm:P2_has_type → crm:E55_Type` (`nonpreferred term`) |
| `idno[@type='GND']` | `crmdig:L54_is_same-as → crm:E53_Place` |
| `note` with text | `crm:P3_has_note → rdfs:Literal` |
