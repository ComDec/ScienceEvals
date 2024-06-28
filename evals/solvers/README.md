# Solvers (Beta)

> *Important: The Solvers framework is still in beta, so new dataset submissions that rely on eval templates should still use the original Eval classes with CompletionFn instead of SolverEval with Solvers.*

When building evaluations, it is helpful to make a distinction between the Evaluation logic ('what is the task and how is it graded'), and ways that actors attempt to Solve the evaluation ('what is the strategy they take, with what tools, etc'). These often get conflated, with LLM evaluations hardcoding assumptions about how the LLM should attempt to solve the problem. To provide a better separation of concerns, we introduce the new `SolverEval` class to build evaluations and the `Solver` class to solve it.

Running a Solver against a SolverEval works in exactly the same way as running a CompletionFn against an Eval:
```bash
oaieval <SOLVER> <SOLVEREVAL>
```

## What are Solvers?
Solvers are an abstraction layer for the entity that "solves" an eval. Often, we think of this as just the model that generates a text response when given a prompt. However, “How good is GPT-4 on this eval?” is an underspecified question. Interacting with a model requires scaffolding (prompting, tooling, etc.), and scaffolding can drastically change the model’s behavior; so any claims about performance should specify the entire system (model + scaffolding) being evaluated.

In the context of evals, we call the systems that are used to solve evals “Solvers”.

> **Relationship with [Completion Functions](/docs/completion-fns.md):** Completion Functions was our first iteration of this abstraction, reasonably assuming that the "solver" would be a function that takes a prompt and returns a completion. However, we've found that passing a prompt to the CompletionFn encourages eval designers to write prompts that often privileges a particular kind of Solver over others. e.g. If developing with ChatCompletion models, the eval tends to bake-in prompts that work best for ChatCompletion models. In moving from Completion Functions to Solvers, we are making a deliberate choice to write Solver-agnostic evals, and delegating any model-specific or strategy-specific code to the Solver.

## Interface between Eval and Solver

Careful design of the interface between the eval and the Solver is central to successful implementation of the Solver abstraction. On each turn, the eval provides a `TaskState` object to the Solver, and the Solver returns a `SolverResult` object to the Eval. The Eval then uses the `SolverResult` to update its internal state, and the process repeats until the Eval is complete.

<img width="1180" alt="image" src="https://github.com/openai/evals/assets/7796965/0e9c37d7-ed9e-47d4-bb9c-6bf909c19927">

The `TaskState` should contain all the information that a Solver needs to provide a response to the Eval environment.
```python
@dataclass
class TaskState:
    task_description: str
    messages: list[Message] = field(default_factory=list)
    current_state: Any = None
```
- The `task_description` describes the overall task instructions, including the expected response format. In general, this should be fixed across all samples of the eval.
- The list of `messages` in the conversation so far. For example, it is often useful to include an input sample as the first message. Any previous interactions should also be included here.
- Any relevant `current_state` variables that should be passed to the Solver. While the current state of the eval should be apparent from previous messages, it is sometimes useful to include explicit state information here (e.g. the current game score or number of turns remaining) for easy access by the Solver without having to parse the messages.

On the other hand, the `SolverResult` is simply the response from the Solver to the Eval.
```python
class SolverResult:
    def __init__(self, output: str, **metadata):
        self._output = output
        self._metadata = metadata
```
- The `output` is the response from the Solver to the Eval, which will be parsed by the Eval. We currently assume that this will always be a string.
- `metadata` is an optional field that may be used to pass additional information from the Solver to the Eval, e.g. for logging purposes.

> If you're familiar with CompletionFns, you can think of `TaskState` as a generalized version of the `prompt` and `SolverResult` as the Solver equivalent for `CompletionResult`.

## Which evals can I use with Solvers?

[`SolverEval`](/evals/eval.py#L168) is our new class for building evals that are compatible with Solvers. It is a subclass of [`Eval`](/evals/eval.py#L46), with a few small differences:
- It expects only a single Solver as input rather than a list of CompletionFns. This clarifies that only one Solver can be evaluated at once; evals may still use additional models e.g. for model-model interactions, but additional models belong to the environment and should be created by the eval itself rather than passed in as input.
- Each call to `SolverEval.eval_sample()` is provided a different copy of the Solver. This allows Solvers to be stateful (e.g. have a memory) without interfering with other samples.
- Most of our custom code evals in [`evals/elsuite/`](/evals/elsuite/) are of this `SolverEval` type.

> **Backward compatibility:** Older `Eval`-based evals work with Solvers, albeit with some limitations, e.g. `Eval` classes are not compatible with stateful Solvers since `Evals` use the same solver on all samples. See [here](/evals/completion_fns/solver_completion_fn.py) for how this works.

## Working with Solvers

The Solvers framework is still in beta, and we make this available largely for power-users who want to experiment with the Solver abstraction. If you simply wish to contribute new dataset submissions that rely on existing eval templates, you should still use the original Eval classes with CompletionFn instead of SolverEval with Solvers.

If you already know how to write an [`Eval`](/evals/eval.py#L46) class (see [Eval docs](/docs/custom-eval.md)), writing a [`SolverEval`](/evals/eval.py#L168) is very similar. See the following examples of SolverEval classes:
- [evals/elsuite/basic/match_with_solvers.py](/evals/elsuite/basic/match_with_solvers.py): A simple eval template for multiple-choice QA tasks.
- [evals/elsuite/twenty_questions/eval.py](/evals/elsuite/twenty_questions/eval.py): A multi-turn eval where the solver attempts to guess a word in 20 questions.
- [evals/elsuite/identifying_variables/eval.py](/evals/elsuite/identifying_variables/eval.py): An eval with multi-stage task setup and complex output grading.
- [evals/elsuite/bugged_tools/eval.py](/evals/elsuite/bugged_tools/eval.py): A multi-turn eval where the solver interacts with various tools to solve a task.

Likewise, writing Solvers is similar to writing CompletionFns, and follows the same process as documented [here](/docs/completion-fns.md). You can see examples of our currently implemented Solvers in [`evals/solvers/`](/evals/solvers); please see [`evals/registry/solvers/defaults.yaml`](/evals/registry/solvers/defaults.yaml) for Solvers that have been designed to be usable by any SolverEval. For example, to run a Chain-of-Thought solver using gpt-3.5-turbo against an eval, you can run:
```bash
oaieval generation/cot/gpt-3.5-turbo {SOLVEREVAL}
```
