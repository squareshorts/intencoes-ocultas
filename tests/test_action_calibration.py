"""Action-specific block predictor: public information, challenge mechanics, splits."""
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from intencoes.agents import HeuristicAgent, Params
from intencoes.engine import Game
from intencoes.rules import ActionType, Character, RuleConfig

ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('action_calibration_test_support',ROOT/'experiments'/'action_calibration_common.py')
ac=importlib.util.module_from_spec(sp);sys.modules[sp.name]=ac;sp.loader.exec_module(ac)


def game_view(seed=12,n=4):
    g=Game([HeuristicAgent(seed=i) for i in range(n)],RuleConfig(n_players=n),seed=seed)
    return g,g.view(0)


def test_provably_false_guardian_claim_always_challenged():
    g,v=game_view(n=3)
    # Set target with 1 hidden card, actor holding both remaining Guards,
    # with final one face-up: public evidence excludes truth.
    from intencoes.engine import View
    R,C,S,G,E=tuple(Character)
    v=View(me=0,hand=(G,G),coins=(3,3,3),hidden_counts=(2,1,2),
           revealed=((),(G,),()),deck_size=9,treasury=45,turn=0,
           config=RuleConfig(n_players=3))
    a=HeuristicAgent(Params(block_prediction='opponent_challenge'))
    assert a._fake_block_survival(v,1,ActionType.ASSASSINATE,1,G)==0


def test_fake_challenge_survival_tracks_opponent_card_counting_not_truth():
    _,v=game_view(n=4)
    a=HeuristicAgent(Params(block_prediction='opponent_challenge'))
    for j in (1,2,3):
        for action in (ActionType.STEAL,ActionType.ASSASSINATE):
            for ch in (Character.GUARDIAO,):
                p=a._fake_block_survival(v,j,action,1,ch)
                assert 0 <= p <= 1
    # A strict challenger prior cannot increase false-block survival.
    b=HeuristicAgent(replace(a.p,opponent_challenge_threshold=0.9))
    p=a._fake_block_survival(v,1,ActionType.ASSASSINATE,1,Character.GUARDIAO)
    q=b._fake_block_survival(v,1,ActionType.ASSASSINATE,1,Character.GUARDIAO)
    assert q <= p


def test_own_cards_change_mechanistic_assessment_but_hidden_opponents_do_not():
    g,v=game_view(n=4)
    a=HeuristicAgent(Params(block_prediction='opponent_challenge'))
    p=a.predicted_block_probability(v,ActionType.ASSASSINATE,1)
    # Hidden deck truth is not accessible through a pre-offer View.
    g.players[1].hand[0],g.players[2].hand[0] = g.players[2].hand[0],g.players[1].hand[0]
    assert a.predicted_block_probability(g.view(0),ActionType.ASSASSINATE,1)==pytest.approx(p)
    assert not hasattr(v,'players') and not hasattr(v,'has_blocker')


def test_action_offsets_are_local_and_monotone():
    _,v=game_view(n=4)
    base=HeuristicAgent(Params(block_prediction='opponent_action'))
    q=base._p_blocked(v,ActionType.STEAL,1)
    for action in (ActionType.STEAL,ActionType.ASSASSINATE):
        off= [0.,0.,0.,0.]
        idx=(0 if action==ActionType.STEAL else 2) + (v.hidden_counts[1]==1)
        off[idx]=1.2
        a=HeuristicAgent(Params(block_prediction='opponent_action',action_block_offsets=tuple(off)))
        b=HeuristicAgent(Params(block_prediction='opponent_action'))
        assert a._p_blocked(v,action,1) >= b._p_blocked(v,action,1)
        assert b._p_blocked(v,action,1)==pytest.approx(base._p_blocked(v,action,1))
    assert 0 <= q <= 1


def test_pre_offer_snapshots_and_experiment_seed_isolation():
    rows,stages=ac.stages_for_games(3,'mixed','opponent_action',(0.1,-0.1,0.2,-0.2),3_300_000,30)
    preds=ac.predict_rows(stages,(0.1,-0.1,0.2,-0.2))
    assert len(rows)==30
    assert len(preds)==sum(r['block_stages'] for r in rows)
    assert all(0<=r[m]<=1 for r in preds for m in ac.MODELS)
    assert ac.pg.PRIOR['opponent_pool_strength']==2.0


def test_fitted_calibration_is_deterministic_from_training_snapshots():
    _,stages=ac.stages_for_games(4,'mixed','opponent',(0.,)*4,1_100_000,70)
    x=ac.fit_offsets(stages,10.)
    y=ac.fit_offsets(list(reversed(stages)),10.)
    assert x==pytest.approx(y,abs=1e-10)
    assert all(-2.5<=z<=2.5 for z in x)


def test_frozen_train_and_validation_seeds_disjoint():
    spec=importlib.util.spec_from_file_location('fit_seeds',ROOT/'experiments'/'13_fit_action_calibration.py')
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    train=set.union(*(set(range(x,x+10_000)) for x in m.TRAIN_START.values()))
    screen=set.union(*(set(range(x,x+10_000)) for x in m.SCREEN_START.values()))
    validate=[set(range(3_000_000+n*100_000+(20_000 if pop else 0),
                       3_000_000+n*100_000+(20_000 if pop else 0)+10_000))
                 for n in (3,4,5) for pop in (0,1)]
    holdout=set.union(*validate)
    assert not train.intersection(screen|holdout)
    assert not screen.intersection(holdout)


def test_table_size_offsets_are_explicit_public_action_features():
    for n in (3,4,5):
        g,v=game_view(seed=19,n=n)
        zero=HeuristicAgent(Params(block_prediction='opponent_action'))
        for action in (ActionType.STEAL,ActionType.ASSASSINATE):
            j=(n-3)*2 + (action==ActionType.ASSASSINATE)
            effect=[0.]*6
            effect[j]=0.5
            changed=HeuristicAgent(Params(block_prediction='opponent_action',
                                          size_block_offsets=tuple(effect)))
            p=zero._p_blocked(v,action,1)
            q=changed._p_blocked(v,action,1)
            assert q>=p
            assert 0<=q<=1
        # The added feature reads n_players; it does not read hidden opponent hands.
        pred=changed._p_blocked(v,ActionType.ASSASSINATE,1)
        g.players[1].hand[0],g.players[2].hand[0] = g.players[2].hand[0],g.players[1].hand[0]
        assert changed._p_blocked(g.view(0),ActionType.ASSASSINATE,1)==pytest.approx(pred)


def test_second_round_final_holdout_seeds_are_disjoint_from_development_and_first_holdout():
    sp=importlib.util.spec_from_file_location('sizefit_seed_test',ROOT/'experiments'/'15_fit_size_calibration.py')
    m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
    for n in (3,4,5):
        for pop in ('mixed','shifted'):
            train=m.start(m.TRAIN_BASE,n,pop)
            screen=m.start(m.SCREEN_BASE,n,pop)
            final=m.start(m.FINAL_BASE,n,pop)
            assert train+1100<screen
            assert screen+500<final
            assert 3_520_000<train
