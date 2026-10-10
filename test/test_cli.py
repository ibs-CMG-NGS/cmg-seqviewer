"""
cli.py 테스트 — 커맨드라인으로 load/filter가 GUI와 동일한 경로(utils.dataset_detection
/ MainPresenter.compute_filtered_df)를 거쳐 정확히 동작하는지, Qt 없이 끝까지
동작하는지, 인식 안 되는 필수 컬럼은 exit code != 0 + 명확한 메시지로 실패하는지.
"""

import pandas as pd
import pytest

import cli


def _write_de_xlsx(tmp_path):
    df = pd.DataFrame({
        "gene_id": [f"G{i}" for i in range(10)],
        "log2fc": [2.0, -3.0, 0.1, 1.5, -0.2, 4.0, -1.8, 0.05, 2.2, -2.5],
        "adj_pvalue": [0.001, 0.02, 0.5, 0.04, 0.9, 0.0001, 0.03, 0.8, 0.01, 0.045],
    })
    f = tmp_path / "de.xlsx"
    df.to_excel(f, index=False)
    return f


class TestCliLoad:
    def test_load_reports_type_and_validity(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["load", str(f)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "type: differential_expression" in out
        assert "rows: 10" in out
        assert "valid: True" in out

    def test_load_atac_hint_fails_clearly_without_mapper(self, tmp_path, capsys):
        df = pd.DataFrame({"Region": ["r1"], "LFC": [1.5], "FDR_adj": [0.01]})
        f = tmp_path / "weird_atac.parquet"
        df.to_parquet(f)
        rc = cli.main(["load", str(f), "--type", "atac"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "Missing required ATAC-seq columns" in err
        assert "Region" in err  # 실제 사용 가능한 컬럼도 메시지에 포함


class TestCliFilter:
    def test_filter_writes_table(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        out_path = tmp_path / "filtered.csv"
        rc = cli.main(["filter", str(f), "--adj-pvalue-max", "0.05",
                       "--log2fc-min", "1.0", "--out", str(out_path)])
        assert rc == 0
        assert out_path.exists()
        result = pd.read_csv(out_path)
        assert len(result) == 7
        assert set(result["gene_id"]) == {"G0", "G1", "G3", "G5", "G6", "G8", "G9"}

    def test_filter_without_out_prints_to_stdout(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["filter", str(f), "--adj-pvalue-max", "0.05", "--log2fc-min", "1.0"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "filtered: 7/10 rows" in out
        assert "G0" in out

    def test_filter_defaults_match_filtercriteria_defaults(self, tmp_path):
        # --adj-pvalue-max/--log2fc-min 등을 생략해도 FilterCriteria 기본값과 같아야
        # GUI 기본 필터와 CLI 기본 필터가 어긋나지 않는다.
        from models.data_models import FilterCriteria
        parser = cli.build_parser()
        args = parser.parse_args(["filter", "dummy.xlsx"])
        defaults = FilterCriteria()
        assert args.adj_pvalue_max == defaults.adj_pvalue_max
        assert args.log2fc_min == defaults.log2fc_min
        assert args.regulation == defaults.regulation_direction
        assert args.fdr_max == defaults.fdr_max
        assert args.mg_padj_max == defaults.mg_padj_max
        assert args.mg_basemean_min == defaults.mg_basemean_min

    def test_unrecognized_output_format_raises(self, tmp_path, capsys):
        f = _write_de_xlsx(tmp_path)
        rc = cli.main(["filter", str(f), "--out", str(tmp_path / "out.pdf")])
        err = capsys.readouterr().err
        assert rc == 1
        assert "Unsupported output format" in err


def test_cli_module_never_constructs_qapplication():
    # 서버/HPC 등 display 없는 환경에서도 그대로 동작해야 한다 — 다른 테스트가
    # 먼저 QApplication을 만들어둘 수 있어 런타임 "instance() is None" 체크는
    # 실행 순서에 flaky하므로, 소스 자체에 QApplication 생성 코드가 없다는 걸
    # 정적으로 확인한다.
    import inspect
    source = inspect.getsource(cli)
    assert "QApplication(" not in source
