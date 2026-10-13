"""Write the OpenAPI schema the web app's TypeScript types are generated from.

python -m irerero_api.openapi_export apps/web/openapi.json
"""

import json
import sys
from pathlib import Path

from irerero_api.main import app


def main() -> None:
    target = Path(sys.argv[1])
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
