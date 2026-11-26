# AGENTS.md

Rules for coding agents and contributors working in this repository.
[README.md](README.md) explains what the repository is and how StarRocks
consumes it. This file holds the rules and checklists.

The repository is new. If a shared script, check, or workflow described here
does not exist yet, create it in the location this file names. Do not inline
it into a thirdparty directory.

## Purpose

- This repository hosts the thirdparties that StarRocks consumes as
  prebuilt binaries: their source or patches, build scripts, and build
  tooling.
- Prebuilt binaries come only from release tags. CI builds them from the
  tagged commit and attaches them to the GitHub Release for that tag.
- StarRocks never builds these thirdparties. It downloads the release assets
  and pins each one by URL and checksum.

## Layout rules

1. Each thirdparty gets its own top-level directory. The directory name uses
   lowercase letters, digits, and `-`, for example `lance-ffi`. That name is
   the `<name>` in release tags and asset names.
2. Everything specific to a thirdparty stays inside its directory: scripts,
   source, patches, env files, Dockerfiles, toolchain pins, lockfiles, tests,
   and CI helper scripts.
3. The top level holds only common code:
   - `scripts/`: helper scripts shared by more than one thirdparty.
   - `checks/`: repo-wide checks, such as lint and layout validation.
   - `.github/`: CI workflows.

   These names are reserved. Any other top-level directory is a thirdparty.
4. Isolation runs both ways:
   - A thirdparty directory never reads, sources, or runs files from another
     thirdparty directory.
   - Common code in `scripts/`, `checks/`, and `.github/` contains no logic
     for one specific thirdparty. Workflows call `<name>/build.sh`. If only
     one thirdparty needs a step, the step goes in that thirdparty's
     directory.
5. Never commit build outputs, downloaded source archives, or release assets.

## Required contents of a thirdparty directory

- `README.md` covers:
  - what the thirdparty is and why StarRocks needs it
  - where the source comes from: for fetched source, the upstream
    repository and the exact ref (tag or commit); for source kept in the
    directory, the repository and commit it was imported from
  - where the version is declared
  - the license
  - supported platforms, as `<os>-<arch>`, with the glibc floor of each.
    If it skips an architecture, does not build on centos7, or ships
    per-distribution packages, say why.
  - the top-level directory inside the release archive
  - for shared libraries, any `NEEDED` entry beyond the allowed system
    libraries, and why it is needed
  - anything StarRocks needs in order to consume it, such as ABI notes
- `build.sh` is the single entry point. It builds and packages the release
  assets for one platform. It may hand off to any tool, such as CMake, Cargo,
  a Python driver, or `docker build`. It must:
  - run without prompts
  - stop with a non-zero exit code on the first failure
  - work from any current directory
- The version is declared in exactly one place inside the directory, for
  example in an env file or `Cargo.toml`. The release tag must match it.
- The upstream LICENSE and NOTICE files are included in every release archive.

## Platform rules

- Ship both x86_64 (amd64) and aarch64 (arm64). Skip one only when
  StarRocks uses the thirdparty on the other architecture alone, and say so
  in its `README.md`.
- Every thirdparty must provide binaries for Rocky Linux 9 and Ubuntu
  24.04. StarRocks 4.2 and later must support both.
- A lower glibc is more portable. glibc versions, lowest first:
  `centos7` 2.17, `rocky9` 2.34, `ubuntu22` 2.35, `ubuntu24` 2.39.
- Preferred: one portable binary per architecture that runs on both Rocky
  Linux 9 and Ubuntu 24.04. Build it on `centos7`. If that does not work,
  build it on `rocky9`. Never build a portable binary on Ubuntu: it would
  need glibc 2.35 or later and would not run on Rocky Linux 9.
- Fallback: if a single binary cannot run on both, build each separately:
  a `rocky9` package and a `ubuntu24` package for every architecture.
  Record the reason in the thirdparty's `README.md`.

## Build rules

- Pin every input:
  - source fetched from upstream to an exact tag or commit, never a branch
    or "latest"
  - build images by tag, preferably also by digest
  - language toolchains to an exact version
  - dependency lockfiles, such as `Cargo.lock`, committed and used in
    locked mode
- Verify the checksum of every downloaded input before using it. Use
  SHA-256 for checksums: for downloaded inputs, for published assets, and
  for what StarRocks pins.
- Build inside the thirdparty's declared build environment. Do not rely on
  packages installed on the host or CI runner.
- For C and C++ ABI compatibility, the StarRocks toolchain images
  (`starrocks/toolchains-*`, defined under `docker/dockerfiles/toolchains/`
  in the StarRocks repo) are a good base for the build environment.
- Compile C and C++ code with `-fno-omit-frame-pointer`. StarRocks requires
  this of its thirdparties so that profiling works.
- Build static libraries (`.a`) as position-independent code: `-fPIC` for C
  and C++, or `CMAKE_POSITION_INDEPENDENT_CODE=ON` in CMake. This lets
  StarRocks link them into shared libraries and PIE executables.
- Keep the shared libraries (`.so`) that a shared library depends on to a
  minimum, so StarRocks can ship it without extra runtime libraries:
  - Link other dependencies statically into the shared library.
  - Link the C++ runtime statically (for GCC, `-static-libstdc++`).
  - Depend only on system libraries present on every supported
    distribution: glibc (`libc`, `libm`, `libpthread`, `libdl`, `librt`)
    and `libgcc_s`. List any other `NEEDED` entry (from `readelf -d`) and
    its reason in the thirdparty's `README.md`.
  - Export only the public API, and hide the symbols of bundled
    dependencies (`-fvisibility=hidden` or a linker version script). Then
    they cannot clash with StarRocks' own copies of the same libraries.
  - Do not embed an RPATH or RUNPATH that points at a build directory.
- If the thirdparty has tests, run them as part of the build. A failing test
  fails the build.

## Release rules

- Release tag format: `<name>-<version>`, for example `lance-ffi-0.1.0`.
  - One tag releases exactly one thirdparty.
  - Tag a commit that is on `main`.
  - `<version>` must equal the version declared in the thirdparty directory,
    and it starts with a digit. If more than one directory name matches the
    start of a tag, the longest one is the `<name>`.
- Release assets, one pair per supported platform:
  - `<name>-<version>-<os>-<arch>.tar.gz`
  - `<name>-<version>-<os>-<arch>.tar.gz.sha256`
- `<os>` is the distribution the asset was built on, including its major
  release: `centos7` or `rocky9` for a portable build, or `rocky9` and
  `ubuntu24` for per-distribution builds.
- `<arch>` is the `uname -m` value: `x86_64` or `aarch64`.
- Each archive unpacks into a single top-level directory.
- Release assets are built by CI from the tag. Never upload a binary that
  was built by hand.
- Tags and assets are immutable. Never delete, move, or re-push a release
  tag, and never replace the assets of a published release. To fix a
  release, publish a new version.
- Any change under `<name>/` that changes the produced binaries needs a new
  version. Documentation-only changes do not.

## Checklists

### Add a thirdparty

1. Pick a directory name that follows the layout rules and is not reserved.
2. Create the directory with the required contents. Put its sources,
   patches, env files, and build tooling inside it.
3. Pin the upstream ref, toolchains, and build images. Commit any lockfiles.
4. Pick the build distribution and architectures by the platform rules.
5. Run `build.sh` for at least one platform. Check that the archive name,
   its top-level directory, and the license files are correct. Check that
   static libraries are built with `-fPIC`, and check the `NEEDED` entries
   of shared libraries with `readelf -d`.
6. Check that the binaries load and run on Rocky Linux 9 and Ubuntu 24.04.
7. Add or update its row in the Thirdparties table in the top-level
   `README.md`.
8. Limit the change to the new directory, the README row, and any truly
   common code.

When importing from an existing repository, such as `lance-ffi` from
`beinan/starrocks-lance-ffi`:

- Record the source repository URL and the imported commit in the
  thirdparty's `README.md`, and keep the upstream attribution.
- Keep its build logic (scripts, Dockerfiles, lockfiles) inside the
  thirdparty directory.
- Replace its standalone tag scheme and release workflow with this
  repository's. For example, `v0.1.0` becomes `lance-ffi-0.1.0`, and asset
  names follow `<name>-<version>-<os>-<arch>.tar.gz`.
- Check its platform set against the platform rules. Drop builds the rules
  do not need.

### Bump a thirdparty version

1. Update the source (or the upstream ref and checksum), patches, or build
   settings.
2. Update the single version declaration and the thirdparty's `README.md`.
3. Run `build.sh` and the thirdparty's tests.
4. Merge to `main`, then push the tag `<name>-<new-version>` on the merge
   commit.
5. After the release is published, update the URL and SHA-256 in the
   StarRocks `thirdparty/vars*.sh` files. That is a separate change in the
   StarRocks repository.

### Change common code

1. Confirm the change belongs at the top level: more than one thirdparty
   uses it, or it applies to the whole repository.
2. Keep it free of branches for specific thirdparties.
3. Check that every thirdparty that uses the changed code still builds.
4. If the change alters the binaries of a thirdparty, bump that
   thirdparty's version before its next release.

## Do not

- Do not put thirdparty-specific files at the top level.
- Do not reference one thirdparty directory from another.
- Do not commit binaries, source archives, or build outputs.
- Do not track a moving upstream branch.
- Do not re-tag, delete, or overwrite a published release.
