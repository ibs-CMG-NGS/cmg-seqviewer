"""
Project Save / Load — .seqproj format

분석 세션을 JSON 기반 .seqproj 파일로 저장하고 복원한다.

저장 대상:
  - 로드된 데이터셋 파일 경로 + 타입
  - 각 sheet의 타입(whole/filtered/comparison)과 filter_params
  - UI 상태 (활성 탭 인덱스)

복원 방식:
  - ProjectIO.load()는 명세(spec dict)만 반환
  - 실제 DataFrame 재구성은 MainWindow._on_open_project()가 수행
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FORMAT_VERSION = "1.0"
FILE_EXTENSION = ".seqproj"


class ProjectIO:
    """프로젝트 파일 읽기/쓰기 유틸리티 (순수 정적 메서드)."""

    # ── 저장 ─────────────────────────────────────────────────────────

    @staticmethod
    def save(path: str | Path, spec: Dict[str, Any]) -> None:
        """spec dict를 .seqproj 파일로 저장.

        Args:
            path: 저장 경로 (.seqproj)
            spec: build_spec()으로 생성한 프로젝트 명세
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        logger.info(f"Project saved: {path}")

    @staticmethod
    def load(path: str | Path) -> Dict[str, Any]:
        """파일에서 프로젝트 명세를 읽어 반환.

        Returns:
            spec dict (실제 DataFrame 로드는 호출자 책임)

        Raises:
            ValueError: 포맷 버전 불일치
            FileNotFoundError: 파일 없음
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        ver = spec.get("format_version", "")
        if not ver.startswith("1."):
            raise ValueError(
                f"Unsupported .seqproj format version: {ver}. "
                "Please update CMG-SeqViewer."
            )

        # 상대 경로 → 절대 경로 변환
        spec = ProjectIO._resolve_paths(spec, path.parent)
        logger.info(f"Project loaded: {path}")
        return spec

    # ── 명세 빌드 ────────────────────────────────────────────────────

    @staticmethod
    def build_spec(
        tab_data: Dict[int, Dict],
        dataset_file_map: Dict[str, str],
        dataset_type_map: Dict[str, str],
        active_tab_index: int,
        tree_expanded: Optional[List[str]] = None,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """현재 분석 상태로부터 저장 가능한 spec dict를 생성.

        Args:
            tab_data: MainWindow.tab_data
            dataset_file_map: {dataset_name: absolute_file_path}
            dataset_type_map: {dataset_name: DatasetType.value 문자열}
            active_tab_index: 현재 활성 탭 인덱스
            tree_expanded: 트리에서 펼쳐진 루트 노드 이름 목록
            project_path: 저장 경로 (상대 경로 변환에 사용)
        """
        project_dir = project_path.parent if project_path else None

        # tab_data를 dataset 기준으로 그룹화
        datasets_spec: Dict[str, Dict] = {}

        for idx in sorted(tab_data.keys()):
            entry = tab_data[idx]
            sheet_type = entry.get("sheet_type", "whole")
            parent = entry.get("parent_dataset")
            label = entry.get("sheet_label", f"Sheet {idx}")

            # comparison 탭은 별도 처리
            if sheet_type == "comparison":
                continue

            root = parent or entry.get("dataset", {})
            # dataset 객체에서 name 추출
            if hasattr(root, "name"):
                root = root.name
            if not root or not isinstance(root, str):
                continue

            if root not in datasets_spec:
                file_path = dataset_file_map.get(root, "")
                if project_dir and file_path:
                    try:
                        file_path = os.path.relpath(file_path, start=project_dir)
                    except ValueError:
                        pass  # 드라이브가 다를 경우 절대 경로 유지
                datasets_spec[root] = {
                    "name": root,
                    "type": dataset_type_map.get(root, ""),
                    "file_path": file_path,
                    "sheets": [],
                }

            sheet_entry: Dict[str, Any] = {
                "type": sheet_type,
                "label": label,
                "tab_index": idx,
            }
            fp = entry.get("filter_params")
            if fp is not None:
                sheet_entry["filter_params"] = fp if isinstance(fp, dict) else fp
            cp = entry.get("comparison_params")
            if cp is not None:
                sheet_entry["comparison_params"] = cp

            datasets_spec[root]["sheets"].append(sheet_entry)

        # comparison 탭 수집
        comparisons = []
        for idx in sorted(tab_data.keys()):
            entry = tab_data[idx]
            if entry.get("sheet_type") == "comparison":
                cp = entry.get("comparison_params") or {}
                comparisons.append({
                    "label": entry.get("sheet_label", "Comparison"),
                    "tab_index": idx,
                    "comparison_params": cp,
                })

        spec: Dict[str, Any] = {
            "format_version": FORMAT_VERSION,
            "app_version": "1.2.1",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "description": "",
            "datasets": list(datasets_spec.values()),
            "comparisons": comparisons,
            "ui_state": {
                "active_tab_index": active_tab_index,
                "tree_expanded_datasets": tree_expanded or [],
            },
        }
        return spec

    # ── 내부 유틸 ────────────────────────────────────────────────────

    @staticmethod
    def _resolve_paths(spec: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
        """spec 내 상대 경로를 절대 경로로 변환."""
        for ds in spec.get("datasets", []):
            fp = ds.get("file_path", "")
            if fp and not os.path.isabs(fp):
                ds["file_path"] = str((project_dir / fp).resolve())
        return spec
