# Debugging Log

This document records two real issues encountered during development, along with their symptoms, diagnoses, root causes, fixes, and verifications.

---

## Issue 1: Project File Path Validation Error
- **Symptom**: Attempting to write `audit.py` to the workspace directory `c:\Users\mehta\Desktop\New folder\` returned an error:
  `c:\Users\mehta\Desktop\New folder\audit.py is not a valid artifact path; artifacts must be in C:\Users\mehta\.gemini\antigravity\brain\...`
- **Diagnosis**: The tool validated the call as an artifact creation attempt because `ArtifactMetadata` was included in the arguments.
- **Root Cause**: The workspace files are standard code assets, but the AI included `ArtifactMetadata` (which is reserved exclusively for system artifacts written to the app data subdirectory).
- **Fix**: Removed the `ArtifactMetadata` block entirely from the `write_to_file` call arguments.
- **Verification**: The file was successfully written to the workspace directory.

---

## Issue 2: Python Inline syntax error on Windows PowerShell
- **Symptom**: Running a quick command line python check for retrieved facets returned:
  `SyntaxError: f-string expression part cannot include a backslash`
- **Diagnosis**: PowerShell handles double-quoted arguments by passing them to Python with escape sequences. When attempting to escape the inner double quotes for the dictionary key (`res[\"normalized_facet\"]`), the backslash was parsed literally by Python.
- **Root Cause**: Windows PowerShell string escaping differences caused a literal backslash to enter Python's f-string block, which is syntax-forbidden in Python.
- **Fix**: Used single quotes inside the double quotes for the python script arguments (`res['normalized_facet']`) to avoid escaping entirely.
- **Verification**: The command executed successfully and printed retrieved facets.
