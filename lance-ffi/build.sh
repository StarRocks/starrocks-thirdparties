#!/usr/bin/env bash
# Copyright 2021-present StarRocks, Inc. Licensed under the Apache License, Version 2.0.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
version=$(python3 -c 'import pathlib,re,sys; print(re.search(r"^version = \"([^\"]+)\"$", pathlib.Path(sys.argv[1]).read_text(), re.M).group(1))' "$source_dir/Cargo.toml")
if [[ ${1:-} == --metadata ]]; then
    printf '{"version":"%s","platforms":["rocky9-x86_64","rocky9-aarch64"]}\n' "$version"
    exit 0
fi
output="$source_dir/dist"
cache_dir=""
while (( $# )); do
    case "$1" in
        --output) output=$2; shift 2 ;;
        --cache-dir) cache_dir=$2; shift 2 ;;
        *) echo "Usage: $0 [--metadata | --output DIR [--cache-dir DIR]]" >&2; exit 2 ;;
    esac
done
arch=$(uname -m)
[[ $(uname -s) == Linux && ( $arch == x86_64 || $arch == aarch64 ) ]] || {
    echo 'Build natively on Linux x86_64 or aarch64' >&2; exit 1;
}
mkdir -p "$output"
output=$(cd "$output" && pwd)
stage=$(mktemp -d "$output/.package-XXXXXX")
trap 'rm -rf "$stage"' EXIT
cache_args=()
if [[ -n "$cache_dir" ]]; then
    [[ ! -f "$cache_dir/index.json" ]] || cache_args+=(--cache-from "type=local,src=$cache_dir")
    cache_args+=(--cache-to "type=local,dest=$cache_dir-new,mode=max")
fi
docker buildx build --progress plain --target package --output "type=local,dest=$stage" \
    "${cache_args[@]}" "$source_dir"
# Compile the C++ ABI consumer and read the SAME portable package on both required systems.
# Runtime dependencies and tools come from pinned images, never from the runner.
for runtime_image in \
    starrocks/toolchains-rocky9:main-20261029@sha256:2b420af3b29c85468b620c0d9e8c5b462aa1e2397eb653df8c701bdc87bfea7f \
    starrocks/toolchains-ubuntu:main-20261029@sha256:b7faa2771e4d98bce73e1bd31cf9269c64ef63500cbaefb35ffffa4b605eb8c8; do
    docker run --rm --network none -v "$stage/lance:/opt/lance:ro" \
        -v "$source_dir/package_test.cpp:/test.cpp:ro" "$runtime_image" bash -ec '
        export PATH="${STARROCKS_GCC_HOME}/bin:$PATH"
        g++ -std=c++17 -fno-omit-frame-pointer -static-libstdc++ /test.cpp \
            -I/opt/lance/include -L/opt/lance/lib -lstarrocks_lance -Wl,-rpath,/opt/lance/lib -o /tmp/lance-test
        /tmp/lance-test /opt/lance/share/lance/testdata/rows.lance'
done
archive="lance-ffi-$version-rocky9-$arch.tar.gz"
tar -czf "$output/$archive" -C "$stage" lance
(cd "$output" && sha256sum "$archive" > "$archive.sha256")
if [[ -n "$cache_dir" ]]; then
    rm -rf "$cache_dir"
    mv "$cache_dir-new" "$cache_dir"
fi
