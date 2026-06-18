# AGENTS.md

## Coding Standards

- Use `pathlib.Path` for filesystem paths.
- Keep modules small, readable, and focused on one concern.
- Prefer explicit error messages over silent fallback behavior.
- Use pandas for tabular data loading and QA checks.
- Add tests for loader and QA behavior when introducing new checks.

## Path Conventions

- Raw source files live under `data/raw/`.
- Intermediate files belong in `data/interim/`.
- Final transformed datasets belong in `data/processed/`.
- Generated reports, extracts, and artifacts belong in `outputs/`.

## Testing Commands

```bash
python3 -m src.data_checks
pytest
```

## Data Handling Rules

- No real family office data should be added to this repository.
- All family office data in this project is synthetic.
- Raw data under `data/raw/` should not be modified directly.
- Write derived datasets to `data/processed/` or `data/interim/`.
- Write generated outputs to `outputs/`.

## Future Modules

- `src/extraction/`
- `src/validation/`
- `src/portfolio_updates/`
- `src/dashboard/`
- `src/risk/`
