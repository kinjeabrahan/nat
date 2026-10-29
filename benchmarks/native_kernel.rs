fn main() {
    let n:i64=std::env::args().nth(1).unwrap().parse().unwrap();
    let mut i=0i64; let mut x=1i64;
    while i<n {
        x=x.checked_mul(17).unwrap().checked_add(i).unwrap()%1000003;
        i=i.checked_add(1).unwrap();
    }
    println!("{}",x);
}
