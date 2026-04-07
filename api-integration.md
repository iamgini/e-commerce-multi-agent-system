# API Integration

- [API Integration](#api-integration)
  - [Testing with fastapi](#testing-with-fastapi)
  - [chainlit\_app](#chainlit_app)
  - [Troubleshooting](#troubleshooting)
    - [Reinstall Python libs in uv](#reinstall-python-libs-in-uv)
    - [Python 3.14 + anyio compatibility issue](#python-314--anyio-compatibility-issue)
  - [Appendix - Building Container](#appendix---building-container)


## Testing with fastapi

```shell
uv run uvicorn fast-api:app --host 0.0.0.0 --port 8000 --reload
```

Smoke test (three turns to verify session continuity):

```shell
# Turn 1 — get a session_id back
SESSION=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hi, what are your store hours?", "user_id": "user_001"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "Session: $SESSION"

# Turn 2 — same session
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"what payment methods do you accept?\", \"session_id\": \"$SESSION\", \"user_id\": \"user_001\"}" \
  | python3 -m json.tool

# Turn 3 — check route label
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"show me wireless headphones under 200\", \"session_id\": \"$SESSION\", \"user_id\": \"user_001\"}" \
  | python3 -m json.tool
```

## chainlit_app

```shell
$ uv run python -c "import chainlit_app"
$ uv run chainlit run chainlit_app.py --port 8001
$ uv run chainlit run chainlit_app.py --port 8001 -h  # headless mode
```

And access `http://localhost:8001`

- **Documentation:** Get started with our comprehensive [Chainlit Documentation](https://docs.chainlit.io) 📚
-
## Troubleshooting

### Reinstall Python libs in uv

```shell
uv pip install chainlit --reinstall
```

### Python 3.14 + anyio compatibility issue

```shell
# Install Python 3.12 if not already available
uv python install 3.12

# Create a virtual environment with Python 3.12
uv venv --python 3.12 .venv

# Activate it
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

uv pip install chainlit

$ uv run --python 3.12 chainlit run chainlit_app.py --port 8001
```

## Appendix - Building Container

```shell
$ podman build -t shopbot --file Containerfile-ShopBot

# podman run --env-file .env -p 8001:8001 shopbot
podman run -e OPENAI_API_KEY=$OPENAI_API_KEY -p 8001:8001 shopbot
```
