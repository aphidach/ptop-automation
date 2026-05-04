# Release and Packaging

Current release version: `0.3.2`.

This project publishes deployable Docker images to GitHub Container Registry when a semantic version tag is pushed.

## Version Sources

- Python package metadata: `pyproject.toml`
- Runtime version constant: `app/version.py`
- Docker image label/build arg: `APP_VERSION`
- Default Makefile version: `VERSION ?= 0.3.2`

Keep these values aligned when cutting a new release.

## Release v0.3.2

Run checks and build the deployable package locally:

```bash
rtk make test
rtk make docker-build VERSION=0.3.2
```

Create and push the release tag:

```bash
rtk git status
rtk make release-tag VERSION=0.3.2
rtk git push origin v0.3.2
```

Commit the release changes before creating the tag. The `release-tag` target fails if the worktree has uncommitted changes, so `v0.3.2` points to the exact release commit.

Pushing `v0.3.2` starts the release workflow. It creates a GitHub Release and publishes:

```text
ghcr.io/<owner>/<repo>:0.3.2
ghcr.io/<owner>/<repo>:latest
```

## Manual Package Build

Build both the Python wheel and Docker image locally:

```bash
rtk make package VERSION=0.3.2
```

Run the Docker image locally:

```bash
rtk make docker-run VERSION=0.3.2
rtk curl http://localhost:8000/health
```

## Deployment

Pull and run the released image on a server:

```bash
rtk docker pull ghcr.io/<owner>/<repo>:0.3.2
rtk docker run -d \
  --name solar-meter-bot \
  --restart unless-stopped \
  --env-file .env \
  -p 8000:8000 \
  -v /absolute/path/to/credentials:/app/credentials:ro \
  -v /absolute/path/to/reports:/app/reports \
  ghcr.io/<owner>/<repo>:0.3.2
```

Required deployment checks:

```bash
rtk curl https://your-domain.example.com/health
```

Then set the LINE webhook URL to:

```text
https://your-domain.example.com/webhook/line
```

If report images must be visible outside the container, prefer `REPORT_IMAGE_STORAGE=r2` with a public `R2_PUBLIC_URL`. Local report storage only works when `APP_BASE_URL` can serve `/reports` publicly.

## Next Release

For the next version, update `pyproject.toml`, `app/version.py`, and `Makefile`, then tag:

```bash
rtk make test
rtk make docker-build VERSION=0.3.3
rtk make release-tag VERSION=0.3.3
rtk git push origin v0.3.3
```
