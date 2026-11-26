# Lance FFI

Rust SDK wrapper with a C ABI for the StarRocks Lance connector. Arrow C Data
Interface batches let StarRocks read Lance datasets without embedding a JVM or
compiling Rust inside its own build.

Imported from https://github.com/beinan/starrocks-lance-ffi at commit
`f735a1904903ffdf1ce3dd197903d024ca40578a`. The implementation originally came
from StarRocks/starrocks#80977 at `2aeed88165dc13a8b0fbbf1b2e75d7c0545bfa60`.
The wrapper and Lance SDK are Apache-2.0 licensed. `LICENSE.txt` covers the
wrapper; `licenses/` retains Lance v12.0.0's LICENSE and upstream generated
third-party license inventory (upstream has no NOTICE file at this tag).
All are included under `share/lance/` in every archive.

## Build and release

Run `./lance-ffi/build.sh --output /absolute/output/path` from any directory.
Docker with Buildx and Python 3 are the only host prerequisites. The entrypoint
builds, runs the Rust regressions and packaging tests, checks ELF compatibility,
and reads a real dataset through a C++ consumer on Rocky9 and Ubuntu24 images.
A failed test prevents packaging. Optional `--cache-dir DIR` reuses Docker layers;
a clean build follows exactly the same validation path.

`Cargo.toml` is the single wrapper version declaration. `Cargo.lock` pins the
Lance 12.0.0 / Arrow 58.3.0 dependency graph and is always consumed with `--locked`.
The Rust 1.96.1 toolchain and StarRocks build/runtime images are digest-pinned in
`Dockerfile` / `build.sh`; protoc is checksum-pinned in `ci-protoc.py`.
The new patch version hides bundled dependency symbols and adds PIC flags to
native dependencies; the five-function C ABI is unchanged.

Both `rocky9-x86_64` and `rocky9-aarch64` packages require glibc **2.34** and run
on Rocky Linux 9 and Ubuntu 24.04 (also Ubuntu 22.04). We build once per native
architecture on Rocky9 and test those identical bytes on both required systems.
CentOS7 is unsupported because the selected Rust/StarRocks toolchains require a
newer glibc. There is no separate Ubuntu package with a higher glibc requirement.
The ELF check rejects any GLIBC requirement above 2.34, any RPATH/RUNPATH, and
any unexpected exported symbol. Only the system `libc`, `libm`, `libgcc_s` and
platform ELF loader are needed; no extra C++/SSL/shared Arrow runtime is required.
Native code uses frame pointers and PIC. Dependency archive symbols are hidden.

After merging, maintainers push `lance-ffi-<version>` on a commit reachable from
`main`. CI builds and tests that tag, then publishes:

- `lance-ffi-<version>-rocky9-x86_64.tar.gz` and `.sha256`
- `lance-ffi-<version>-rocky9-aarch64.tar.gz` and `.sha256`

Each archive has one root directory, `lance/`, with `lib/libstarrocks_lance.so`,
`include/lance_rs_ffi.h`, relocatable `lib/cmake/StarRocksLance/` configs, a
source/toolchain/hash manifest and a small integration-test dataset. StarRocks
pins release URLs and SHA-256 values only after the release exists. The CMake
package exposes the `lance_rust` target and `StarRocksLance_TEST_DATASET` fixture.
PR builds upload validation artifacts but never publish releases. Existing
referenced releases are immutable; never replace the earlier staging artifacts.

## Ownership and query semantics

- C strings and property arrays are borrowed only during `sr_lance_reader_open`.
- The caller owns a successful reader handle; calls on one handle cannot overlap.
- Each successful `sr_lance_reader_next` transfers Arrow release callbacks to C++.
  Imported buffers can outlive the reader. EOF, pending and errors transfer no buffers.
- The cancellation callback is borrowed during open and called on the calling
  thread. Next polls return within 100 ms while I/O is pending so C++ can check
  query cancellation. Open polls the same cancellation callback every 100 ms
  while pending and respects the BE query timeout through that callback.
- Rust unwinds are caught at fallible FFI boundaries. SDK error strings are not
  returned because they may contain credentials or signed URLs.
- Sessions and credential-bearing object stores are private to each reader.
  Only the bounded Tokio runtime is shared. Readahead is limited to one batch and
  one fragment. Rust uses a private allocator to avoid BE thread-local allocator
  accounting across Tokio workers. Exported Arrow buffers are charged to the BE
  instance memory tracker until released. SDK-internal caches and temporary I/O
  allocations remain outside the query tracker; this is not a hard memory limit.
- The dataset version is resolved once at open (or selected through the ABI's
  explicit version argument) and retained for the entire stream. Callers must pass the version captured with the schema to pin all scans
  of a dataset within a query. All fragments are read. Fragment scheduling and ANN are future work.
- Projection is pushed down. Predicates and LIMIT remain in StarRocks; pushing a
  limit ahead of residual filtering would change query results.

Rust tests create real multi-fragment datasets and exercise the public ABI,
snapshot stability, projection, nulls, buffer ownership, cancellation and errors.
The thirdparty builder also generates a local fixture used by
`connector_lance_test` to exercise Rust through C++ and StarRocks column conversion.

## Reference implementation and attribution

The FFI contract also references
[`lance-format/lance-c`](https://github.com/lance-format/lance-c/blob/2089f6ffc7a138f52ac90c0592fdd3e85727d57d/include/lance/lance.h):
opaque reader handles, Arrow C Data Interface outputs with caller-owned outer
structures and release callbacks, and explicit close/free functions. A reader
must be closed exactly once; exported batches can outlive it. Callbacks must
return normally without throwing across the C ABI.

This wrapper retains length-delimited inputs, per-call sanitized errors and
bounded polling for StarRocks cancellation instead of adopting lance-c's full
dataset/scanner API or thread-local error channel. Function names, return codes
and signatures are not ABI-compatible with lance-c. DataCache callbacks remain
a separate integration task.

The native reader framework and naming follow the
[`lance-cp-sr-lance-dev` branch](https://github.com/tianfy17/starrocks/tree/lance-cp-sr-lance-dev)
submitted by @tianfy17 in [StarRocks #77326](https://github.com/StarRocks/starrocks/pull/77326),
as discussed in [#79428](https://github.com/StarRocks/starrocks/issues/79428).
The reference was inspected at `2bf405c23e5ec717f93c7b5cc961b3f4083fe636`.
Credit goes to lixianhai for the original native reader implementation
([01616406f109](https://github.com/StarRocks/starrocks/commit/01616406f109029d5a1822f36ca1f7b848f363d1),
cherry-picked there from `2af107159dd`) and to @tianfy17 for the contributed
branch and integration work.

The matching concepts use `lance_rs_ffi.h`, `SrLanceReader`, `SrLanceString`,
`SrLanceStringPair`, `sr_lance_reader_open/next/close`, `open_reader`,
`string_from_raw`, `strings_from_raw`, `storage_options_from_raw`, and
`export_batch`. The C++ adapter follows the same reader stages: `_init_read_fields`,
`_open_reader`, `_next_batch`, `_append_batch_to_read_chunk`, and
`_batch_is_exhausted`, with `_reader`, `_field_names`, `_arrow_batch`, and
`_batch_start_idx` holding the corresponding state.

This remains a private ABI, not a drop-in binary replacement for that branch.
The open arguments retain version selection, StarRocks cloud properties and
cancellation; next also returns a pending status. The adapter stays inside
ConnectorLance rather than depending on HdfsScanner/ParquetScanner. It converts
each batch slice with strict query error handling and explicit memory accounting.
Shared credential-bearing sessions, ANN, fragment scheduling and limit pushdown
are not part of this series.
