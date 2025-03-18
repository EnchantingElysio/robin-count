requirements:
	uv sync --no-dev && uv pip freeze > requirements.txt && uv sync --only-dev && uv pip freeze > dev.requirements.txt && uv sync