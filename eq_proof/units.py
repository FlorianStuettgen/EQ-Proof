from typing import Dict


BASE = {
    "": ((0, 0, 0, 0, 0, 0, 0), 1.0),
    "m": ((1, 0, 0, 0, 0, 0, 0), 1.0),
    "kg": ((0, 1, 0, 0, 0, 0, 0), 1.0),
    "s": ((0, 0, 1, 0, 0, 0, 0), 1.0),
    "A": ((0, 0, 0, 1, 0, 0, 0), 1.0),
    "K": ((0, 0, 0, 0, 1, 0, 0), 1.0),
    "mol": ((0, 0, 0, 0, 0, 1, 0), 1.0),
    "cd": ((0, 0, 0, 0, 0, 0, 1), 1.0),
}

DERIVED = {
    "Hz": ((0, 0, -1, 0, 0, 0, 0), 1.0),
    "J": ((2, 1, -2, 0, 0, 0, 0), 1.0),
    "V": ((2, 1, -3, -1, 0, 0, 0), 1.0),
    "ohm": ((2, 1, -3, -2, 0, 0, 0), 1.0),
    "eV": ((2, 1, -2, 0, 0, 0, 0), 1.602176634e-19),
}

PREFIX = {
    "Y": 1e24,
    "Z": 1e21,
    "E": 1e18,
    "P": 1e15,
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "h": 1e2,
    "da": 1e1,
    "d": 1e-1,
    "c": 1e-2,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    "a": 1e-18,
    "z": 1e-21,
    "y": 1e-24,
}

CONSTANTS = {
    "h": ("J*s", 6.62607015e-34),
    "hbar": ("J*s", 1.054571817e-34),
    "c": ("m/s", 299792458.0),
    "k_B": ("J/K", 1.380649e-23),
    "q_e": ("A*s", 1.602176634e-19),
}


def _mul(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _div(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _pow(a, power):
    return tuple(x * power for x in a)


def _atom(token):
    if token in BASE:
        return BASE[token]
    if token in DERIVED:
        return DERIVED[token]
    if len(token) >= 2 and token[:2] in PREFIX and token[2:] in BASE:
        dim, factor = BASE[token[2:]]
        return dim, factor * PREFIX[token[:2]]
    if len(token) >= 2 and token[:2] in PREFIX and token[2:] in DERIVED:
        dim, factor = DERIVED[token[2:]]
        return dim, factor * PREFIX[token[:2]]
    if token[:1] in PREFIX and token[1:] in BASE:
        dim, factor = BASE[token[1:]]
        return dim, factor * PREFIX[token[:1]]
    if token[:1] in PREFIX and token[1:] in DERIVED:
        dim, factor = DERIVED[token[1:]]
        return dim, factor * PREFIX[token[:1]]
    raise ValueError(f"Unknown unit token: {token}")


def parse_unit(unit: str):
    if not unit or unit == "1":
        return BASE[""]
    unit = unit.replace(" ", "")
    numerator, *denominator = unit.split("/")
    dim = BASE[""][0]
    factor = 1.0

    for token in filter(None, numerator.split("*")):
        base, power = token.split("^") if "^" in token else (token, "1")
        parsed_dim, parsed_factor = _atom(base)
        int_power = int(power)
        dim = _mul(dim, _pow(parsed_dim, int_power))
        factor *= parsed_factor**int_power

    if denominator:
        for token in filter(None, "*".join(denominator).split("*")):
            base, power = token.split("^") if "^" in token else (token, "1")
            parsed_dim, parsed_factor = _atom(base)
            int_power = int(power)
            dim = _div(dim, _pow(parsed_dim, int_power))
            factor /= parsed_factor**int_power
    return dim, factor


def convert(value, from_unit, to_unit):
    from_dim, from_factor = parse_unit(from_unit)
    to_dim, to_factor = parse_unit(to_unit)
    if from_dim != to_dim:
        raise ValueError("Incompatible units")
    return (value * from_factor) / to_factor


def coerce_inputs_to_spec_units(values: dict, spec_units: Dict[str, str]):
    steps = []
    out = dict(values)
    for key, unit in spec_units.items():
        if isinstance(values.get(key), dict) and "value" in values[key] and "unit" in values[key]:
            value = float(values[key]["value"])
            from_unit = str(values[key]["unit"])
            converted = convert(value, from_unit, unit)
            out[key] = converted
            steps.append(
                {
                    "op": "unit_convert",
                    "var": key,
                    "from": from_unit,
                    "to": unit,
                    "value_in": value,
                    "value_out": converted,
                }
            )
    return out, steps
