# test-quality

Checks that a test can actually fail — a pre-write gate ("what production change should
make this fail?"), a five-mutation check for tests that already exist, and the four shapes
that stay green no matter what the production code does.

## When it triggers

Use it when writing a test, reviewing a test file or a test diff, encoding a defect as a
failing test before the fix, or when a suite is green and nobody can say what production
change would break it. On a defect the defect is the mutation: the test goes red against
the unfixed code and red again when the fix is reverted, which is the bar layer-cycle's
defect branch states for "red observed".

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
