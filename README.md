# AOS-CX Container Lab

**Release status: generic ARM64 OCI application only. Do not deploy the released OCI archive to an AOS-CX switch.**

This repository contains a small, non-networked health heartbeat and a GitHub Actions release workflow. The first release is intentionally not an AOS-CX `container.img`: HPE's public documentation does not define the downloadable image's on-disk format, the complete required in-image manifest, or the accepted image CPU architecture. Renaming a Docker or OCI archive to `.img` would not resolve those unknowns.

## HPE Format Blocker

The official [AOS-CX 10.18 Containers Guide for 6300F/M and other switch series](https://support.hpe.com/hpesc/public/docDisplay?docId=sd00007929en_us&page=index.html) documents container support and the management interface. In particular:

- `image-location` fetches the configured URL over HTTP; its example uses a filename ending in `.img`.
- Images with a valid HPE signature are accepted by default. `allow-unsigned` permits an unsigned image unless `secure-mode enhanced` is configured.
- The `container exec` description says an endpoint script is located through a manifest in the container image filesystem, but does not specify the full manifest filename/schema or how to package the image.
- The guide identifies the 6300F/M family, but does not state the image architecture/ABI the switch accepts.

Those statements do **not** establish that a Docker `save` archive, OCI archive, root filesystem, or any particular `.img` format is accepted by the switch. No switch-deployable image is built or released here. The release workflow enforces this distinction in the artifact name and release metadata.

Before a later release can be called deployable, obtain authoritative HPE confirmation of the exact 10.18.1010 package format, required manifest path and schema, architecture/ABI, maximum image size, and signature requirements for the exact 6300 SKU. Then validate an image on a lab switch before adding it to a Mist-managed site.

## Application

The process emits a JSON heartbeat to stdout every 30 seconds. Its one-shot `--check` mode is used by the OCI image's healthcheck. This reports only that the local process/runtime check ran; it does not inspect switch state or validate switch services.

The application has no listening socket, network client, switch-management API access, credentials, secrets, or application-defined environment variables. The upstream Python base image may carry standard non-secret runtime defaults; CI rejects secret-like environment variable names. The image runs as UID/GID `65532:65532`, declares no ports, and carries OCI title, description, version, source, and revision labels. The healthcheck is container metadata; HPE documentation does not establish that AOS-CX consumes Docker healthcheck metadata.

## Build And Release

Local application tests:

```powershell
python -m unittest discover -s tests -v
```

Building and running the generic ARM64 image requires Docker Desktop with Buildx and ARM64 emulation:

```powershell
$version = (Get-Content VERSION -Raw).Trim()
docker buildx build --platform linux/arm64 --load --build-arg "APP_VERSION=$version" -t aoscx-container-healthcheck:$version .
docker run --rm --platform linux/arm64 --network none --read-only --cap-drop ALL --security-opt no-new-privileges --memory 128m --cpus 0.1 aoscx-container-healthcheck:$version --check
```

The CI workflow runs the application tests, builds and runs the ARM64 image with no network, read-only root filesystem, dropped Linux capabilities, and bounded local test resources, validates the OCI archive structure/configuration, and generates SHA-256 checksums. The Python base image is pinned to its ARM64 digest and third-party GitHub Actions are pinned to commit SHAs.

To publish a release, update `VERSION`, commit the change, and push a matching tag such as `v0.1.0`. The workflow rejects a tag that does not match `VERSION`. GitHub Releases receive the generic `*.oci.tar`, its `*.sha256` file, and `release-metadata.json`. No switch image is produced. Check a downloaded archive with `sha256sum --check <archive>.sha256` on Linux/macOS, or `Get-FileHash <archive> -Algorithm SHA256` on Windows and compare the digest with the `.sha256` asset.

## Mist-Managed Deployment

**Deployment is blocked pending the HPE format confirmation above.** Do not point Mist at the released `.oci.tar`, rename it to `.img`, set `allow-unsigned` as a workaround for the format gap, or enable it on a switch. The following is the gated process for a future, HPE-validated image; nothing in CI connects to Mist or changes a switch.

1. Confirm HPE's format/schema/architecture and image-size requirements, the exact 6300 SKU, secure-mode policy, and whether the validated image is HPE-signed. Test on a lab switch running the target AOS-CX release first.
2. Host only the validated switch package on an approved HTTP server reachable in the chosen switch VRF. HPE's documented `image-location` command supports HTTP.
3. Before configuration, inspect `show capacities containers` and `show capacities-status containers`. Set low per-container CPU and memory restrictions based on the measured workload and the switch's remaining capacity. Do not assume the default limits are available when other containers are running.
4. In Mist, use **Site → Switch Configuration → Custom CLI commands** to make an explicitly reviewed, manual configuration change. Example shape only; replace the URL and do not apply until the blocker is cleared:

   ```text
   container cx_health
    image-location http://<approved-server>/<hpe-validated-image>.img vrf mgmt
    restrict cpu 1
    restrict memory 64
   ```

   Add `allow-unsigned` only if HPE confirms the package is unsigned, local policy permits it, and the switch is not in `secure-mode enhanced`. Enable the container only as a separate, manually approved step after reviewing the downloaded image and configuration. This repository does not enable it.
5. Verify the configured image and runtime from switch CLI:

   ```text
   show container cx_health
   show capacities-status containers
   show running-config container
   ```

   Require an `operational` container status and successful image/manifest status; consult the AOS-CX guide for the fields and release-specific output.

For rollback, first remove the custom CLI configuration from the Mist site/group and allow Mist to reconcile the switch. If local cleanup is still required, use the documented `no container cx_health` form from AOS-CX configuration context; it removes the container's existing configuration. Verify with `show container` and `show running-config container`. Image-cache cleanup is not documented here, so do not manually delete switch files. Retain the prior Mist configuration and known-good release until the rollback is verified.

## Resource Limits And Licensing

The AOS-CX 10.18 guide documents defaults of 10% CPU and 256 MB memory per container. It limits the configured total across all containers to at most 20% of device CPU capacity and 20% of device memory capacity. Changing limits on an enabled operational container can restart it. The example's 1% CPU and 64 MB memory are starting ceilings, not guarantees; check the switch's capacity/status output and account for all containers before using them.

The guide warns that container features require an **AOS-CX Advanced Software Feature Pack**. It also says AOS-CX does not enforce pack ownership before container use and that the warning appears during container creation. This does not establish entitlement for a particular customer, switch, or contract. Confirm licensing with HPE or the account team before production use; the absence of an enforcement error is not proof of a license.