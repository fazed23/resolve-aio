# GPT Setup

ResolveAIO reads the OpenAI key from:

`config/resolve_aio.env`

Example:

```env
OPENAI_API_KEY=sk-proj-your-real-key
```

Notes:

- `scripts/run.sh --chat` and `scripts/run.bat --chat` load this file automatically.
- The Python chat backend also loads it directly, so the key works even when the UI is started without the shell scripts.
- If `OPENAI_API_KEY` is already set in the system environment, that value wins.
