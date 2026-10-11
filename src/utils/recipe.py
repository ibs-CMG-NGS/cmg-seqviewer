"""
Recipe: 입력 파일 + 필터 기준 + 출력 설정을 하나의 YAML/JSON 파일로 묶어서,
"확정된 절차"를 비대화형으로 재현 가능하게 기록한다.

models.enrichment_models.EnrichmentRequest.to_recipe_dict()/from_recipe_dict()의
JSON-safe round-trip 패턴을 일반 load -> filter -> export 파이프라인으로 확장한
것 — cli.py의 `run`(단일 파일)과 `batch`(여러 파일에 동일 recipe 반복 적용)
서브커맨드가 쓴다. 탐색적 분석에는 필요 없고, 절차가 확정된 뒤 재현/배치용으로만
쓰는 게 의도다.

Recipe 파일 예시 (recipe.yaml):
    input: data/sample1_DE.xlsx
    # type: atac              # 선택 — "Open ATAC-seq Dataset..."처럼 자동 감지를 건너뛰고 강제
    # name: MyDataset          # 선택 — 데이터셋 이름 (기본값: 파일명)
    filter:
      mode: statistical         # FilterMode 값 (statistical/gene_list/keyword/column_subset)
      adj_pvalue_max: 0.05
      log2fc_min: 1.0
      regulation_direction: both
    output:
      table: results/sample1_filtered.xlsx
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Recipe:
    input: str
    type: Optional[str] = None
    name: Optional[str] = None
    filter: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Recipe":
        """.yaml/.yml/.json recipe 파일을 읽어 Recipe로 파싱한다.

        알 수 없는 최상위 키나 'input' 누락은 바로 ValueError — 오탈자로 조용히
        무시된 설정이 적용 안 된 채 실행되는 걸 막는다 (G14: 조용한 fallback 금지
        원칙을 recipe 파싱에도 동일 적용).
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Recipe not found: {path}")
        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            import yaml
            data = yaml.safe_load(text) or {}
        elif suffix == ".json":
            data = json.loads(text) or {}
        else:
            raise ValueError(
                f"Unsupported recipe format: {suffix!r} (use .yaml/.yml/.json)")

        if not isinstance(data, dict):
            raise ValueError(f"Recipe {path} must be a mapping at the top level")
        if "input" not in data:
            raise ValueError(f"Recipe {path} is missing the required key 'input'")
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(
                f"Recipe {path} has unknown top-level key(s): {sorted(unknown)} "
                f"(expected a subset of {sorted(known)})")
        return cls(**data)

    def build_filter_criteria(self):
        """filter 절(dict)을 FilterCriteria로 변환. mode는 문자열(FilterMode.value)로
        받아 enum으로 변환 — 그 외 키는 FilterCriteria 필드명과 1:1 그대로 전달하므로
        recipe의 filter: 절 키는 FilterCriteria의 필드명과 같아야 한다."""
        from models.data_models import FilterCriteria, FilterMode

        raw = dict(self.filter)
        mode_value = raw.pop("mode", FilterMode.STATISTICAL.value)
        try:
            mode = FilterMode(mode_value)
        except ValueError as exc:
            valid = [m.value for m in FilterMode]
            raise ValueError(
                f"Recipe filter.mode={mode_value!r} is not valid (expected one of {valid})"
            ) from exc

        valid_fields = {f.name for f in dataclasses.fields(FilterCriteria)} - {"mode"}
        unknown = set(raw) - valid_fields
        if unknown:
            raise ValueError(
                f"Recipe filter has unknown key(s): {sorted(unknown)} "
                f"(expected a subset of {sorted(valid_fields)})")
        return FilterCriteria(mode=mode, **raw)
