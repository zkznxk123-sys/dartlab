from __future__ import annotations

import json

from dartlab.skill_os.compiler import buildSkillArtifacts


def main() -> None:
    result = buildSkillArtifacts()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
