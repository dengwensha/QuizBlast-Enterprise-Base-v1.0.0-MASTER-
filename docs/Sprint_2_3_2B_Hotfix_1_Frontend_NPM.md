# Sprint 2.3.2B Hotfix-1 — Frontend npm install Fix

## Problem
Docker build failed at frontend stage:

`target frontend: failed to solve: process "/bin/sh -c npm install" did not complete successfully: exit code: 1`

## Root Cause
The generated `package-lock.json` contained internal package registry URLs from the build environment. On local Docker builds, npm could not resolve those internal URLs.

## Fix
- Replaced internal registry URLs in `frontend/package-lock.json` with `https://registry.npmjs.org/`.
- Added `frontend/.npmrc` to explicitly use public npm registry.
- Updated frontend Dockerfile from `npm install` to deterministic `npm ci --no-audit --no-fund`.
- Added `frontend/.dockerignore` to prevent `node_modules`, `dist`, and temporary build files entering Docker context.

## Validation
- `npm ci --prefer-offline --no-audit --no-fund` passed.
- `npm run build` passed.
