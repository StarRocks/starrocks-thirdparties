# starrocks-thirdparties

This repository hosts the thirdparty libraries and tools used by
[StarRocks](https://github.com/StarRocks/starrocks): their source or patches,
build scripts, and build tooling. StarRocks does not build these from
source. It downloads the prebuilt binaries that this repository publishes.

## How it works

1. Each thirdparty lives in its own top-level directory. Everything specific
   to it lives in that directory: build scripts, source or patches,
   environment settings, and build tooling such as Dockerfiles or language
   toolchains.
2. The top level holds only common scripts and checks shared by all
   thirdparties.
3. A thirdparty is released by pushing a release tag that names the
   thirdparty and its version. Prebuilt binaries come only from release tags.
4. The binaries for each tag are attached to the GitHub Release for that tag.
5. StarRocks pins each prebuilt binary by download URL and checksum in its
   `thirdparty/vars*.sh` files.

## Repository layout

This is the target layout. The repository is new, so the common directories
and the release workflow are added as they are needed.

```
starrocks-thirdparties/
+-- README.md
+-- AGENTS.md          rules for contributors and coding agents
+-- LICENSE
+-- scripts/           common helper scripts shared by all thirdparties
+-- checks/            repo-wide checks (lint, layout validation)
+-- .github/           CI workflows
+-- <name>/            one directory per thirdparty, for example lance-ffi/
    +-- README.md      what it is, upstream, version, license, platforms
    +-- build.sh       entry point that builds and packages the binaries
    +-- ...            source, patches, env files, Dockerfiles, other tooling
```

`scripts`, `checks`, and `.github` are reserved names. Any other top-level
directory is a thirdparty.

`build.sh` is the only fixed entry point. Behind it, each thirdparty uses
whatever build tools it needs, for example CMake, Cargo, a Python driver, or
a Dockerfile.

## Thirdparties

| Directory   | Status                  | Description                                                    | Upstream |
|-------------|-------------------------|----------------------------------------------------------------|----------|
| `lance-ffi` | Planned, not yet added  | Lance Rust SDK wrapper with a C ABI for the StarRocks Lance connector | [beinan/starrocks-lance-ffi](https://github.com/beinan/starrocks-lance-ffi) |

## Platform policy

Requirements:

- **CPU architectures.** Every thirdparty ships for both x86_64 (amd64) and
  aarch64 (arm64). The only exception is a thirdparty that StarRocks uses on
  one CPU architecture only. Its README says so.
- **Target systems.** StarRocks 4.2 and later must support Rocky Linux 9
  and Ubuntu 24.04. Every thirdparty must provide binaries for both.

A binary built against an older glibc also runs on distributions with a
newer glibc, so a lower glibc is more portable. glibc versions, lowest
first:

| Distribution  | `<os>`     | glibc |
|---------------|------------|-------|
| CentOS 7      | `centos7`  | 2.17  |
| Rocky Linux 9 | `rocky9`   | 2.34  |
| Ubuntu 22.04  | `ubuntu22` | 2.35  |
| Ubuntu 24.04  | `ubuntu24` | 2.39  |

How to build:

1. **Preferred: one portable binary per architecture.** It runs on both
   Rocky Linux 9 and Ubuntu 24.04. Build it on `centos7`. If that does not
   work, build it on `rocky9`. Never build a portable binary on Ubuntu: it
   would need glibc 2.35 or later and would not run on Rocky Linux 9.
2. **Fallback: one binary per distribution.** If a single binary cannot run
   on both Rocky Linux 9 and Ubuntu 24.04, build each separately: a
   `rocky9` package and a `ubuntu24` package for every architecture. The
   thirdparty's README records why.

## Linking policy

- Static libraries are built as position-independent code (`-fPIC`), so
  StarRocks can link them into shared libraries and PIE executables.
- Shared libraries depend on as few other shared libraries as possible.
  Other dependencies, including the C++ runtime, are linked in statically.
  The only shared dependencies are system libraries present on every
  supported distribution: glibc and `libgcc_s`. This way StarRocks can ship
  them without extra runtime libraries. Symbols of bundled dependencies are
  hidden, so they cannot clash with StarRocks' own copies of the same
  libraries.

See [AGENTS.md](AGENTS.md) for the full build rules.

## Releases

Release tags use the form:

```
<name>-<version>
```

`<name>` is the thirdparty's directory name, and `<version>` is the version
declared in that directory. `<version>` starts with a digit. If more than
one directory name matches the start of a tag, the longest one is the
`<name>`. Each tag releases exactly one thirdparty. For example,
`lance-ffi-0.1.0` releases version 0.1.0 of `lance-ffi/`.

Release assets are named:

```
<name>-<version>-<os>-<arch>.tar.gz
<name>-<version>-<os>-<arch>.tar.gz.sha256
```

- `<os>` is the distribution the asset was built on, including its major
  release. That is `centos7` or `rocky9` for a portable build, or `rocky9`
  and `ubuntu24` for per-distribution builds. See
  [Platform policy](#platform-policy).
- `<arch>` is the `uname -m` value: `x86_64` (amd64) or `aarch64` (arm64).

Release tags and their assets are immutable. StarRocks pins every asset by
URL and checksum, so a published release is never re-tagged or re-uploaded.
To ship a fix, bump the version and push a new tag.

## Using a release from StarRocks

StarRocks declares each prebuilt thirdparty in its `thirdparty/vars*.sh`
files as a group of variables: `<NAME>_DOWNLOAD`, `<NAME>_NAME`,
`<NAME>_SOURCE`, and a checksum. Architecture-specific entries go in
`vars-x86_64.sh` and `vars-aarch64.sh`. Distribution-specific overrides go
in files such as `vars-ubuntu22-<arch>.sh`. Point `<NAME>_DOWNLOAD` at the
release asset:

```
https://github.com/StarRocks/starrocks-thirdparties/releases/download/<name>-<version>/<name>-<version>-<os>-<arch>.tar.gz
```

Pin the SHA-256 published in the asset's `.sha256` file. StarRocks is moving
its checksums from MD5 to SHA-256. Branches that still verify only
`<NAME>_MD5SUM` need the asset's MD5, computed after the SHA-256 check
passes.

## Contributing

Read [AGENTS.md](AGENTS.md) before adding a thirdparty, bumping a version,
or changing common code. It holds the rules and checklists that human
contributors and coding agents both follow.

## License

The build scripts in this repository are licensed under the Apache License
2.0. See [LICENSE](LICENSE). Each thirdparty keeps its own upstream license,
and its prebuilt binaries ship with that license.
