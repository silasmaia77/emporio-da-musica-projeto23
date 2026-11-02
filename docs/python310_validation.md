# Python 3.10 compatibility update — Project 23

Runtime tested: CPython 3.10.22 on Linux, in a new isolated virtual environment.

Changes:
- Streamlit 1.66.1 -> 1.65.0, because 1.66 requires Python >=3.11.
- ipykernel 7.4.0 -> 7.3.0, because 7.4 requires Python >=3.11.
- Explicit tzdata dependency for Windows ZoneInfo support.
- Docker base changed to python:3.10-slim.
- Notebook metadata, assertions and documentation now target Python 3.10.
- Virtual-environment directories excluded from Git and Docker build context.

Validation:
- All runtime and development dependencies installed successfully in CPython 3.10.22.
- 46 pytest cases passed in that interpreter.
- Streamlit AppTest startup passed in that interpreter.
- All 25 notebook Python blocks executed sequentially in-process on Python 3.10; external LLM/Meta checks explicitly skipped.
- Dependency resolution for Windows x86_64 / Python 3.10 succeeded. No actual Windows execution was available; the candidate should run the same validation on their machine.

Ports remain 8523 (UI), 8023 (Meta API); Docker project remains emporio_musica_23.
No credentials are bundled. No live LLM or Meta messages were sent. Docker execution remains unvalidated.
