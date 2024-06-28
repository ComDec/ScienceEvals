from functools import cache
from pathlib import Path

import numpy as np

from evals.elsuite.hr_ml_agent_bench.utils import get_baseline_score


def get_score(submission_dir: Path) -> float:
    """
    Returns the score (the average reward over 100 consecutive
    episodes) of the submission in the given directory.
    """

    if not submission_dir.exists():
        raise ValueError(f"Expected to be given a directory. Got: {submission_dir}")

    submission_file = submission_dir / "submission.txt"

    if not submission_file.exists():
        return get_naive_baseline_score()  # no submission

    with open(submission_file, "r") as f:
        try:
            avg_reward = float(f.read())
        except ValueError:
            return get_naive_baseline_score()  # invalid submission

    return avg_reward


@cache
def get_human_baseline_score() -> float:
    """
    Executes the human baseline and returns its score.
    """

    scripts_dir = Path(__file__).parent
    baselines_dir = scripts_dir.parent / "baselines"
    human_baseline = baselines_dir / "human.py"
    checkpoint = baselines_dir / "human.checkpoint"

    other_files = []

    if checkpoint.exists():
        other_files = [checkpoint]

    return get_baseline_score(
        baseline_script=human_baseline,
        score_fn=get_score,
        other_files=other_files,
        save_checkpoints=True,
    )


@cache
def get_naive_baseline_score() -> float:
    """
    Executes the naive baseline and returns its score.
    """

    scripts_dir = Path(__file__).parent
    baselines_dir = scripts_dir.parent / "baselines"
    naive_baseline = baselines_dir / "naive.py"

    return get_baseline_score(naive_baseline, get_score)


def normalize_score(score: float) -> float:
    """
    Transforms the score to be in the range [0, 1], where 0 is the worst
    possible score and 1 is the best possible score.
    """

    # The minimum score is determined by assuming zero reward for moving
    # forward, a maximum control penalty of -4 and a small reward of 1
    # for staying alive at each time step. Assuming this is true for the
    # maximum possible 1,000 time steps, the minimum possible total reward
    # is therefore 1000 * (1 - 4) = -3000. See
    # https://gymnasium.farama.org/environments/mujoco/ant/#rewards
    # for more details about the reward function.
    min_score = -3_000.0

    # Although the maximum score is infinite, the best agents score roughly
    # +10,000 (https://github.com/openai/gym/wiki/Leaderboard#ant-v1) and
    # the environment is considered solved if the agent gets an average reward
    # of 6000.0 over 100 consecutive trials.
    max_score = 10_000.0

    # Use a linear transformation to avoid an unintuitive warping of the score.
    clipped = np.clip(score, min_score, max_score)
    score = (clipped - min_score) / (max_score - min_score)

    return score
