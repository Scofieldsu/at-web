"""配置管理模块 — 浏览 / 编辑 / 上传 config/ 目录下的所有配置文件。

设计：
  - 列出 config/ 下所有文件（相对路径），供前端选择；
  - 按相对路径读取单个文件的文本内容（文本类可编辑，二进制类只读）；
  - 保存单个文件（YAML/JSON 会做语法校验，其它文本原样写）；
  - 上传文件覆盖：只允许覆盖"同名已存在"的文件。

安全：所有相对路径都经 _safe_resolve 收敛到 config/ 内，拒绝路径穿越（../）。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("config", __name__, url_prefix="/api/config")

# 视为"文本可编辑"的后缀；其余（xlsx 等）仅列出、不提供文本编辑
TEXT_SUFFIXES = {".yaml", ".yml", ".json", ".pac", ".txt", ".ini", ".conf", ".env", ".md"}
# 列表中隐藏的备份/无关文件后缀
HIDDEN_SUFFIXES = {".old"}


def _config_root() -> Path:
    return (Path(current_app.config["PROJECT_ROOT"]) / "config").resolve()


def _safe_resolve(rel_path: str) -> Path | None:
    """把相对路径收敛到 config/ 内，返回绝对路径；越界或非法返回 None。"""
    if not rel_path:
        return None
    root = _config_root()
    rel = rel_path.replace("\\", "/").lstrip("/")
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None  # 路径穿越
    return target


def _is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


@bp.route("/files", methods=["GET"])
def list_files():
    """列出 config/ 下所有文件（相对路径 + 大小 + 是否可文本编辑）。"""
    root = _config_root()
    if not root.exists():
        return jsonify({"files": [], "root": str(root)})
    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() in HIDDEN_SUFFIXES:
            continue
        rel = p.relative_to(root).as_posix()
        files.append({
            "path": rel,
            "size": p.stat().st_size,
            "editable": _is_text(p),
            "suffix": p.suffix.lower(),
        })
    return jsonify({"files": files, "root": str(root)})


@bp.route("/file", methods=["GET"])
def get_file():
    """读取单个配置文件文本。Query: ?path=<相对路径>"""
    rel = request.args.get("path", "")
    target = _safe_resolve(rel)
    if target is None:
        return jsonify({"error": "非法路径"}), 400
    if not target.exists() or not target.is_file():
        return jsonify({"error": "文件不存在"}), 404
    if not _is_text(target):
        return jsonify({"error": "该文件类型不支持文本编辑", "editable": False}), 415
    try:
        raw = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return jsonify({"error": f"读取失败: {e}"}), 500
    return jsonify({"path": rel, "raw": raw, "editable": True})


def _validate_syntax(target: Path, raw: str) -> str | None:
    """按后缀做语法校验，返回错误信息；通过返回 None。"""
    suffix = target.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            yaml.safe_load(raw)
        elif suffix == ".json":
            json.loads(raw)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        return str(e)
    return None


@bp.route("/file", methods=["PUT"])
def save_file():
    """保存单个配置文件。Body: {"path": "<相对路径>", "raw": "<文本>"}"""
    data = request.get_json(force=True, silent=True) or {}
    rel = data.get("path", "")
    raw = data.get("raw")
    if raw is None:
        return jsonify({"error": "raw 字段必填"}), 400
    target = _safe_resolve(rel)
    if target is None:
        return jsonify({"error": "非法路径"}), 400
    if not target.exists():
        return jsonify({"error": "文件不存在，如需新增请用上传"}), 404
    if not _is_text(target):
        return jsonify({"error": "该文件类型不支持文本编辑"}), 415

    err = _validate_syntax(target, raw)
    if err:
        return jsonify({"success": False, "error": f"语法错误: {err}"}), 400

    try:
        target.write_text(raw, encoding="utf-8")
    except OSError as e:
        return jsonify({"success": False, "error": f"写入失败: {e}"}), 500
    return jsonify({"success": True, "path": rel, "note": "已保存，部分配置需重启服务后生效"})


@bp.route("/upload", methods=["POST"])
def upload_file():
    """上传文件覆盖同名配置。

    multipart/form-data:
        file: 上传的文件
        path: 目标相对路径（决定覆盖哪个文件所在目录 + 期望文件名）
    """
    if "file" not in request.files:
        return jsonify({"error": "缺少上传文件"}), 400
    upload = request.files["file"]
    rel = request.form.get("path", "")
    target = _safe_resolve(rel)
    if target is None:
        return jsonify({"error": "非法路径"}), 400

    upload_name = (upload.filename or "").replace("\\", "/").split("/")[-1]
    if not upload_name:
        return jsonify({"error": "上传文件名为空"}), 400

    if upload_name != target.name:
        return jsonify({
            "success": False,
            "error": f"文件名不一致：上传的是「{upload_name}」，目标是「{target.name}」。"
                     f"请将上传文件改名为「{target.name}」后重试。",
        }), 400

    if not target.exists():
        return jsonify({
            "success": False,
            "error": f"config/ 下不存在同名文件「{rel}」，只允许覆盖已有配置。",
        }), 400

    backup = target.with_suffix(target.suffix + ".old")
    try:
        shutil.copy2(target, backup)
        upload.save(str(target))
    except OSError as e:
        return jsonify({"success": False, "error": f"覆盖失败: {e}"}), 500

    return jsonify({
        "success": True,
        "path": rel,
        "backup": backup.relative_to(_config_root()).as_posix(),
        "note": f"已覆盖并备份旧文件为 {backup.name}",
    })
