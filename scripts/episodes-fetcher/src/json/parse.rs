// json_parse.rs — Parser implementation (functional split from json.rs).

use crate::json::value::Value;

pub struct Parser<'a> {
    pub bytes: &'a [u8],
    pub pos: usize,
}

impl<'a> Parser<'a> {
    pub fn skip_ws(&mut self) {
        while self.pos < self.bytes.len() {
            match self.bytes[self.pos] {
                b' ' | b'\t' | b'\n' | b'\r' => self.pos += 1,
                _ => break,
            }
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    pub fn eat(&mut self, c: u8) -> Result<(), String> {
        match self.peek() {
            Some(x) if x == c => {
                self.pos += 1;
                Ok(())
            }
            Some(x) => Err(format!("expected '{}', got '{}'", c as char, x as char)),
            None => Err(format!("expected '{}', got EOF", c as char)),
        }
    }

    pub fn parse_value(&mut self) -> Result<Value, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'{') => self.parse_obj(),
            Some(b'[') => self.parse_arr(),
            Some(b'"') => Ok(Value::Str(self.parse_str()?)),
            Some(b't') => {
                self.expect(b"true")?;
                Ok(Value::Bool(true))
            }
            Some(b'f') => {
                self.expect(b"false")?;
                Ok(Value::Bool(false))
            }
            Some(b'n') => {
                self.expect(b"null")?;
                Ok(Value::Null)
            }
            Some(c) if (c as char).is_ascii_digit() || c == b'-' => self.parse_number(),
            Some(c) => Err(format!("unexpected '{}'", c as char)),
            None => Err("unexpected EOF".into()),
        }
    }

    fn expect(&mut self, kw: &[u8]) -> Result<(), String> {
        for &b in kw {
            self.eat(b)?;
        }
        Ok(())
    }

    fn parse_str(&mut self) -> Result<String, String> {
        self.eat(b'"')?;
        let mut out = String::new();
        loop {
            match self.peek() {
                Some(b'"') => {
                    self.pos += 1;
                    return Ok(out);
                }
                Some(b'\\') => {
                    self.pos += 1;
                    match self.peek() {
                        Some(b'"') => {
                            out.push('"');
                            self.pos += 1;
                        }
                        Some(b'\\') => {
                            out.push('\\');
                            self.pos += 1;
                        }
                        Some(b'n') => {
                            out.push('\n');
                            self.pos += 1;
                        }
                        Some(b'r') => {
                            out.push('\r');
                            self.pos += 1;
                        }
                        Some(b't') => {
                            out.push('\t');
                            self.pos += 1;
                        }
                        Some(b'u') => {
                            self.pos += 1;
                            let hex = self.take_while(4, |c| (c as char).is_ascii_hexdigit())?;
                            let code = u32::from_str_radix(&hex, 16)
                                .map_err(|e| format!("bad \\u escape: {e}"))?;
                            let c = char::from_u32(code)
                                .ok_or_else(|| format!("invalid code point {code}"))?;
                            out.push(c);
                        }
                        Some(c) => return Err(format!("bad escape '\\{}'", c as char)),
                        None => return Err("EOF in escape".into()),
                    }
                }
                Some(c) => {
                    out.push(c as char);
                    self.pos += 1;
                }
                None => return Err("EOF in string".into()),
            }
        }
    }

    fn take_while(&mut self, n: usize, f: fn(u8) -> bool) -> Result<String, String> {
        let mut s = String::new();
        for _ in 0..n {
            match self.peek() {
                Some(c) if f(c) => {
                    s.push(c as char);
                    self.pos += 1;
                }
                Some(c) => return Err(format!("expected hex digit, got '{}'", c as char)),
                None => return Err("EOF in escape digits".into()),
            }
        }
        Ok(s)
    }

    fn parse_number(&mut self) -> Result<Value, String> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        while let Some(c) = self.peek() {
            if (c as char).is_ascii_digit() {
                self.pos += 1;
            } else {
                break;
            }
        }
        let mut is_float = false;
        if self.peek() == Some(b'.') {
            is_float = true;
            self.pos += 1;
            while let Some(c) = self.peek() {
                if (c as char).is_ascii_digit() {
                    self.pos += 1;
                } else {
                    break;
                }
            }
        }
        if matches!(self.peek(), Some(b'e') | Some(b'E')) {
            is_float = true;
            self.pos += 1;
            if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                self.pos += 1;
            }
            while let Some(c) = self.peek() {
                if (c as char).is_ascii_digit() {
                    self.pos += 1;
                } else {
                    break;
                }
            }
        }
        let s = std::str::from_utf8(&self.bytes[start..self.pos])
            .map_err(|e| format!("bad utf-8 in number: {e}"))?;
        if is_float {
            let x: f64 = s.parse().map_err(|e| format!("bad float '{s}': {e}"))?;
            Ok(Value::Float(x))
        } else {
            let n: i64 = s.parse().map_err(|e| format!("bad int '{s}': {e}"))?;
            Ok(Value::Int(n))
        }
    }

    fn parse_arr(&mut self) -> Result<Value, String> {
        self.eat(b'[')?;
        let mut out = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(Value::Arr(out));
        }
        loop {
            self.skip_ws();
            out.push(self.parse_value()?);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b']') => {
                    self.pos += 1;
                    return Ok(Value::Arr(out));
                }
                Some(c) => return Err(format!("expected ',' or ']', got '{}'", c as char)),
                None => return Err("EOF in array".into()),
            }
        }
    }

    fn parse_obj(&mut self) -> Result<Value, String> {
        self.eat(b'{')?;
        let mut out = std::collections::BTreeMap::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(Value::Obj(out));
        }
        loop {
            self.skip_ws();
            let k = self.parse_str()?;
            self.skip_ws();
            self.eat(b':')?;
            self.skip_ws();
            let v = self.parse_value()?;
            out.insert(k, v);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(Value::Obj(out));
                }
                Some(c) => return Err(format!("expected ',' or '}}', got '{}'", c as char)),
                None => return Err("EOF in object".into()),
            }
        }
    }
}
