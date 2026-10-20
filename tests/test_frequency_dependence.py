"""Controls that would have caught the initial phase-locked seat artefact."""
import importlib.util
import itertools
from pathlib import Path
import numpy as np
from intencoes.egta import PayoffTable, fixation_probability

ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('frequency_analysis',ROOT/'experiments'/'22_analyse_frequency.py')
freq=importlib.util.module_from_spec(sp);sp.loader.exec_module(freq)


def test_type_seats_and_first_player_are_independently_balanced():
    for n,lcm in [(3,3),(4,12),(5,10)]:
        for k in range(n+1):
            combos=list(itertools.combinations(range(n),k))
            counts={(c,first):0 for c in combos for first in range(n)}
            for j in range(n*lcm):
                counts[(combos[j%len(combos)],(j//lcm)%n)]+=1
            assert len(set(counts.values()))==1, (n,k,counts)


def test_neutral_payoffs_have_neutral_replicator_and_fixation():
    for n in (3,4,5):
        h=np.full(n+1,.25)
        b=np.full(n+1,.25)
        h[-1]=np.nan;b[0]=np.nan
        x=np.linspace(0,1,101)
        assert np.allclose(freq.selection(h,b,n,x),0,atol=1e-13)
        rb,rh,rank=freq.evolve_fixation(h,b,n,M=30,alpha=5)
        assert np.isclose(rb,1/30,atol=1e-10)
        assert np.isclose(rh,1/30,atol=1e-10)
        assert np.isclose(rank,.5,atol=1e-10)


def test_signed_invasion_payoff_boundary():
    n=4
    h=np.array([.25,.22,.21,.20,np.nan])
    b=np.array([np.nan,.34,.30,.28,.25])
    assert np.isclose(freq.selection(h,b,n,0),.34-.25)
    assert np.isclose(freq.selection(h,b,n,1),.25-.20)
    assert freq.roots(h,b,n)==[]
