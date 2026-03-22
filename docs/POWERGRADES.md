# PowerGrades

ResolveAIO does not fabricate `.drx` files.

Real PowerGrades are exported through DaVinci Resolve's Gallery API, so these commands require:

1. DaVinci Resolve to be open
2. A project and timeline to be active
3. Scripting access to be available on the machine

## Export one grade

```bash
python -m src.automation.powergrade_tools export-current "Hero Look"
```

This grabs the currently selected graded clip and writes a real `.drx` file into [`presets/powergrades`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/powergrades).

## Export a timeline set

```bash
python -m src.automation.powergrade_tools export-timeline
```

This grabs stills from all clips on the current timeline and exports them as `.drx` files into a timeline-named subfolder under [`presets/powergrades`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/powergrades).

## Apply a DRX file

```bash
python -m src.automation.powergrade_tools apply presets/powergrades/hero-look.drx
```

That applies the DRX to all clips on video track 1 of the current timeline.

## From the Chat UI

Commands supported in the UI:

- `export current powergrade "Hero Look"`
- `export timeline powergrades`
- `apply preset "Hero Look"` once the `.drx` exists in [`presets/powergrades`](/Volumes/Transcend/resolve plugin aio/resolve-aio/presets/powergrades)
