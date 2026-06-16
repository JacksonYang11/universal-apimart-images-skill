#!/usr/bin/env python3
"""Batch-generate WeChat article images through APIMart GPT-Image-2."""

from __future__ import annotations

import argparse
import base64
import ctypes
import datetime as dt
import html
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "https://api.apimart.ai"
DEFAULT_OUTPUT_DIR = r"D:\AI-generated-images"
COMPLETE_STATUSES = {"completed", "complete", "succeeded", "success", "done", "finished"}
FAILED_STATUSES = {"failed", "failure", "error", "cancelled", "canceled", "timeout"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and download APIMart GPT-Image-2 tasks.")
    parser.add_argument("json_file", help="Path to the approved WeChat image task JSON.")
    parser.add_argument("--api-key", default=os.environ.get("APIMART_API_KEY"), help="APIMart API key. Defaults to APIMART_API_KEY.")
    parser.add_argument("--api-base", default=os.environ.get("APIMART_API_BASE", DEFAULT_API_BASE), help="APIMart API base URL.")
    parser.add_argument("--output-dir", default=None, help=f"Output root. Defaults to JSON output_dir or {DEFAULT_OUTPUT_DIR}.")
    parser.add_argument("--run-dir", default=None, help="Exact output folder to use. Useful when resuming existing task IDs.")
    parser.add_argument("--initial-wait", type=float, default=60.0, help="Seconds to wait after all tasks are submitted before first polling attempt.")
    parser.add_argument("--poll-interval", type=float, default=30.0, help="Seconds between batch polling attempts.")
    parser.add_argument("--timeout", type=float, default=900.0, help="Maximum seconds to wait after the initial wait for all tasks.")
    parser.add_argument("--dry-run", action="store_true", help="Validate input and show planned API payloads without calling APIMart.")
    parser.add_argument("--no-notify", action="store_true", help="Disable completion sound and message box.")
    args = parser.parse_args()

    task_file = Path(args.json_file).expanduser().resolve()
    data = load_json(task_file)
    article_title = str(data.get("article_title") or data.get("title") or "wechat_article").strip()
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise SystemExit("JSON must contain a non-empty images array.")

    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        output_root = Path(args.output_dir or data.get("output_dir") or DEFAULT_OUTPUT_DIR)
        run_dir = output_root / f"{dt.datetime.now():%Y%m%d_%H%M%S}_{sanitize_filename(article_title)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks = [normalize_image_task(item, index, task_file.parent) for index, item in enumerate(images)]
    manifest: dict[str, Any] = {
        "article_title": article_title,
        "article_source": data.get("article_source", ""),
        "wechat_intro": data.get("wechat_intro", ""),
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "api_base": args.api_base,
        "model": "gpt-image-2",
        "resolution": "1k",
        "size": "16:9",
        "n": 1,
        "output_dir": str(run_dir),
        "tasks": [],
    }

    if args.dry_run:
        for task in tasks:
            payload = build_payload(task)
            manifest["tasks"].append({"name": task["name"], "usage": task["usage"], "payload": payload})
        write_manifest_and_preview(run_dir, manifest)
        print(f"Dry run OK. Planned {len(tasks)} image task(s).")
        print(f"Output folder: {run_dir}")
        return 0

    if not args.api_key:
        raise SystemExit("APIMART_API_KEY is not set. Set it or pass --api-key.")

    failures = 0
    records: list[dict[str, Any]] = []
    record_tasks: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for task in tasks:
        record: dict[str, Any] = {
            "name": task["name"],
            "usage": task["usage"],
            "prompt": task["prompt"],
            "refs": task["refs_original"],
            "status": "pending",
        }
        records.append(record)
        record_tasks.append((record, task))
        manifest["tasks"].append(record)
        write_json(run_dir / "manifest.json", manifest)

        try:
            if task.get("task_id"):
                task_id = str(task["task_id"])
                record["task_id"] = task_id
                record["status"] = "submitted"
                print(f"[resume] {task['name']} task_id={task_id}")
            else:
                payload = build_payload(task)
                response = post_json(args.api_base, "/v1/images/generations", payload, args.api_key)
                task_id = extract_task_id(response)
                record["task_id"] = task_id
                record["submit_response"] = response
                record["status"] = "submitted"
                print(f"[submitted] {task['name']} task_id={task_id}")
            write_json(run_dir / "manifest.json", manifest)
        except Exception as exc:  # noqa: BLE001 - CLI should continue with remaining tasks.
            failures += 1
            record["status"] = "failed"
            record["error"] = str(exc)
            print(f"[submit failed] {task['name']}: {exc}", file=sys.stderr)
        finally:
            write_manifest_and_preview(run_dir, manifest)

    if failures == 0:
        print(f"[wait] all tasks started; waiting {max(args.initial_wait, 0):g} seconds before polling")
        time.sleep(max(args.initial_wait, 0))
        failures += poll_all_tasks(records, manifest, run_dir, args.api_base, args.api_key, args.poll_interval, args.timeout)

    if failures == 0:
        failures += download_all_images(record_tasks, manifest, run_dir)

    write_manifest_and_preview(run_dir, manifest)

    if failures:
        downloaded_count = sum(1 for record in records if record.get("status") == "downloaded")
        summary = f"未全部完成：{downloaded_count}/{len(tasks)} 张图片已生成并下载。"
    else:
        summary = f"完成：{len(tasks)}/{len(tasks)} 张图片已生成并下载。"
    print(summary)
    print(f"Output folder: {run_dir}")
    if not args.no_notify and failures == 0:
        notify(summary, str(run_dir))
    return 1 if failures else 0


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise SystemExit(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Top-level JSON value must be an object.")
    return data


def normalize_image_task(item: Any, index: int, base_dir: Path) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise SystemExit(f"images[{index}] must be an object.")
    prompt = str(item.get("prompt") or "").strip()
    if not prompt:
        raise SystemExit(f"images[{index}] is missing prompt.")
    name = sanitize_filename(str(item.get("name") or f"image_{index + 1:02d}"))
    usage = str(item.get("usage") or item.get("role") or name).strip()
    refs = item.get("refs", item.get("image_urls", []))
    if refs is None:
        refs = []
    if not isinstance(refs, list):
        raise SystemExit(f"images[{index}].refs must be an array when present.")
    return {
        "index": index,
        "name": name,
        "usage": usage,
        "prompt": prompt,
        "refs_original": refs,
        "image_urls": [normalize_reference(ref, base_dir) for ref in refs],
        "task_id": item.get("task_id"),
    }


def normalize_reference(ref: Any, base_dir: Path) -> str:
    value = str(ref).strip()
    if not value:
        raise SystemExit("Reference image path/URL cannot be empty.")
    if value.startswith(("http://", "https://", "data:")):
        return value
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    path = path.resolve()
    if not path.exists():
        raise SystemExit(f"Reference image does not exist: {path}")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_payload(task: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": "gpt-image-2",
        "prompt": task["prompt"],
        "n": 1,
        "size": "16:9",
        "resolution": "1k",
    }
    if task["image_urls"]:
        payload["image_urls"] = task["image_urls"]
    return payload


def post_json(api_base: str, path: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    return request_json("POST", f"{api_base.rstrip('/')}{path}", api_key, payload)


def get_json(api_base: str, path: str, api_key: str) -> dict[str, Any]:
    return request_json("GET", f"{api_base.rstrip('/')}{path}", api_key, None)


def request_json(method: str, url: str, api_key: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error calling {url}: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {raw[:500]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected JSON response from {url}: {parsed!r}")
    return parsed


def extract_task_id(response: dict[str, Any]) -> str:
    for path in (("task_id",), ("id",), ("data", "task_id"), ("data", "id"), ("task", "id")):
        value = get_nested(response, path)
        if value:
            return str(value)
    data = response.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                value = item.get("task_id") or item.get("id")
                if value:
                    return str(value)
    raise RuntimeError(f"Could not find task_id in submit response: {response}")


def poll_all_tasks(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    run_dir: Path,
    api_base: str,
    api_key: str,
    interval: float,
    timeout: float,
) -> int:
    pending = [record for record in records if record.get("task_id") and record.get("status") != "failed"]
    deadline = time.monotonic() + timeout
    failures = 0

    while pending and time.monotonic() <= deadline:
        completed_this_round = 0
        for record in list(pending):
            task_id = str(record["task_id"])
            try:
                response = get_json(api_base, f"/v1/tasks/{task_id}", api_key)
                status = (extract_status(response) or "").lower()
                record["last_response"] = response
                print(f"[poll] {record['name']} task_id={task_id} status={status or 'unknown'}")

                if status in COMPLETE_STATUSES:
                    image_urls = extract_image_urls(response)
                    if not image_urls:
                        raise RuntimeError("Task completed but no image URL was found in the response.")
                    record["final_response"] = response
                    record["image_urls"] = image_urls
                    record["status"] = "completed"
                    record.pop("last_response", None)
                    record.pop("last_poll_error", None)
                    pending.remove(record)
                    completed_this_round += 1
                elif status in FAILED_STATUSES:
                    record["status"] = "failed"
                    record["error"] = f"Task failed with status={status}"
                    pending.remove(record)
                    failures += 1
                else:
                    record["status"] = status or "running"
            except Exception as exc:  # noqa: BLE001 - transient polling errors can be retried.
                record["status"] = "poll_error"
                record["last_poll_error"] = str(exc)
                print(f"[poll error] {record['name']}: {exc}", file=sys.stderr)

        write_manifest_and_preview(run_dir, manifest)
        if failures:
            return failures
        if pending:
            print(f"[wait] {len(records) - len(pending)}/{len(records)} task(s) completed; polling again in {max(interval, 1):g} seconds")
            time.sleep(max(interval, 1))
        elif completed_this_round:
            print(f"[complete] all {len(records)} task(s) generated successfully")

    for record in pending:
        record["status"] = "failed"
        record["error"] = "Timed out waiting for all tasks to complete."
        failures += 1
    if pending:
        write_manifest_and_preview(run_dir, manifest)
    return failures


def download_all_images(
    record_tasks: list[tuple[dict[str, Any], dict[str, Any]]],
    manifest: dict[str, Any],
    run_dir: Path,
) -> int:
    failures = 0
    for record, task in record_tasks:
        try:
            image_urls = record.get("image_urls") or []
            if not image_urls:
                raise RuntimeError("No image URL is available for download.")

            downloaded = []
            for image_index, image_url in enumerate(image_urls[:1], start=1):
                filename = make_image_filename(task, image_index, image_url)
                file_path = download_file(image_url, run_dir / filename)
                downloaded.append(str(file_path))
            record["files"] = downloaded
            record["status"] = "downloaded"
            print(f"[downloaded] {record['name']} -> {downloaded[0]}")
        except Exception as exc:  # noqa: BLE001 - CLI should keep downloading remaining files.
            failures += 1
            record["status"] = "failed"
            record["error"] = str(exc)
            print(f"[download failed] {record['name']}: {exc}", file=sys.stderr)
        finally:
            write_manifest_and_preview(run_dir, manifest)
    return failures


def poll_task(api_base: str, task_id: str, api_key: str, interval: float, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_response: dict[str, Any] | None = None
    while time.monotonic() <= deadline:
        response = get_json(api_base, f"/v1/tasks/{task_id}", api_key)
        last_response = response
        status = (extract_status(response) or "").lower()
        print(f"[poll] {task_id} status={status or 'unknown'}")
        if status in COMPLETE_STATUSES:
            return response
        if status in FAILED_STATUSES:
            raise RuntimeError(f"Task {task_id} failed with status={status}: {response}")
        time.sleep(max(interval, 1))
    raise RuntimeError(f"Timed out waiting for task {task_id}. Last response: {last_response}")


def extract_status(response: dict[str, Any]) -> str | None:
    for path in (("status",), ("state",), ("data", "status"), ("data", "state"), ("task", "status")):
        value = get_nested(response, path)
        if value:
            return str(value)
    return None


def extract_image_urls(response: Any) -> list[str]:
    urls: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and is_http_url(child):
                    key_lower = key.lower()
                    if any(token in key_lower for token in ("url", "image", "output", "result")):
                        urls.append(child)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and is_http_url(value):
            urls.append(value)

    visit(response)
    unique = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    image_like = [url for url in unique if re.search(r"\.(png|jpe?g|webp)(\?|$)", url, re.I)]
    return image_like or unique


def get_nested(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def download_file(url: str, destination: Path) -> Path:
    request = Request(url, headers={"User-Agent": "wechat-apimart-images/1.0"})
    try:
        with urlopen(request, timeout=180) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} downloading {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error downloading {url}: {exc}") from exc

    suffix = suffix_from_content_type(content_type)
    if suffix and destination.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        destination = destination.with_suffix(suffix)
    destination.write_bytes(body)
    return destination


def suffix_from_content_type(content_type: str) -> str:
    lowered = content_type.lower()
    if "png" in lowered:
        return ".png"
    if "jpeg" in lowered or "jpg" in lowered:
        return ".jpg"
    if "webp" in lowered:
        return ".webp"
    return ""


def make_image_filename(task: dict[str, Any], image_index: int, image_url: str) -> str:
    parsed_suffix = Path(urlparse(image_url).path).suffix.lower()
    suffix = parsed_suffix if parsed_suffix in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
    base = f"{task['index']:02d}_{task['name']}"
    if image_index > 1:
        base = f"{base}_{image_index}"
    return f"{base}{suffix}"


def sanitize_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value.strip())
    value = re.sub(r"\s+", "_", value)
    value = value.strip("._ ")
    return value[:80] or "untitled"


def write_manifest_and_preview(run_dir: Path, manifest: dict[str, Any]) -> None:
    write_json(run_dir / "manifest.json", manifest)
    write_preview(run_dir / "preview.html", manifest)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_preview(path: Path, manifest: dict[str, Any]) -> None:
    cards = []
    for task in manifest.get("tasks", []):
        files = task.get("files") or []
        img_html = ""
        if files:
            rel = Path(files[0]).name
            img_html = f'<img src="{html.escape(rel)}" alt="{html.escape(task.get("name", ""))}">'
        error = f'<p class="error">{html.escape(str(task.get("error", "")))}</p>' if task.get("error") else ""
        cards.append(
            "<section>"
            f"{img_html}"
            f"<h2>{html.escape(str(task.get('usage') or task.get('name') or 'image'))}</h2>"
            f"<p class=\"meta\">{html.escape(str(task.get('status', '')))}</p>"
            f"<pre>{html.escape(str(task.get('prompt', '')))}</pre>"
            f"{error}"
            "</section>"
        )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(str(manifest.get("article_title", "WeChat Images")))}</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Microsoft YaHei, sans-serif; background: #f6f7f9; color: #1f2933; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .intro {{ color: #52616b; margin: 0 0 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }}
    section {{ background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; overflow: hidden; }}
    img {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; display: block; background: #e4e7eb; }}
    h2 {{ font-size: 17px; margin: 14px 16px 4px; }}
    .meta {{ margin: 0 16px 10px; color: #7b8794; font-size: 13px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; margin: 0; padding: 0 16px 16px; font-family: inherit; font-size: 14px; line-height: 1.6; }}
    .error {{ color: #b42318; margin: 0 16px 16px; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(str(manifest.get("article_title", "WeChat Images")))}</h1>
    <p class="intro">{html.escape(str(manifest.get("wechat_intro", "")))}</p>
    <div class="grid">{''.join(cards)}</div>
  </main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def notify(summary: str, folder: str) -> None:
    if os.name != "nt":
        print("\a", end="")
        return
    try:
        import winsound

        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(None, f"{summary}\n\n{folder}", "APIMart 图片生成完成", 0x40)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit("Interrupted.")
