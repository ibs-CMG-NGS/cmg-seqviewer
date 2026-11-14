"""EnrichmentService: dataset-source orchestration with a fake analyzer."""

import pandas as pd
import pytest

from models.data_models import Dataset, DatasetType
from models.enrichment_models import EnrichmentRequest, ErrorKind
from services.enrichment_service import EnrichmentService
from utils.enrichment_analyzer import EnrichmentError, RawResult


class FakeAnalyzer:
    def __init__(self):
        self.calls = []

    def enrich_ora(
        self,
        genes,
        background=None,
        organism="human",
        libraries=None,
        engine="auto",
        direction="TOTAL",
        population_symbols=None,
        one_sided=False,
    ):
        self.calls.append(
            {
                "genes": list(genes),
                "background": background,
                "organism": organism,
                "libraries": libraries,
                "engine": engine,
                "direction": direction,
                "population_symbols": population_symbols,
                "one_sided": one_sided,
            }
        )
        return [RawResult("TOTAL_BP", "enrichr", pd.DataFrame())], ["W2 test"]

    def to_standard(self, raw_results, organism="human"):
        return (
            pd.DataFrame(
                {
                    "term_id": ["GO:1"],
                    "description": ["Test term"],
                    "fdr": [0.01],
                    "gene_count": [2],
                    "ontology": ["BP"],
                    "direction": ["TOTAL"],
                    "gene_symbols": ["G1/G2"],
                }
            ),
            [],
        )

    def build_metadata(self, request, raw_results, warnings, n_deg, n_bg, organism):
        return {
            "engine_effective": "enrichr",
            "n_deg": n_deg,
            "n_background": n_bg,
            "warnings": list(warnings),
        }


def _de_dataset():
    return Dataset(
        "de",
        DatasetType.DIFFERENTIAL_EXPRESSION,
        dataframe=pd.DataFrame(
            {
                "gene_id": ["G1", "G2", "G3"],
                "symbol": ["G1", "G2", "G3"],
                "log2fc": [2.0, -2.0, 0.1],
                "adj_pvalue": [0.01, 0.02, 0.8],
            }
        ),
    )


def _request(**kwargs):
    base = dict(
        source="dataset",
        dataset_name="de",
        fc_min=1.0,
        fdr_max=0.05,
        direction="TOTAL",
        organism="human",
        libraries=["BP"],
        engine="offline",
    )
    base.update(kwargs)
    return EnrichmentRequest(**base)


def test_run_dataset_orchestrates_analyzer():
    fake = FakeAnalyzer()
    svc = EnrichmentService(analyzer=fake)
    result = svc.run_dataset(_de_dataset(), _request())
    assert result.dataset_name == "Enrichment: de"
    assert result.engine_used == "enrichr"
    assert result.metadata["n_deg"] == 2
    assert result.warnings == ["W2 test"]
    assert len(result.dataframe) == 1
    assert fake.calls[0]["genes"] == ["G1", "G2"]
    assert fake.calls[0]["population_symbols"] == ["G1", "G2", "G3"]


def test_run_dataset_no_genes():
    svc = EnrichmentService(analyzer=FakeAnalyzer())
    with pytest.raises(EnrichmentError) as exc:
        svc.run_dataset(_de_dataset(), _request(fc_min=100.0))
    assert exc.value.kind == ErrorKind.NO_INPUT_GENES


def test_run_dataset_rejects_non_dataset_source():
    svc = EnrichmentService(analyzer=FakeAnalyzer())
    with pytest.raises(ValueError, match="source='dataset'"):
        svc.run_dataset(_de_dataset(), _request(source="paste"))
