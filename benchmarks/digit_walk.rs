fn step(mapping: &[u8], value: u8) -> u8 {
    let text = [value];
    let index: usize = std::str::from_utf8(&text).unwrap().parse().unwrap();
    mapping[index]
}

fn main() {
    let mut state = b'0';
    let mut a = b'0';
    while a != b'9' {
        let mut b = b'0';
        while b != b'9' {
            let mut c = b'0';
            while c != b'9' {
                let mut d = b'0';
                while d != b'9' {
                    state = step(b"1234567890", state);
                    d = step(b"1234567899", d);
                }
                c = step(b"1234567899", c);
            }
            b = step(b"1234567899", b);
        }
        a = step(b"1234567899", a);
    }
    println!("{}", state as char);
}
