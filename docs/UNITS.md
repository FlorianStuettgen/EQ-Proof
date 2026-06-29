# Units

Declare canonical units under the top-level `units` field:

```json
{
  "units": {
    "E": "J",
    "f": "Hz"
  }
}
```

Inputs can be plain numbers or unit-wrapped values:

```json
{
  "E": {"value": 0.42, "unit": "eV"},
  "f": {"value": 100, "unit": "kHz"}
}
```

The engine converts unit-wrapped inputs into canonical units before repair and records each conversion in the proof steps.

Supported units include SI base units, `Hz`, `J`, `V`, `ohm`, and `eV`, plus common ASCII prefixes such as `k`, `M`, `m`, `u`, and `n`.
