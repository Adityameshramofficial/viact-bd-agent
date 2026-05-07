# Tools

Python scripts for deterministic execution. Each script handles one job: API calls, data transformations, file operations, or database queries.

## Conventions
- Scripts read credentials from `../.env` via `python-dotenv`
- Output goes to `../.tmp/` for intermediate files, or directly to cloud services for final deliverables
- Each script should be runnable standalone: `python tools/script_name.py`

## Scripts
<!-- List scripts here as they are added -->
