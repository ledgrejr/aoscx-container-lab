import argparse
import hashlib
import json
import re
import tarfile


def read_member(archive, name):
    member = archive.extractfile(name)
    if member is None:
        raise ValueError(f"missing OCI archive member: {name}")
    return member.read()


def read_blob(archive, digest):
    match = re.fullmatch(r"sha256:([0-9a-f]{64})", digest)
    if match is None:
        raise ValueError(f"unsupported OCI digest: {digest}")
    data = read_member(archive, f"blobs/sha256/{match.group(1)}")
    if hashlib.sha256(data).hexdigest() != match.group(1):
        raise ValueError(f"OCI blob digest mismatch: {digest}")
    return data


def validate(path, expected_version):
    with tarfile.open(path, "r:*") as archive:
        if json.loads(read_member(archive, "oci-layout")) != {"imageLayoutVersion": "1.0.0"}:
            raise ValueError("unsupported OCI image layout")

        index = json.loads(read_member(archive, "index.json"))
        descriptors = [
            item for item in index.get("manifests", [])
            if item.get("platform", {}).get("os") == "linux"
            and item.get("platform", {}).get("architecture") == "arm64"
        ]
        if len(descriptors) != 1:
            raise ValueError("expected exactly one linux/arm64 image manifest")

        manifest = json.loads(read_blob(archive, descriptors[0]["digest"]))
        image_config = json.loads(read_blob(archive, manifest["config"]["digest"]))
        config = image_config.get("config", {})
        labels = config.get("Labels") or {}
        environment = config.get("Env") or []
        secret_name = re.compile(r"(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY|CREDENTIAL)", re.IGNORECASE)
        has_sensitive_environment = any(
            secret_name.search(item.partition("=")[0]) for item in environment
        )

        checks = {
            "version label": labels.get("org.opencontainers.image.version") == expected_version,
            "non-root user": config.get("User") == "65532:65532",
            "no exposed ports": not config.get("ExposedPorts"),
            "no sensitive environment variables": not has_sensitive_environment,
            "health check": bool(config.get("Healthcheck", {}).get("Test")),
            "expected entrypoint": config.get("Entrypoint") == ["python", "/app/healthcheck.py"],
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError("OCI config validation failed: " + ", ".join(failed))


def main():
    parser = argparse.ArgumentParser(description="Validate this project's generic OCI release archive.")
    parser.add_argument("archive")
    parser.add_argument("--version", required=True)
    options = parser.parse_args()
    validate(options.archive, options.version)
    print(f"Validated generic linux/arm64 OCI archive for version {options.version}; not an AOS-CX image.")


if __name__ == "__main__":
    main()