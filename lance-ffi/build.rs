// Copyright 2021-present StarRocks, Inc. Licensed under the Apache License, Version 2.0.
fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("linux") {
        // Hide native and Rust dependency symbols, including crc-fast's C API,
        // while keeping this crate's five FFI entrypoints visible.
        println!("cargo:rustc-cdylib-link-arg=-Wl,--exclude-libs,ALL");
    }
}
