# CHANGELOG

## QuizBlast Enterprise Base v1.0.0 MASTER

### Added
- Official MASTER baseline structure.
- VERSION file.
- Release notes and stabilization report.
- QES task numbering standard document.

### Stabilized
- Backend Python compile verified.
- Frontend npm build verified.
- Manual backend golden tests verified after schema adjustment.
- QBDS DTO relaxed so Validation Engine can own row-level validation errors.
- Database session helper now rolls back on exceptions.
- Removed generated cache/build artifacts from release package.

### Known Limitations
- Frontend is still largely inside `App.jsx`; Sprint 2.3.3 / QB-233-T001 will split this into component/page structure.
- Browser `alert()`/`confirm()` still exists; Sprint 2.3.3 will replace these with `QBModal`.
- Import History endpoint exists, but a dedicated UI screen is planned for Sprint 2.3.3.
