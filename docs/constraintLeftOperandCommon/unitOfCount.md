## unitOfCount - Complete Formal Semantics

---

### 1. Syntactic Definition

#### 1.1 Vocabulary Domain

Let $\mathcal{P}$ denote the set of all ODRL profiles. Each profile $p \in \mathcal{P}$ defines a vocabulary of counting units:

$$\mathcal{U}_p = \{ u_1, u_2, \ldots, u_n \} \quad \text{(finite, profile-specific)}$$

**Common vocabulary** (frequently defined across profiles):

$$\mathcal{U}_{\text{common}} = \{ \texttt{perUser}, \texttt{perDevice}, \texttt{perOrganization}, \texttt{perSession} \}$$

**Global vocabulary** (union across all profiles):

$$\mathcal{U} = \bigcup_{p \in \mathcal{P}} \mathcal{U}_p$$

#### 1.2 Constraint Syntax

A `unitOfCount` constraint has the form:

$$c ::= \langle \texttt{unitOfCount}, \textit{op}, V \rangle$$

Where:
- $\textit{op} \in \{ \texttt{eq}, \texttt{neq}, \texttt{isAnyOf}, \texttt{isNoneOf} \}$
- $V \in \mathcal{U}$ for unary operators
- $V \subseteq \mathcal{U}$ for set operators

---

### 2. Denotational Semantics

#### 2.1 Execution Event Model

Let $E$ be the set of all action execution events. Each event $e \in E$ carries attributes:

$$e = \langle \textit{action}, \textit{user}, \textit{device}, \textit{org}, \textit{session}, \textit{timestamp}, \ldots \rangle$$

#### 2.2 Projection Functions

Each counting unit $u \in \mathcal{U}$ defines a **projection function** that extracts the relevant attribute:

$$\pi : \mathcal{U} \rightarrow (E \rightarrow \mathcal{A})$$

Where $\mathcal{A}$ is a universal attribute domain. Specifically:

$$\pi(u) = \begin{cases}
\lambda e. e.\textit{user} & \text{if } u = \texttt{perUser} \\
\lambda e. e.\textit{device} & \text{if } u = \texttt{perDevice} \\
\lambda e. e.\textit{org} & \text{if } u = \texttt{perOrganization} \\
\lambda e. e.\textit{session} & \text{if } u = \texttt{perSession} \\
\lambda e. e.\textit{id} & \text{if } u = \texttt{perExecution} \text{ (default)}
\end{cases}$$

#### 2.3 Equivalence Relation

Each counting unit induces an **equivalence relation** over events:

$$e_1 \sim_u e_2 \iff \pi(u)(e_1) = \pi(u)(e_2)$$

**Quotient set** (equivalence classes):

$$E / {\sim_u} = \{ [e]_u \mid e \in E \}$$

Where $[e]_u = \{ e' \in E \mid e' \sim_u e \}$

#### 2.4 Counting Semantics

The **count** under unit $u$ is the cardinality of the quotient set:

$$\texttt{Count}_u(E) = |E / {\sim_u}| = |\{ \pi(u)(e) \mid e \in E \}|$$

**Equivalently** (set of distinct attribute values):

$$\texttt{Count}_u(E) = |\text{image}(\pi(u)|_E)|$$

---

### 3. Constraint Satisfaction Semantics

#### 3.1 Interpretation Function

Let $\mathcal{I}$ be an interpretation that assigns a counting unit to a policy scope:

$$\mathcal{I} : \textit{Scope} \rightarrow \mathcal{U}$$

#### 3.2 Satisfaction Relation

A constraint $c = \langle \texttt{unitOfCount}, \textit{op}, V \rangle$ is satisfied under interpretation $\mathcal{I}$ for scope $s$:

$$\mathcal{I}, s \models c \iff \llbracket c \rrbracket_{\mathcal{I}(s)}$$

Where the **denotation** $\llbracket c \rrbracket_u$ specifies the set of valid units:

$$\llbracket \langle \texttt{unitOfCount}, \texttt{eq}, v \rangle \rrbracket = \{ v \}$$

$$\llbracket \langle \texttt{unitOfCount}, \texttt{neq}, v \rangle \rrbracket = \mathcal{U} \setminus \{ v \}$$

$$\llbracket \langle \texttt{unitOfCount}, \texttt{isAnyOf}, V \rangle \rrbracket = V$$

$$\llbracket \langle \texttt{unitOfCount}, \texttt{isNoneOf}, V \rangle \rrbracket = \mathcal{U} \setminus V$$

#### 3.3 Satisfaction Condition

$$\mathcal{I}, s \models c \iff \mathcal{I}(s) \in \llbracket c \rrbracket$$

---

### 4. Interaction with `count` LeftOperand

#### 4.1 Semantic Binding

When `unitOfCount` and `count` appear in the same scope, they form a **semantic pair**:

$$\langle \texttt{count}, \textit{op}_n, n \rangle \bowtie \langle \texttt{unitOfCount}, \texttt{eq}, u \rangle$$

**Combined semantics:**

$$\mathcal{I}, E \models (\texttt{count } \textit{op}_n \; n) \bowtie (\texttt{unitOfCount} = u) \iff \texttt{Count}_u(E) \; \textit{op}_n \; n$$

#### 4.2 Formal Definition

$$\llbracket \texttt{count } \textit{op} \; n \rrbracket_u(E) = \begin{cases}
\top & \text{if } \texttt{Count}_u(E) \; \textit{op} \; n \\
\bot & \text{otherwise}
\end{cases}$$

**Expanded for each operator:**

$$\llbracket \texttt{count eq } n \rrbracket_u(E) = \top \iff |E/{\sim_u}| = n$$

$$\llbracket \texttt{count lteq } n \rrbracket_u(E) = \top \iff |E/{\sim_u}| \leq n$$

$$\llbracket \texttt{count gteq } n \rrbracket_u(E) = \top \iff |E/{\sim_u}| \geq n$$

$$\llbracket \texttt{count lt } n \rrbracket_u(E) = \top \iff |E/{\sim_u}| < n$$

$$\llbracket \texttt{count gt } n \rrbracket_u(E) = \top \iff |E/{\sim_u}| > n$$

#### 4.3 Default Scope

When `unitOfCount` is absent, the default is raw execution counting:

$$u_{\text{default}} = \texttt{perExecution}$$

$$\pi(\texttt{perExecution}) = \lambda e. e.\textit{id}$$

Thus $e_1 \sim_{\texttt{perExecution}} e_2 \iff e_1 = e_2$ (identity relation).

---

### 5. SMT Encoding

#### 5.1 Enumeration Mapping

Define an injective mapping from vocabulary to integers:

$$\eta : \mathcal{U} \hookrightarrow \mathbb{Z}$$

For the common vocabulary:

$$\eta(\texttt{perUser}) = 0$$
$$\eta(\texttt{perDevice}) = 1$$
$$\eta(\texttt{perOrganization}) = 2$$
$$\eta(\texttt{perSession}) = 3$$

#### 5.2 Z3 Variable

For each scope $s$, introduce an integer variable:

$$x_s : \texttt{Int}$$

**Domain constraint:**

$$\phi_{\text{dom}}(x_s) = (0 \leq x_s \leq |\mathcal{U}| - 1)$$

#### 5.3 Constraint Encoding

$$\texttt{Enc} : \textit{Constraint} \times \textit{Var} \rightarrow \textit{Formula}$$

$$\texttt{Enc}(\langle \texttt{unitOfCount}, \texttt{eq}, v \rangle, x) = (x = \eta(v))$$

$$\texttt{Enc}(\langle \texttt{unitOfCount}, \texttt{neq}, v \rangle, x) = (x \neq \eta(v))$$

$$\texttt{Enc}(\langle \texttt{unitOfCount}, \texttt{isAnyOf}, V \rangle, x) = \bigvee_{v \in V} (x = \eta(v))$$

$$\texttt{Enc}(\langle \texttt{unitOfCount}, \texttt{isNoneOf}, V \rangle, x) = \bigwedge_{v \in V} (x \neq \eta(v))$$

#### 5.4 Complete Encoding with Domain

$$\texttt{Enc}^*(c, x) = \phi_{\text{dom}}(x) \land \texttt{Enc}(c, x)$$

---

### 6. Conflict Detection

#### 6.1 Satisfiability-Based Detection

Two constraints $c_1, c_2$ over the same scope are **in conflict** iff:

$$\texttt{CONFLICT}(c_1, c_2) \iff \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset$$

**SMT formulation:**

$$\texttt{CONFLICT}(c_1, c_2) \iff \texttt{UNSAT}(\texttt{Enc}^*(c_1, x) \land \texttt{Enc}^*(c_2, x))$$

#### 6.2 Conflict Rules (Derived)

**Rule 1: Equal to different values**

$$\frac{v_1 \neq v_2}{\texttt{CONFLICT}(\texttt{eq } v_1, \texttt{eq } v_2)}$$

*Proof:* $\{v_1\} \cap \{v_2\} = \emptyset$ when $v_1 \neq v_2$

**Rule 2: Equal and not equal to same value**

$$\frac{}{\texttt{CONFLICT}(\texttt{eq } v, \texttt{neq } v)}$$

*Proof:* $\{v\} \cap (\mathcal{U} \setminus \{v\}) = \emptyset$

**Rule 3: Equal and excluded from set containing it**

$$\frac{v \in V}{\texttt{CONFLICT}(\texttt{eq } v, \texttt{isNoneOf } V)}$$

*Proof:* $\{v\} \cap (\mathcal{U} \setminus V) = \emptyset$ when $v \in V$

**Rule 4: isAnyOf disjoint sets**

$$\frac{V_1 \cap V_2 = \emptyset}{\texttt{CONFLICT}(\texttt{isAnyOf } V_1, \texttt{isAnyOf } V_2)}$$

**Rule 5: isAnyOf excluded by isNoneOf**

$$\frac{V_1 \subseteq V_2}{\texttt{CONFLICT}(\texttt{isAnyOf } V_1, \texttt{isNoneOf } V_2)}$$

#### 6.3 Compatibility Rules

**Rule C1: Same value**

$$\frac{}{\texttt{COMPATIBLE}(\texttt{eq } v, \texttt{eq } v)}$$

**Rule C2: Equal within allowed set**

$$\frac{v \in V}{\texttt{COMPATIBLE}(\texttt{eq } v, \texttt{isAnyOf } V)}$$

**Rule C3: Not equal, not excluded**

$$\frac{v_1 \neq v_2}{\texttt{POSSIBLY-COMPATIBLE}(\texttt{neq } v_1, \texttt{neq } v_2)}$$

*Witness:* Any $v \in \mathcal{U} \setminus \{v_1, v_2\}$ satisfies both (when $|\mathcal{U}| \geq 3$)

---

### 7. Profile-Sensitive Semantics

#### 7.1 Profile Context

Each policy $P$ is associated with a profile:

$$\textit{profile} : \textit{Policy} \rightarrow \mathcal{P}$$

#### 7.2 Profile-Local Interpretation

The meaning of a vocabulary term depends on profile context:

$$\llbracket u \rrbracket_p : \mathcal{U}_p \rightarrow (E \rightarrow \mathcal{A})$$

**Key property:** The same local name may have different semantics across profiles:

$$\llbracket \texttt{perUser} \rrbracket_{p_1} \neq \llbracket \texttt{perUser} \rrbracket_{p_2} \quad \text{(possible)}$$

Example: `perUser` in an enterprise profile might mean "per authenticated employee," while in a consumer profile it might mean "per registered account."

#### 7.3 Cross-Profile Comparison

**Conservative rule:**

$$\frac{\textit{profile}(P_1) \neq \textit{profile}(P_2)}{\texttt{UNKNOWN}(c_1 \in P_1, c_2 \in P_2)}$$

**Rationale:** Without profile alignment ontology, semantic equivalence cannot be determined.

#### 7.4 Profile Alignment (Optional Extension)

If a profile alignment $\alpha : \mathcal{U}_{p_1} \rightharpoonup \mathcal{U}_{p_2}$ is provided:

$$\frac{\alpha(u_1) = u_2}{\llbracket u_1 \rrbracket_{p_1} \equiv \llbracket u_2 \rrbracket_{p_2}}$$

This enables cross-profile conflict detection when alignments exist.

---

### 8. Structural Validation Rules

Beyond satisfiability, `unitOfCount` requires structural validation:

#### 8.1 Well-Formedness Rules

**Rule WF1: Orphan Detection**

$$\frac{\texttt{unitOfCount} \in \textit{constraints}(R) \quad \texttt{count} \notin \textit{leftOperands}(R)}{\texttt{WARNING}: \text{orphan unitOfCount}}$$

**Rule WF2: Operator Validity**

$$\frac{\textit{op} \notin \{\texttt{eq}, \texttt{neq}, \texttt{isAnyOf}, \texttt{isNoneOf}\}}{\texttt{INVALID}: \text{operator } \textit{op} \text{ not valid for unitOfCount}}$$

**Rule WF3: Vocabulary Membership**

$$\frac{v \notin \mathcal{U}_{\textit{profile}(P)}}{\texttt{WARNING}: \text{unknown vocabulary term } v}$$

#### 8.2 Cardinality Rules

**Rule Card1: Single Value per Scope**

A scope should have at most one effective `unitOfCount` value:

$$\frac{|\{ v \mid \langle \texttt{unitOfCount}, \texttt{eq}, v \rangle \in \textit{constraints}(s) \}| > 1}{\texttt{CONFLICT}: \text{multiple unitOfCount values}}$$

---

### 9. Abstract Interpretation

#### 9.1 Abstract Domain

The abstract domain for `unitOfCount` is the powerset of vocabulary:

$$\hat{\mathcal{U}} = \mathcal{P}(\mathcal{U})$$

With partial order $\sqsubseteq$ defined as subset inclusion.

#### 9.2 Abstraction Function

$$\alpha : \textit{Constraint} \rightarrow \hat{\mathcal{U}}$$

$$\alpha(\langle \texttt{unitOfCount}, \texttt{eq}, v \rangle) = \{v\}$$

$$\alpha(\langle \texttt{unitOfCount}, \texttt{neq}, v \rangle) = \mathcal{U} \setminus \{v\}$$

$$\alpha(\langle \texttt{unitOfCount}, \texttt{isAnyOf}, V \rangle) = V$$

$$\alpha(\langle \texttt{unitOfCount}, \texttt{isNoneOf}, V \rangle) = \mathcal{U} \setminus V$$

#### 9.3 Meet Operation (Conjunction)

$$\alpha(c_1) \sqcap \alpha(c_2) = \alpha(c_1) \cap \alpha(c_2)$$

**Conflict detection:**

$$\texttt{CONFLICT}(c_1, c_2) \iff \alpha(c_1) \sqcap \alpha(c_2) = \emptyset$$

#### 9.4 Join Operation (Disjunction)

$$\alpha(c_1) \sqcup \alpha(c_2) = \alpha(c_1) \cup \alpha(c_2)$$

---

### 10. Soundness Theorem

**Theorem 10.1 (Soundness of Conflict Detection):**

For any two `unitOfCount` constraints $c_1, c_2$ within the same profile and scope:

$$\texttt{CONFLICT}(c_1, c_2) \implies \neg \exists u \in \mathcal{U}. \; (u \in \llbracket c_1 \rrbracket \land u \in \llbracket c_2 \rrbracket)$$

*Proof:* Direct from the definition of $\llbracket \cdot \rrbracket$ as set denotation and conflict as empty intersection. $\square$

**Theorem 10.2 (Completeness within Closed Vocabulary):**

If $\mathcal{U}$ is finite and known:

$$\neg \exists u \in \mathcal{U}. \; (u \in \llbracket c_1 \rrbracket \land u \in \llbracket c_2 \rrbracket) \implies \texttt{CONFLICT}(c_1, c_2)$$

*Proof:* Finite domain enumeration. $\square$

**Theorem 10.3 (Conservative Cross-Profile Handling):**

For constraints from different profiles:

$$\texttt{UNKNOWN}(c_1, c_2) \text{ is sound}$$

*Proof:* Without profile alignment, semantic equivalence of vocabulary terms cannot be established. Returning UNKNOWN avoids false positives and false negatives. $\square$


### 12. Example Computations

#### Example 1: Counting with Different Units

```python
# Events
events = [
    ExecutionEvent("e1", "alice", "laptop1", "acme", "s1", 1000),
    ExecutionEvent("e2", "alice", "phone1", "acme", "s2", 1001),
    ExecutionEvent("e3", "bob", "laptop1", "acme", "s1", 1002),
    ExecutionEvent("e4", "bob", "laptop2", "acme", "s3", 1003),
]

# Count_perUser(E) = |{alice, bob}| = 2
CountingSemantics.count("perUser", events)  # → 2

# Count_perDevice(E) = |{laptop1, phone1, laptop2}| = 3
CountingSemantics.count("perDevice", events)  # → 3

# Count_perSession(E) = |{s1, s2, s3}| = 3
CountingSemantics.count("perSession", events)  # → 3

# Count_perExecution(E) = |{e1, e2, e3, e4}| = 4
CountingSemantics.count("perExecution", events)  # → 4
```

#### Example 2: Conflict Detection

```python
sem = UnitOfCountSemantics()

# eq perUser ∧ eq perDevice → CONFLICT
c1 = UnitOfCountConstraint("eq", "perUser")
c2 = UnitOfCountConstraint("eq", "perDevice")
sem.detect_conflict(c1, c2)  # → CONFLICT

# eq perUser ∧ isAnyOf {perUser, perDevice} → COMPATIBLE
c3 = UnitOfCountConstraint("isAnyOf", {"perUser", "perDevice"})
sem.detect_conflict(c1, c3)  # → COMPATIBLE

# eq perUser ∧ isNoneOf {perUser} → CONFLICT
c4 = UnitOfCountConstraint("isNoneOf", {"perUser"})
sem.detect_conflict(c1, c4)  # → CONFLICT

# Cross-profile → UNKNOWN
c5 = UnitOfCountConstraint("eq", "perUser", profile="profile_A")
c6 = UnitOfCountConstraint("eq", "perUser", profile="profile_B")
sem.detect_conflict(c5, c6)  # → UNKNOWN
```

---

### 13. LaTeX Summary

```latex
\subsection{unitOfCount Formal Semantics}

\paragraph{Domain.}
Let $\mathcal{U}_p$ denote the vocabulary of counting units defined by profile $p$.
Common values include $\{\texttt{perUser}, \texttt{perDevice}, \texttt{perOrganization}, \texttt{perSession}\}$.

\paragraph{Projection Function.}
Each unit $u \in \mathcal{U}$ defines a projection $\pi(u) : E \to \mathcal{A}$
that extracts the relevant attribute from execution events.

\paragraph{Equivalence Relation.}
The unit induces an equivalence relation: $e_1 \sim_u e_2 \iff \pi(u)(e_1) = \pi(u)(e_2)$.

\paragraph{Counting Semantics.}
\[
\texttt{Count}_u(E) = |E / {\sim_u}| = |\{ \pi(u)(e) \mid e \in E \}|
\]

\paragraph{Constraint Denotation.}
\begin{align*}
\llbracket \texttt{eq } v \rrbracket &= \{v\} \\
\llbracket \texttt{neq } v \rrbracket &= \mathcal{U} \setminus \{v\} \\
\llbracket \texttt{isAnyOf } V \rrbracket &= V \\
\llbracket \texttt{isNoneOf } V \rrbracket &= \mathcal{U} \setminus V
\end{align*}

\paragraph{Conflict Detection.}
\[
\texttt{CONFLICT}(c_1, c_2) \iff \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset
\]

\paragraph{SMT Encoding.}
Vocabulary terms are mapped to integers via $\eta : \mathcal{U} \hookrightarrow \mathbb{Z}$.
Constraints encode as:
\[
\texttt{Enc}(\texttt{eq } v, x) = (x = \eta(v))
\]

\paragraph{Soundness.}
Conflict detection is sound: detected conflicts imply no satisfying assignment exists.
Within a closed vocabulary, detection is also complete.
Cross-profile comparisons conservatively return \texttt{UNKNOWN}.
```

---

This completes the formal semantics for `unitOfCount`. The key insight is that it's a **meta-semantic modifier** that changes how counting is interpreted, not a numeric constraint itself. The formal model captures this through projection functions, equivalence relations, and profile-sensitive vocabulary handling.