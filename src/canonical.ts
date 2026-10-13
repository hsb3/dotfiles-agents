// Canonical JSON as Python writes it: json.dumps(value, sort_keys=True,
// separators=(",", ":"), ensure_ascii=False). JSON.parse loses the difference
// between 1 and 1.0, so parseJson keeps each number's lexeme.

export class JsonNumber {
  constructor(
    readonly lexeme: string,
    readonly isFloat: boolean,
  ) {}
  get value(): number {
    return Number(this.lexeme);
  }
}

export class JsonSyntaxError extends Error {}

// Parses JSON text, keeping numbers as JsonNumber. Duplicate keys keep the last value.
export function parseJson(text: string): unknown {
  let i = 0;
  const fail = (what: string): never => {
    throw new JsonSyntaxError(`${what} at offset ${i}`);
  };
  const ws = () => {
    while (i < text.length) {
      const c = text.charCodeAt(i);
      if (c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d) i++;
      else break;
    }
  };
  const str = (): string => {
    i++; // opening quote
    let out = "";
    let start = i;
    while (true) {
      if (i >= text.length) fail("unterminated string");
      const c = text.charCodeAt(i);
      if (c === 0x22) {
        out += text.slice(start, i);
        i++;
        return out;
      }
      if (c < 0x20) fail("control character in string");
      if (c === 0x5c) {
        out += text.slice(start, i);
        const e = text[i + 1];
        i += 2;
        switch (e) {
          case '"': out += '"'; break;
          case "\\": out += "\\"; break;
          case "/": out += "/"; break;
          case "b": out += "\b"; break;
          case "f": out += "\f"; break;
          case "n": out += "\n"; break;
          case "r": out += "\r"; break;
          case "t": out += "\t"; break;
          case "u": {
            const hex = text.slice(i, i + 4);
            if (!/^[0-9a-fA-F]{4}$/.test(hex)) fail("bad unicode escape");
            out += String.fromCharCode(parseInt(hex, 16));
            i += 4;
            break;
          }
          default:
            fail("bad escape");
        }
        start = i;
        continue;
      }
      i++;
    }
  };
  const num = (): JsonNumber => {
    const m = /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/.exec(text.slice(i));
    if (!m) return fail("bad number");
    i += m[0].length;
    return new JsonNumber(m[0], m[2] !== undefined || m[3] !== undefined);
  };
  const value = (): unknown => {
    ws();
    const c = text[i];
    if (c === "{") {
      i++;
      const obj: Record<string, unknown> = {};
      ws();
      if (text[i] === "}") {
        i++;
        return obj;
      }
      while (true) {
        ws();
        if (text[i] !== '"') fail("expected key");
        const k = str();
        ws();
        if (text[i] !== ":") fail("expected ':'");
        i++;
        const v = value();
        Object.defineProperty(obj, k, { value: v, enumerable: true, writable: true, configurable: true });
        ws();
        if (text[i] === ",") {
          i++;
          continue;
        }
        if (text[i] === "}") {
          i++;
          return obj;
        }
        fail("expected ',' or '}'");
      }
    }
    if (c === "[") {
      i++;
      const arr: unknown[] = [];
      ws();
      if (text[i] === "]") {
        i++;
        return arr;
      }
      while (true) {
        arr.push(value());
        ws();
        if (text[i] === ",") {
          i++;
          continue;
        }
        if (text[i] === "]") {
          i++;
          return arr;
        }
        fail("expected ',' or ']'");
      }
    }
    if (c === '"') return str();
    if (text.startsWith("true", i)) {
      i += 4;
      return true;
    }
    if (text.startsWith("false", i)) {
      i += 5;
      return false;
    }
    if (text.startsWith("null", i)) {
      i += 4;
      return null;
    }
    return num();
  };
  const result = value();
  ws();
  if (i !== text.length) fail("trailing data");
  return result;
}

// Replaces every JsonNumber with a plain number.
export function plain(value: unknown): unknown {
  if (value instanceof JsonNumber) return value.value;
  if (Array.isArray(value)) return value.map(plain);
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      Object.defineProperty(out, k, { value: plain(v), enumerable: true, writable: true, configurable: true });
    }
    return out;
  }
  return value;
}

// Python's repr() of a float: shortest round-trip digits, positional when the
// decimal exponent is in [-4, 16), otherwise d[.ddd]e±XX.
export function pythonFloatRepr(x: number): string {
  if (!Number.isFinite(x)) throw new Error(`not a finite number: ${x}`);
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const sign = x < 0 ? "-" : "";
  const [mantissa, expText] = Math.abs(x).toExponential().split("e") as [string, string];
  const digits = mantissa.replace(".", "");
  const exp = Number(expText);
  if (exp >= -4 && exp < 16) {
    if (exp < 0) return `${sign}0.${"0".repeat(-exp - 1)}${digits}`;
    const intPart = digits.slice(0, exp + 1).padEnd(exp + 1, "0");
    const frac = digits.slice(exp + 1) || "0";
    return `${sign}${intPart}.${frac}`;
  }
  const rest = digits.slice(1);
  const e = Math.abs(exp).toString().padStart(2, "0");
  return `${sign}${digits[0]}${rest ? "." + rest : ""}e${exp < 0 ? "-" : "+"}${e}`;
}

function pythonInt(lexeme: string): string {
  const intPart = lexeme.replace(/^-/, "");
  if (/^0+$/.test(intPart)) return "0";
  return lexeme;
}

function quote(s: string): string {
  let out = '"';
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c === 0x22) out += '\\"';
    else if (c === 0x5c) out += "\\\\";
    else if (c < 0x20) {
      if (c === 0x08) out += "\\b";
      else if (c === 0x0c) out += "\\f";
      else if (c === 0x0a) out += "\\n";
      else if (c === 0x0d) out += "\\r";
      else if (c === 0x09) out += "\\t";
      else out += "\\u" + c.toString(16).padStart(4, "0");
    } else out += s[i];
  }
  return out + '"';
}

// Orders strings by Unicode code point, as Python sorts str.
export function compareCodePoints(a: string, b: string): number {
  const ia = a[Symbol.iterator]();
  const ib = b[Symbol.iterator]();
  while (true) {
    const x = ia.next();
    const y = ib.next();
    if (x.done || y.done) return x.done && y.done ? 0 : x.done ? -1 : 1;
    const cx = x.value.codePointAt(0)!;
    const cy = y.value.codePointAt(0)!;
    if (cx !== cy) return cx - cy;
  }
}

export function canonicalJson(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (value instanceof JsonNumber) return value.isFloat ? pythonFloatRepr(value.value) : pythonInt(value.lexeme);
  if (typeof value === "number") return Number.isInteger(value) && !Object.is(value, -0) ? String(value) : pythonFloatRepr(value);
  if (typeof value === "string") return quote(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (typeof value === "object") {
    const keys = Object.keys(value).sort(compareCodePoints);
    const obj = value as Record<string, unknown>;
    return `{${keys.map((k) => `${quote(k)}:${canonicalJson(obj[k])}`).join(",")}}`;
  }
  throw new Error(`cannot serialise ${typeof value}`);
}

export function sha256Hex(data: string | Uint8Array): string {
  return new Bun.CryptoHasher("sha256").update(data).digest("hex");
}

export function canonicalSha256(value: unknown): string {
  return sha256Hex(canonicalJson(value));
}
