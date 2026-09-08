---
name: test-quality
description: Use when writing a test, reviewing a test file or a test diff, encoding a defect as a failing test before the fix, or when a suite is green and nobody can say what production change would break it. Answers "would this test ever fail?" with a pre-write gate, a five-mutation check (wrong constant, wrong branch, missing side effect, empty return, missing validation), and the four shapes that stay green forever — mocking the subject under test, one double shared across every branch, assertions that mirror the implementation, and re-testing framework mechanics.
---

# Test quality

A test earns its place by failing. One that cannot name the production
change that would break it is a green light wired to nothing: it costs a
run on every commit and catches nothing on any of them.

## The pre-write gate

Before writing a test, answer in one sentence: **what production change
should make this fail?** No answer means there is no test to write yet —
the behavior is not pinned down; go read or draft the contract. An answer
as vague as "if the code is wrong" means the assertion is not specific
enough to be worth making.

## The mutation check

For a test that already exists, break the production code on purpose and
confirm the test goes red. Five mutations, cheapest first:

| Mutation | Applied to |
| --- | --- |
| wrong constant | a returned or compared literal — off by one, or negated |
| wrong branch | flip a condition, or swap the arms |
| missing side effect | delete the write, emit, or call the test claims to check |
| empty return | return the empty value instead of the real one |
| missing validation | delete a guard, then feed it the input that guard rejects |

A mutation the suite survives is a hole: fix the test, then revert the
mutation. Apply this to the specific code the test names — a whole-file
mutation run is a different and much slower tool.

## Four shapes that stay green forever

- **Mocking the subject under test.** A double standing in for the thing
  you are testing asserts the double. Mock what the subject talks to —
  clock, network, filesystem, database — never the subject.
- **One double shared across every branch.** A double configured once for
  the whole file feeds every case the same input, so one branch is
  exercised and the rest are decoration. Configure a separate double per
  branch, inside the case that needs it.
- **Mirror assertions.** An expected value recomputed with the
  implementation's own expression passes for every implementation,
  including a wrong one. Write the expected value out literally.
- **Re-testing framework mechanics.** Asserting that a decorator registers
  a route, an ORM persists a field, or a library validator rejects the
  wrong type tests the library, which is already tested. Test the branch
  you wrote, not the one they wrote.

## When it runs

Before writing tests; on any test diff under review; and on a defect,
where the failing test comes first and is observed red — the pre-write
gate plus one mutation is the bar for what "red observed" means. A suite
inherited green gets the mutation check before anyone trusts it.

## Guardrails

- Never weaken a test, loosen an assertion, or lower a threshold to make a
  suite pass. A test that cannot be made to fail on purpose is deleted or
  rewritten, not relaxed.
- Report a hole found in a test you do not own as a finding, with the
  mutation that survived; do not silently patch it mid-task.
- Coverage counts lines executed, not behavior pinned. A covered line with
  no mutation that turns it red is uncovered in the only sense that matters.
