# Shared package interface

Each thirdparty exposes `build.sh --metadata`, returning JSON with `version`
and `platforms` (for example `rocky9-x86_64`, `rocky9-aarch64`). Discovery calls
only this interface; dependency-specific pins and logic stay in its directory.

CI calls `<name>/build.sh --output DIR --cache-dir DIR` on the native architecture
runner, with `PACKAGE_PLATFORM` selecting the declared distribution/architecture.
The entrypoint must build in its pinned environment, test and emit exactly the
matching `<name>-<version>-<os>-<arch>.tar.gz` and `.sha256` files. The cache is
optional and must affect speed only, never correctness. A new package that needs
a different runner type must extend the generic platform mapping.

PR/branch builds validate packages without publishing. Only a tag matching the
package version on a commit reachable from `main` can publish a release. All
native builds and tests must succeed first. Release creation intentionally fails
if that release already exists; it never replaces published assets.
