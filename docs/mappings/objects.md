# Objects Mapping

**Source:** `mapping/mapping-objects.x3ml`  
**Output:** `mapping/output/objects/objects.ttl`

---

```text
E22_Human-Made_Object
├── P1_is_identified_by
│   └── E33_E41_Linguistic_Appellation
│       ├── P190_has_symbolic_content → Literal
│       └── P2_has_type → E55_Type
│
├── P2_has_type
│   └── E55_Type
│       └── P127_has_broader_term → E55_Type
│           └── artwork / built_work
│
├── crmdig:L54_is_same-as
│   └── E22_Human-Made_Object
│       └── GND URI
│
├── P108i_was_produced_by
│   └── E12_Production
│       ├── P14_carried_out_by
│       │   └── E21_Person
│       └── P4_has_time-span
│           └── E52_Time-Span
│               ├── P82a_begin_of_the_begin → xsd:gYear
│               ├── P82b_end_of_the_end → xsd:gYear
│               ├── P2_has_type → E55_Type
│               └── rdfs:label → Literal
│
├── P67i_is_referred_to_by
│   └── E33_Linguistic_Object
│       ├── P2_has_type → E55_Type
│       └── P190_has_symbolic_content → Literal
│
├── P45_consists_of
│   └── E57_Material
│
├── P43_has_dimension
│   └── E54_Dimension
│       └── P90_has_value → Literal
│
├── P50_has_current_keeper
│   └── E74_Group
│
└── P55_has_current_location
    └── E53_Place
```


| Source | CIDOC CRM / CRMdig target |
|---|---|
| `object` | `crm:E22_Human-Made_Object` |
| `head[@type='main']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| `head[@type='alternative']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| `head[@type='hw']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| `@type` | `crm:P2_has_type → crm:E55_Type` |
| `note/idno[@type='GND']` | `crmdig:L54_is_same-as → crm:E22_Human-Made_Object` |
| `note/persName[@role='creator']` | `crm:P108i_was_produced_by → crm:E12_Production → crm:P14_carried_out_by → crm:E21_Person` |
| `preprocessed_date` | `crm:P108i_was_produced_by → crm:E12_Production → crm:P4_has_time-span → crm:E52_Time-Span` |
| `@preprocessed_dateLower` | `crm:P82a_begin_of_the_begin → xsd:gYear` |
| `@preprocessed_dateUpper` | `crm:P82b_end_of_the_end → xsd:gYear` |
| `@preprocessed_dateQualifier` | `crm:P2_has_type → crm:E55_Type` |
| `note/p` | `crm:P67i_is_referred_to_by → crm:E33_Linguistic_Object` |
| `note/p/material` | `crm:P45_consists_of → crm:E57_Material` |
| `note/p/dim` | `crm:P43_has_dimension → crm:E54_Dimension` |
| ancestor `organisation` | `crm:P50_has_current_keeper → crm:E74_Group` |
| ancestor `place` | `crm:P55_has_current_location → crm:E53_Place` |
