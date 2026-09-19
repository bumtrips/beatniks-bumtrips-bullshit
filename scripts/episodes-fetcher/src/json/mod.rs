// json/mod.rs — public JSON entry point.
//
// Minimal JSON parser + writer. Stdlib only. Scope: objects, arrays,
// strings, integers, true/false/null. No floats, no streaming.
//
// Functionally split:
//   json/value.rs  — Value enum + Display + string quoting
//   json/parse.rs  — recursive-descent Parser
//   json/mod.rs    — public `parse(input) -> Value` and `Value::to_string()`

pub mod parse;
pub mod value;

pub use value::Value;

use parse::Parser;

pub fn parse(input: &str) -> Result<Value, String> {
    let mut p = Parser {
        bytes: input.as_bytes(),
        pos: 0,
    };
    p.skip_ws();
    let v = p.parse_value()?;
    p.skip_ws();
    if p.pos != p.bytes.len() {
        return Err(format!("trailing input at byte {}", p.pos));
    }
    Ok(v)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_object() {
        let s = r#"{"a":1,"b":"x\ny","c":true,"d":null,"e":[1,2]}"#;
        let v = parse(s).unwrap();
        assert_eq!(v.to_string(), s);
    }
}
