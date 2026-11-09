# Trajectory format

A run is a UTF-8 JSONL file. Each non-empty line is one trajectory. Blank lines are ignored. There is no header line.

This repository's dataset is entirely `source: "synthetic"`. The format also allows `human` and `production` so a later file of real logs can use the same scorer. Those words are labels, not a claim that this repo contains either.

## Object

| Field | Required | Type | Meaning |
|---|---|---|---|
| `id` | yes | string | Stable id. Unique inside a file. |
| `task_id` | yes | string | Task family, for example `weather`. |
| `source` | yes | string | `synthetic`, `human`, or `production`. |
| `task` | yes | string | The user request the agent was given. |
| `steps` | yes | array | Ordered tool calls. May be empty. |
| `final_answer` | yes | string | What the agent returned to the user. May be empty. |
| `seed` | no | integer | Generator seed. The built-in agents record it. |
| `params` | no | object | Structured inputs. Required if you re-run `--agent sample` or `--agent regressed`. |
| `meta` | no | object | Ignored by the scorers. |

Unknown top-level fields are rejected. A scorer that is handed a Python dict still ignores anything it does not read; the file reader is the strict boundary.

## Step

| Field | Required | Type | Meaning |
|---|---|---|---|
| `tool` | yes | string | Tool name. |
| `arguments` | yes | object | Arguments the agent recorded. Key order is not significant. |
| `observation` | yes | any JSON | What the tool returned, as recorded. |
| `argument_schema` | no | object | JSON Schema subset. Golden side. See below. |
| `observation_schema` | no | object | JSON Schema subset for the observation. |
| `thought` | no | string | Optional note. Not scored. |

The candidate file usually omits schemas. Schemas live on the golden trajectory and are applied to the candidate's arguments and observation.

## Schema subset

`type` (`object`, `array`, `string`, `number`, `integer`, `boolean`, `null`), `required`, `properties`, `additionalProperties` (boolean only), `items`, `enum`, `minimum`, `maximum`, `minLength`, `maxLength`.

`integer` does not accept `true` or `false`. `enum` does not treat `true` as `1`. Unknown keywords are errors.

## Worked record

`data/example.jsonl` is the first line of `data/golden.jsonl`, byte for byte. It is one synthetic weather trajectory: `get_weather` with a city, the fixture observation, and a final answer. Regenerating with seed 0 rewrites both files.

## How two files are compared

`eval` pairs rows by `id`.

- A golden id with no candidate scores 0 and is marked missing.
- A candidate id with no golden is listed on the run as `extra_candidate_ids` and is not part of the mean.
- Steps are aligned by index. The harness does not search for a shift. An inserted step at index 0 makes every later step compare against the wrong golden step.
- Argument and observation equality uses canonical JSON (`sort_keys`, no insignificant whitespace).
- The final answer scores 1 when the strings match after case-folding and whitespace collapse. Otherwise the score is token F1 on `[a-z0-9]+` tokens.

## Scorers

Per index, over `max(len(golden), len(candidate))` steps:

| Scorer | What a 1 means |
|---|---|
| `tool_choice` | Same tool name. A missing or extra step is 0. |
| `exact` | Mean of tool-name match, canonical argument match, and canonical observation match. A missing or extra step is 0. |
| `schema` | Mean of argument-schema and observation-schema checks on golden indexes. Extra steps are not in this mean. A missing step is 0 when the golden step has a schema. Shape only: the wrong city still passes `"type": "string"`. |
| `judge` | The judge hook. The default `MockJudge` is `0.5 * tool + 0.3 * argument-key Jaccard + 0.2 * observation-key Jaccard`. Missing or extra steps are 0. |

`final_answer` is the answer score above.

The trajectory judge component is `0.7 * mean(step judge scores) + 0.3 * judge.judge_answer(...)`. With the mock, `judge_answer` is the same function as `final_answer`. A custom hook can disagree, and the two components stay separate so you can see which one moved.

Weights, renormalized over whichever components exist:

```
tool_choice 0.25
exact 0.30
schema 0.15
final_answer 0.20
judge 0.10
```

`exact` already includes the tool name, so a wrong tool is counted twice. That is intentional: picking the wrong tool should be expensive. It is not two independent measurements.

All component scores are rounded to 6 decimal places before they are written.

## Run JSON

`eval` writes one JSON object, not JSONL: `mean`, `by_scorer`, `judge.name`, `judge.is_mock`, `weights`, and `trajectories[]` with per-step scores. `diff` and `gate` read that object.

The gate recomputes the mean from `trajectories[].score`. A `mean` field that does not match those rows is a warning. It does not decide pass or fail.
