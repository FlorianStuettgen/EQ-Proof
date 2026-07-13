# Specification language

## Purpose

A specification declares the variables that may appear in a submitted output, their bounds and fixed status, and the linear equations that define feasibility.

The machine-readable contract is [`schemas/specification.schema.json`](../schemas/specification.schema.json). Runtime parsing applies additional semantic rules that JSON Schema cannot fully express, such as `lower <= upper`, Python-keyword rejection, unique equation IDs, and linearity.

## Root document

| Field | Required | Meaning |
| --- | :---: | --- |
| `schema_version` | ✓ | Must equal `1.0` |
| `name` | ✓ | Stable non-empty specification name |
| `description` | — | Human context |
| `metadata` | — | Free-form object preserved in the proof |
| `variables` | ✓ | Ordered object of variable rules |
| `equations` | — | Array of linear relations |

Unknown root, variable, and equation fields are rejected. This prevents misspellings from silently becoming ignored configuration.

## Variables

```json
"mechanical": {
  "lower": 0,
  "upper": 500000,
  "fixed": false,
  "label": "Mechanical budget",
  "unit": "CAD"
}
```

Variable names must be valid non-keyword Python identifiers because the expression language uses identifier syntax. Every submitted input must contain exactly the declared variables—no missing or extra names.

`fixed: true` means “preserve the submitted value exactly,” not “fix to a value written in the specification.” This design makes the artifact record the actual approved or committed value that governed the repair.

## Expression grammar

Conceptually:

```text
relation   := expression ("==" | "<=" | ">=") expression
expression := term (("+" | "-") term)*
term       := scalar "*" expression
            | expression "*" scalar
            | expression "/" scalar
            | variable
            | scalar
            | "(" expression ")"
scalar     := finite integer or floating-point literal
```

Examples:

```text
a + b == 1
civil + mechanical + electrical <= 1000000
q4 >= q3
2 * x - y / 4 == 7
```

Rejected examples:

```text
x * y == 1                     # nonlinear
x ** 2 <= 4                    # power
min(x, y) >= 0                 # function call
object.attribute == 1          # attribute access
__import__("os") == 0          # executable syntax
0 <= x <= 1                    # chained comparison; use bounds
```

The expression length and AST node count are capped to limit pathological inputs.

## Normalization

All relations are normalized to either:

```text
aᵀx == b
```

or:

```text
aᵀx <= b
```

A `>=` relation is multiplied by `-1`. Constants are moved to the right-hand side. Coefficients are ordered according to the variable order in the JSON document.

## Supported sets

| Declaration | Projection |
| --- | --- |
| lower/upper bounds | element-wise clipping |
| equality | hyperplane projection |
| inequality | half-space projection |
| fixed variable | coordinate elimination |

Their intersection must be convex. Integer, categorical, logical, nonlinear, and disjunctive constraints are outside the 1.x boundary.
