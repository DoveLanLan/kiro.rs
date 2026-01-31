#!/usr/bin/env python3

import json
import os
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "config" / "credentials.json"

    cache_dir = os.environ.get("AWS_SSO_CACHE_DIR") or (Path.home() / ".aws/sso/cache")
    cache_dir = Path(cache_dir)
    token_path = cache_dir / "kiro-auth-token.json"

    if not token_path.exists():
        raise SystemExit(
            f"找不到 {token_path}。\n"
            f"- 如果你不在默认目录，请先设置 AWS_SSO_CACHE_DIR\n"
            f"- 确认你已在 Kiro IDE 里完成组织账号登录（IdC）"
        )

    token = json.loads(token_path.read_text(encoding="utf-8"))
    refresh_token = token.get("refreshToken")
    if not refresh_token:
        raise SystemExit(f"{token_path} 缺少 refreshToken")

    # 关键：不写 accessToken，并强制 expiresAt 过期，让服务启动后立即走 refresh 流程
    # 之后会把新的 accessToken/refreshToken/expiresAt 回写到该文件（要求该文件可写）。
    cred = {
        "priority": 0,
        "authMethod": "idc",
        "refreshToken": refresh_token,
        "expiresAt": "1970-01-01T00:00:00Z",
    }

    if token.get("clientIdHash"):
        cred["clientIdHash"] = token["clientIdHash"]
    if token.get("region"):
        cred["region"] = token["region"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([cred], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"已生成 {out_path}")
    print("提示：此文件会被服务自动回写（包含 accessToken / expiresAt 等），请勿提交到仓库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

