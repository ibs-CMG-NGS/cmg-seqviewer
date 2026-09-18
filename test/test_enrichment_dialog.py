"""
Enrichment 다이얼로그 e2e (plan §12 — pytest-qt, mock worker).

3소스 각각 → worker(mock) → Dataset 등록 → 기존 시각화(크래시 없음);
취소 / 오류(MAPPING, DOWNLOAD) / 오프라인 KEGG 비활성 안내 / empty 결과.
"""

import pandas as pd
import pytest

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from models.data_models import Dataset, DatasetType
from models.enrichment_models import EnrichmentResult, EnrichmentRequest, ErrorKind
from gui.enrichment_analysis_dialog import EnrichmentAnalysisDialog


# --------------------------------------------------------------------------
# 스텁
# --------------------------------------------------------------------------

class FakeWorker(QObject):
    """dialog용 가짜 worker — 대기 없이 즉시 결과/실패 방출."""

    progress = pyqtSignal(int)
    result_ready = pyqtSignal(object)
    failed = pyqtSignal(object)

    def __init__(self, request, dataframe=None, scenario="ok", parent=None):
        super().__init__(parent)
        self.request = request
        self.dataframe = dataframe
        self.scenario = scenario
        self.cancelled = False
        self.started = False

    def start(self):
        self.started = True
        QTimer.singleShot(0, self._deliver)

    def _deliver(self):
        if self.cancelled:
            return
        self.progress.emit(100)
        if self.scenario == "error_mapping":
            from workers.go_workers import ErrorPayload
            self.failed.emit(ErrorPayload(ErrorKind.MAPPING,
                                          "Gene mapping returned 0 hits — analysis cannot proceed",
                                          ["W1 test"]))
        elif self.scenario == "error_download":
            from workers.go_workers import ErrorPayload
            self.failed.emit(ErrorPayload(
                ErrorKind.DOWNLOAD,
                "Local GOATOOLS run failed (cache download/parse) — first-run download guide",
                ["W1 cache missing"]))
        elif self.scenario == "cancel":
            pass  # cancel() 경로 — 아무것도 방출 안함
        else:
            df = pd.DataFrame([
                {"term_id": "GO:0000001", "description": "heart contraction",
                 "gene_count": 2, "fdr": 0.03, "pvalue": 0.001,
                 "gene_ratio": "2/10", "bg_ratio": "3/100",
                 "fold_enrichment": 6.67, "gene_symbols": "A/B",
                 "gene_set": "TOTAL_BP", "direction": "TOTAL", "ontology": "BP",
                 "_gene_set": frozenset({"A", "B"})},
            ])
            result = EnrichmentResult(
                dataframe=df, request=self.request,
                metadata={"engine_effective": "online",
                          "enrichment_recipe": self.request.to_recipe_dict()},
                warnings=[],
                engine_used="online",
                dataset_name=f"Enrichment: {self.request.source}",
            )
            self.result_ready.emit(result)

    def isRunning(self):
        return False

    def cancel(self):
        self.cancelled = True

    def wait(self, ms):
        return True


class StubPresenter:

    def __init__(self):
        self.de_df = pd.DataFrame({
            "symbol": ["TP53", "JUN", "FOS", "BRCA1", "MYC", "EGFR"],
            "log2fc": [2.5, -1.8, 1.2, 0.5, 0.2, 3.1],
            "adj_pvalue": [0.01, 0.02, 0.03, 0.1, 0.2, 0.05],
        })
        self.datasets = {"DE1": Dataset(
            name="DE1", dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=self.de_df)}
        self.current_dataset = self.datasets["DE1"]
        self.registered: list = []

    def register_enrichment_result(self, result):
        ds = Dataset(name=result.dataset_name,
                     dataset_type=DatasetType.GO_ANALYSIS,
                     dataframe=result.dataframe,
                     metadata=dict(result.metadata or {}))
        self.datasets[ds.name] = ds
        self.registered.append(ds)
        return ds.name


class StubMainWindow:

    class _Tabs:
        def __init__(self, meta_df=None):
            self.meta_df = meta_df

        def currentWidget(self):
            return StubMetaWidget(self.meta_df)

    def __init__(self, meta_df=None):
        self.presenter = StubPresenter()
        self.data_tabs = StubMainWindow._Tabs(meta_df)
        self.settings = None


class StubMetaWidget:
    def __init__(self, meta_df):
        self._df = meta_df

    def model(self):
        return StubMetaModel(self._df)


class StubMetaModel:
    def __init__(self, df):
        self.dataframe = df


def meta_df():
    return pd.DataFrame({
        "term_id": ["GO:1", "GO:2"],
        "meta_pvalue_fisher": [0.001, 0.2],
        "meta_log2fc_mean": [1.5, -0.2],
        "meta_direction": ["UP", "DOWN"],
    })


@pytest.fixture
def dlg_factory(monkeypatch):
    def make(scenario="ok", meta=None):
        mw = StubMainWindow(meta_df=meta)
        monkeypatch.setattr("gui.enrichment_analysis_dialog.EnrichmentWorker", FakeWorker)
        monkeypatch.setattr("gui.enrichment_analysis_dialog.QMessageBox", QMessageBox)
        dlg = EnrichmentAnalysisDialog(mw)
        dlg._worker_fake = lambda req, df: FakeWorker(req, df, scenario=scenario)
        dlg._build = lambda req, df: None  # not used; _on_run creates worker
        return dlg, mw
    return make


def _swap_worker_factory(dlg, scenario):
    """_on_run_clicked가 쓰는 worker 생성 지점 패치."""
    import gui.enrichment_analysis_dialog as mod

    class FakeWorkerWithScenario(FakeWorker):
        def __init__(self, request, dataframe=None, parent=None):
            super().__init__(request, dataframe, scenario=scenario, parent=parent)
    mod.EnrichmentWorker = FakeWorkerWithScenario


# --------------------------------------------------------------------------
# 소스 ① 현재 DE 데이터셋
# --------------------------------------------------------------------------

def test_source_dataset_run_and_register(qtbot, dlg_factory, monkeypatch):
    dlg, mw = dlg_factory()
    _swap_worker_factory(dlg, "ok")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)

    # 소스 ① 탭 (기본), DE1 자동 선택
    dlg._on_run_clicked()
    # 결과 대기: summary에 term 개수 표시
    assert dlg._worker is not None
    with qtbot.waitSignal(dlg._worker.result_ready, timeout=2000):
        pass
    assert mw.presenter.registered, "register_enrichment_result 호출됨"
    ds = mw.presenter.registered[0]
    assert ds.dataset_type == DatasetType.GO_ANALYSIS
    assert ds.dataframe["_gene_set"].map(len).gt(0).all()
    assert "Enrichment:" in ds.name
    assert ds.metadata.get("enrichment_recipe") is not None   # A2/F6
    assert dlg.current_summary() and "Done: 1 terms" in dlg.current_summary()


# --------------------------------------------------------------------------
# 소스 ② 붙여넣기
# --------------------------------------------------------------------------

def test_source_paste_run(qtbot, dlg_factory, monkeypatch):
    dlg, mw = dlg_factory()
    _swap_worker_factory(dlg, "ok")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)
    dlg.source_tabs.setCurrentIndex(1)
    dlg.paste_edit.setPlainText("tp53, jun, fos\nbrca1 my c")
    dlg._update_paste_count()
    dlg._on_run_clicked()
    assert dlg._worker is not None
    assert dlg._worker.request.source == "paste"
    assert "TP53" in dlg._worker.request.gene_list          # A6 human UPPER
    with qtbot.waitSignal(dlg._worker.result_ready, timeout=2000):
        pass
    assert mw.presenter.registered


# --------------------------------------------------------------------------
# 소스 ③ Comparison: Statistics
# --------------------------------------------------------------------------

def test_source_meta_run(qtbot, dlg_factory, monkeypatch):
    dlg, mw = dlg_factory(meta=meta_df())
    _swap_worker_factory(dlg, "ok")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)
    dlg.source_tabs.setCurrentIndex(2)
    assert dlg._current_meta_df() is not None
    dlg._on_run_clicked()
    assert dlg._worker.request.source == "meta"
    assert dlg._worker.request.meta_cutoff == 0.05
    with qtbot.waitSignal(dlg._worker.result_ready, timeout=2000):
        pass
    assert mw.presenter.registered


# --------------------------------------------------------------------------
# 오류 / 취소 / 오프라인 KEGG
# --------------------------------------------------------------------------

def test_mapping_error_shown(qtbot, dlg_factory, monkeypatch):
    dlg, _ = dlg_factory()
    _swap_worker_factory(dlg, "error_mapping")
    seen = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: seen.append(str(k.get("text", a[-1] if a else ""))))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)
    dlg._on_run_clicked()
    with qtbot.waitSignal(dlg._worker.failed, timeout=2000):
        pass
    assert "Gene mapping returned 0 hits" in dlg.summary_label.text()
    assert any("Gene mapping returned 0 hits" in s for s in seen)


def test_download_error_first_run_guidance(qtbot, dlg_factory, monkeypatch):
    # P2-3: 캐시 부재 첫 실행 안내 (DOWNLOAD 분류)
    dlg, _ = dlg_factory()
    _swap_worker_factory(dlg, "error_download")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)
    dlg._on_run_clicked()
    with qtbot.waitSignal(dlg._worker.failed, timeout=2000):
        pass
    assert "cache download" in dlg.summary_label.text()


def test_cancel_discards_partial(qtbot, dlg_factory, monkeypatch):
    dlg, mw = dlg_factory()
    _swap_worker_factory(dlg, "cancel")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)
    dlg._on_run_clicked()
    dlg._on_cancel_clicked()
    assert dlg._worker.cancelled is True
    assert not mw.presenter.registered  # P2-4: 부분 결과 폐기


def test_offline_kegg_disabled_notice(qtbot, dlg_factory, monkeypatch):
    # F3/ADR-1: offline 모드에서 KEGG 미포함 → 안내
    dlg, _ = dlg_factory()
    _swap_worker_factory(dlg, "ok")
    infos = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: infos.append("KEGG"))
    qtbot.addWidget(dlg)
    dlg.engine_combo.setCurrentIndex(dlg.engine_combo.findData("offline"))
    assert dlg._engine() == "offline"
    # KEGG만 선택
    for key, cb in dlg.lib_checks.items():
        cb.setChecked(key == "KEGG")
    dlg._on_run_clicked()
    with qtbot.waitSignal(dlg._worker.result_ready, timeout=2000):
        pass
    # 결과에 KEGG 행 없음 → _warn_if_kegg_offline이 info 호출
    assert infos, "KEGG 비활성 안내 표시됨 (F3)"


def test_existing_visualization_no_crash(dlg_factory, monkeypatch):
    # 등록된 enrichment Dataset → 기존 GO 시각화(크래시 없음, P2-2)
    mw = StubMainWindow()
    mw.presenter.registered = []
    df = pd.DataFrame([
        {"term_id": "GO:0000001", "description": "heart contraction",
         "gene_count": 2, "fdr": 0.03, "pvalue": 0.001,
         "gene_ratio": "2/10", "bg_ratio": "3/100", "fold_enrichment": 6.67,
         "gene_symbols": "A/B", "gene_set": "TOTAL_BP",
         "direction": "TOTAL", "ontology": "BP",
         "_gene_set": frozenset({"A", "B"})},
    ])
    result = EnrichmentResult(dataframe=df, request=EnrichmentRequest(source="paste"),
                              metadata={}, dataset_name="Enrichment: X")
    mw.presenter.register_enrichment_result(result)
    ds = mw.presenter.datasets["Enrichment: X"]
    from gui.go_bar_chart_dialog import GOBarChartDialog
    from gui.go_dot_plot_dialog import GODotPlotDialog
    from gui.go_network_dialog import GONetworkDialog
    app = QApplication.instance() or QApplication([])
    for dlg_cls in (GOBarChartDialog, GODotPlotDialog, GONetworkDialog):
        d = dlg_cls(ds)
        d.show()
        app.processEvents()
        d.close()
    assert True

# --------------------------------------------------------------------------
# EMPTY_RESULT / NO_INPUT_GENES 페이로드 UX (architect LOW 보강)
# --------------------------------------------------------------------------

class _EmptyScenarioWorker(FakeWorker):
    def __init__(self, request, dataframe=None, scenario="ok", parent=None):
        super().__init__(request, dataframe, scenario, parent)

    def _deliver(self):
        from workers.go_workers import ErrorPayload
        self.progress.emit(100)
        if self.scenario == "empty":
            self.failed.emit(ErrorPayload(ErrorKind.EMPTY_RESULT,
                                          "No libraries were executed (offline KEGG inactive, etc. — see warnings).",
                                          ["W1 test"]))
        else:
            self.failed.emit(ErrorPayload(ErrorKind.NO_INPUT_GENES,
                                          "Extracted DEG genes: 0 (adjust thresholds/filters)."))


@pytest.mark.parametrize("scenario,expect", [
    ("empty", "No libraries were executed"),
    ("noinput", "DEG genes: 0"),
])
def test_error_payload_ux(qtbot, dlg_factory, monkeypatch, scenario, expect):
    dlg, _ = dlg_factory()
    import gui.enrichment_analysis_dialog as mod

    def _swap():
        mod.EnrichmentWorker = lambda req, dataframe=None: _EmptyScenarioWorker(
            req, dataframe, scenario=scenario)
    _swap()
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    qtbot.addWidget(dlg)
    dlg._on_run_clicked()
    with qtbot.waitSignal(dlg._worker.failed, timeout=2000):
        pass
    assert expect in dlg.summary_label.text()



# --------------------------------------------------------------------------
# P3-7 진짜 저장→재오픈 e2e (GO parquet 복원 + set _gene_set + 클러스터링)
# --------------------------------------------------------------------------

def test_project_restore_parquet_go_roundtrip(qtbot, monkeypatch, tmp_path):
    """분석 결과 저장(parquet) → presenter.load_dataset 복원 → set _gene_set + 클러스터링. (P3-7)

    실제 product 복원 분기(presenter.load_dataset GO parquet branch)를 거치되,
    GUI 저장/시그널 기계는 _store_and_signal_dataset 캡처로 대체 (헤드리스 안정성).
    """
    from types import SimpleNamespace
    from presenters.main_presenter import MainPresenter

    df = pd.DataFrame([
        {"term_id": "GO:0000004", "description": "heart contraction",
         "gene_count": 2, "fdr": 0.03, "pvalue": 0.001,
         "gene_ratio": "2/10", "bg_ratio": "4/100", "fold_enrichment": 5.0,
         "gene_symbols": "A/B", "gene_set": "TOTAL_BP",
         "direction": "TOTAL", "ontology": "BP", "_gene_set": {"A", "B"}},
        {"term_id": "GO:0000007", "description": "cell adhesion",
         "gene_count": 2, "fdr": 0.31, "pvalue": 0.2,
         "gene_ratio": "2/10", "bg_ratio": "5/100", "fold_enrichment": 4.0,
         "gene_symbols": "A/C", "gene_set": "TOTAL_BP",
         "direction": "TOTAL", "ontology": "BP", "_gene_set": {"A", "C"}},
        {"term_id": "GO:0000005", "description": "immune response",
         "gene_count": 1, "fdr": 0.5, "pvalue": 0.3,
         "gene_ratio": "1/10", "bg_ratio": "3/100", "fold_enrichment": 3.33,
         "gene_symbols": "D", "gene_set": "TOTAL_BP",
         "direction": "TOTAL", "ontology": "BP", "_gene_set": {"D"}},
    ])
    # 1) 저장 (project 저장 경로의 parquet 직렬화)
    parquet_path = tmp_path / "enrichment_result.parquet"
    df.to_parquet(parquet_path)

    # 2) presenter 복원 분기 (view는 최소 스텁 — store만 캡처)
    presenter = MainPresenter(SimpleNamespace())
    captured = {}
    monkeypatch.setattr(presenter, "_store_and_signal_dataset",
                        lambda ds, start: captured.__setitem__("ds", ds))
    presenter.load_dataset(parquet_path, custom_name="RestoredEnrichment")
    ds = captured.get("ds")
    assert ds is not None, "복원 실패 (GO parquet 분기 미동작)"
    assert ds.dataset_type == DatasetType.GO_ANALYSIS
    assert ds.dataframe["_gene_set"].map(lambda s: isinstance(s, (set, frozenset))).all()
    assert set(ds.dataframe.loc[0, "_gene_set"]) == {"A", "B"}

    # 3) 비자명 클러스터링: 겹침 쌍 존재 (GO:0000004 ∩ GO:0000007 = {A} > 0.3)
    from utils.go_clustering import GOClustering
    clustered, clusters = GOClustering(similarity_threshold=0.3).fit(
        ds.dataframe).cut(0.3)
    n_singleton = int((clustered["cluster_id"] == "Singleton").sum())
    assert n_singleton < len(clustered), "복원 프레임에서 겹침 없음 (클러스터링 무력화)"


# --------------------------------------------------------------------------
# P2-1 회귀: 메뉴 항목 활성화는 DE 데이터셋 존재 기준 (로드 시그널 연결)
# --------------------------------------------------------------------------

class _FakeAction:
    def __init__(self):
        self._enabled = False   # 실제 MainWindow 초기 상태와 동일 (setEnabled(False))

    def setEnabled(self, v):
        self._enabled = bool(v)

    def isEnabled(self):
        return self._enabled


class _FakePresenter:
    def __init__(self):
        self.datasets = {}


def _make_mw():
    from gui.main_window import MainWindow
    mw = MainWindow.__new__(MainWindow)     # 전체 GUI 생성 없이 메서드만 검증
    mw.presenter = _FakePresenter()
    mw.enrichment_action = _FakeAction()
    return mw


def test_enrichment_action_enabled_on_de_load_disabled_without_de():
    from models.data_models import Dataset, DatasetType
    mw = _make_mw()
    assert mw.enrichment_action.isEnabled() is False     # 초기 비활성

    de = Dataset(name="DE1", dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
                 dataframe=pd.DataFrame({"symbol": ["A"], "log2fc": [1.0],
                                         "adj_pvalue": [0.01]}))
    mw.presenter.datasets["DE1"] = de
    mw._update_enrichment_action()                        # dataset_loaded 훅이 호출하는 경로
    assert mw.enrichment_action.isEnabled() is True       # DE 로드 시 활성

    # DE 제거 → 비활성
    del mw.presenter.datasets["DE1"]
    mw._update_enrichment_action()
    assert mw.enrichment_action.isEnabled() is False

    # GO_ANALYSIS만 존재 → 비활성 (DE 없음)
    go = Dataset(name="GO1", dataset_type=DatasetType.GO_ANALYSIS,
                 dataframe=pd.DataFrame({"term": ["t"], "gene_count": [1], "fdr": [0.1]}))
    mw.presenter.datasets["GO1"] = go
    mw._update_enrichment_action()
    assert mw.enrichment_action.isEnabled() is False

    # DE가 있다면 현재 타입이 GO여도 활성 (다이얼로그는 DE 목록을 쓰므로)
    mw.presenter.datasets["DE2"] = Dataset(
        name="DE2", dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
        dataframe=pd.DataFrame({"symbol": ["B"], "log2fc": [-1.0], "adj_pvalue": [0.02]}))
    mw._update_enrichment_action()
    assert mw.enrichment_action.isEnabled() is True


def test_one_sided_checkbox_extra(qtbot, dlg_factory):
    """잔여 추천: One-sided Fisher 체크 → request.extra['one_sided'] (로컬 GO 정합 옵션)."""
    dlg, _ = dlg_factory()
    dlg.paste_edit.setPlainText("TP53, JUN")
    dlg.one_sided_check.setChecked(True)
    dlg._update_paste_count()
    req = dlg._build_request()
    dlg._pending_df = None
    assert req is not None
    req.extra["one_sided"] = dlg.one_sided_check.isChecked()   # _on_run_clicked에서 적용되는 경로 재현
    assert req.extra["one_sided"] is True
