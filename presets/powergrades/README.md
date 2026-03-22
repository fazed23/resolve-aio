# PowerGrades

This folder holds real exported Resolve PowerGrades (`.drx`).

Current state:

- The app now ships real DCTLs, LUTs, and Fusion templates.
- Real PowerGrades should be exported from Resolve through the Gallery API.

Recommended next step:

1. Open Resolve and grade the current clip.
2. Run `python -m src.automation.powergrade_tools export-current "Hero Look"`.
3. Or run `python -m src.automation.powergrade_tools export-timeline`.
4. The exported `.drx` files will appear here and immediately show up in the UI catalog.

More details: [`docs/POWERGRADES.md`](/Volumes/Transcend/resolve plugin aio/resolve-aio/docs/POWERGRADES.md)
