# Persons Mapping

**Source:** `mapping/mapping-persons.x3ml`  
**Output:** `mapping/output/persons/persons.ttl`

---


```text
E21_Person
├── P1_is_identified_by
│   └── E33_E41_Linguistic_Appellation
│       ├── P190_has_symbolic_content → Literal
│       └── P2_has_type → E55_Type
│
├── crmdig:L54_is_same-as
│   ├── E21_Person (GND URI)
│   ├── E21_Person (ULAN URI)
│   └── E21_Person (VIAF URI)
│
├── P98i_was_born
│   └── E67_Birth
│       └── P4_has_time-span
│           └── E52_Time-Span
│               ├── P82a_begin_of_the_begin → xsd:gYear
│               ├── P82b_end_of_the_end → xsd:gYear
│               ├── P2_has_type → E55_Type
│               └── rdfs:label → Literal
│
└── P100i_died_in
    └── E69_Death
        └── P4_has_time-span
            └── E52_Time-Span
                ├── P82a_begin_of_the_begin → xsd:gYear
                ├── P82b_end_of_the_end → xsd:gYear
                ├── P2_has_type → E55_Type
                └── rdfs:label → Literal
```


| Source | CIDOC CRM / CRMdig target |
|---|---|
| `//person` | `crm:E21_Person` |
| `persName[@type='main']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| `persName[@type='alternative']` | `crm:P1_is_identified_by → crm:E33_E41_Linguistic_Appellation` |
| `idno[@type='GND']` | `crmdig:L54_is_same-as → crm:E21_Person` |
| `idno[@type='ULAN']` | `crmdig:L54_is_same-as → crm:E21_Person` |
| `idno[@type='VIAF']` | `crmdig:L54_is_same-as → crm:E21_Person` |
| `preprocessed_birth` | `crm:P98i_was_born → crm:E67_Birth → crm:P4_has_time-span → crm:E52_Time-Span` |
| `@preprocessed_dateLower` (birth) | `crm:P82a_begin_of_the_begin → xsd:gYear` |
| `@preprocessed_dateUpper` (birth) | `crm:P82b_end_of_the_end → xsd:gYear` |
| `@preprocessed_dateQualifier` (birth) | `crm:P2_has_type → crm:E55_Type` |
| text of `preprocessed_birth` | `rdfs:label → Literal` on `crm:E52_Time-Span` |
| `preprocessed_death` | `crm:P100i_died_in → crm:E69_Death → crm:P4_has_time-span → crm:E52_Time-Span` |
| `@preprocessed_dateLower` (death) | `crm:P82a_begin_of_the_begin → xsd:gYear` |
| `@preprocessed_dateUpper` (death) | `crm:P82b_end_of_the_end → xsd:gYear` |
| `@preprocessed_dateQualifier` (death) | `crm:P2_has_type → crm:E55_Type` |
| text of `preprocessed_death` | `rdfs:label → Literal` on `crm:E52_Time-Span` |
