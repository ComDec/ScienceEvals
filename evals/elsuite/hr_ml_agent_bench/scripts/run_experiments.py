"""
You can do:

```bash
nohup python run_experiments.py > output.log 2>&1 &
```

which will run all experiments in the background and save the output to `output.log`.
"""

import logging
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

N_SEEDS = 1
N_PROCESSES = 10

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

commit_hash = os.popen("git rev-parse HEAD").read().strip()
log_dir = Path(__file__).parent / "logs" / commit_hash
out_dir = Path(__file__).parent / "outputs"

solvers = [
    "hr_ml_agent_bench/baseline/gpt-3.5-turbo-16k",
    "hr_ml_agent_bench/baseline/gpt-4-1106-preview",
    "generation/direct/gpt-3.5-turbo-16k",
    "generation/direct/gpt-4-1106-preview",
    "generation/direct/gemini-pro",
    "generation/direct/llama-2-70b-chat",
    "generation/direct/mixtral-8x7b-instruct",
]

tasks = [
    # v1
    "hr-ml-agent-bench.cifar10",
    "hr-ml-agent-bench.house-price",
    "hr-ml-agent-bench.parkinsons-disease",
    "hr-ml-agent-bench.spaceship-titanic",
    "hr-ml-agent-bench.vectorization",
    "hr-ml-agent-bench.ogbn-arxiv",
    "hr-ml-agent-bench.feedback",
    "hr-ml-agent-bench.imdb",
    # v2
    "hr-ml-agent-bench.ant",
    "hr-ml-agent-bench.bipedal-walker",
    "hr-ml-agent-bench.cartpole",
    "hr-ml-agent-bench.humanoid",
    "hr-ml-agent-bench.inverted-pendulum",
    "hr-ml-agent-bench.pong",
    "hr-ml-agent-bench.pusher",
]

logger.info(f"Writing experiments to {out_dir}...")

if not out_dir.exists():
    out_dir.mkdir()


def run_experiment(solver: str, task: str, seed: int) -> None:
    escaped_solver = solver.replace("/", "_")
    log_file = log_dir / task / escaped_solver / f"{seed}.log"

    if log_file.exists():
        return logger.info(f"Skipping {log_file} since it already exists.")

    if not log_file.parent.exists():
        log_file.parent.mkdir(parents=True)

    subprocess.run(
        f"EVALS_SEQUENTIAL=1 oaieval {solver} {task} --record_path {log_file} --extra_eval_args seed={seed}",
        shell=True,
    )


with ProcessPoolExecutor(max_workers=N_PROCESSES) as executor:
    for seed in range(N_SEEDS):
        for solver in solvers:
            for task in tasks:
                logger.info(
                    f"Running experiment for {solver} on {task} with seed {seed}..."
                )

                executor.submit(run_experiment, solver, task, seed)

logger.info(f"Finished writing experiments to {log_dir}!")
