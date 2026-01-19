## Action Semantics

In this work, ODRL actions are treated as **symbolic labels** used solely 
to partition constraint spaces. We do not interpret actions operationally, 
nor do we assume deontic entailment across action hierarchies (e.g., 
`read ⊑ use` does not imply that permitting `use` permits `read`).

Constraint satisfiability and inheritance are analyzed **independently 
for each action**:

$$\forall a \in \mathcal{A}: \llbracket \Pi_{child} \rrbracket_a \Rightarrow \llbracket \Pi_{parent} \rrbracket_a$$

This design ensures sound monotonic reasoning while remaining agnostic 
to policy enforcement semantics.

### Explicit Exclusions

This work does **not** model:
- Execution semantics of actions
- Effects of actions on assets  
- Deontic conflict resolution
- Hierarchical action entailment (`includedIn`)
- ODRL duty fulfillment semantics