import pytest

from cns_scientometrics.ncbi import eutils_esearch


@pytest.mark.network
def test_esearch_finds_bmc_2015(tmp_path):
    ids = eutils_esearch("pmc", '"BMC Neurosci"[Journal] AND 2015[PDAT]', 600, tmp_path)
    assert len(ids) > 100  # CNS*2015 supplement alone is ~420 abstracts
