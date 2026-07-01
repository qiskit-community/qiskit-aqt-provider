# Contributing

## Contributing to Qiskit AQT Provider

### Issue reporting

When you encounter a problem please open an issue for it to
the [issue tracker](https://github.com/Qiskit/qiskit-aqt-provider/issues).

### Improvement proposal

If you have an idea for a new feature please open an **Feature Request** issue
in the [issue tracker](https://github.com/Qiskit/qiskit-aqt-provider/issues). Opening
an issue starts a discussion with the team about your idea, how it fits in with
the project, how it can be implemented, etc.

### Code Review

Code review is done in the open and open to anyone. While only maintainers have
access to merge commits, providing feedback on pull requests is very valuable
and helpful. It is also a good mechanism to learn about the code base. You can
view a list of all open pull requests here:
https://github.com/Qiskit/qiskit-aqt-provider/pulls
to review any open pull requests and provide feedback on it.

### Pull requests

We use [GitHub pull requests](
https://help.github.com/articles/about-pull-requests) to accept contributions.

While not required, opening a new issue about the bug you're fixing or the
feature you're working on before you open a pull request is an important step
in starting a discussion with the community about your work. The issue gives us
a place to talk about the idea and how we can work together to implement it in
the code. It also lets the community know what you're working on and if you
need help, you can use the issue to go through it with other community and team
members.

If you've written some code but need help finishing it, want to get initial
feedback on it prior to finishing it, or want to share it and discuss prior
to finishing the implementation you can open a *Work in Progress* pull request.
When you create the pull request prefix the title with the **\[WIP\]** tag (for
**W**ork **I**n **P**rogress). This will indicate to reviewers that the code in
the PR isn't in it's final state and will change. It also means that we will
not merge the commit until it is finished. You or a reviewer can remove the
[WIP] tag when the code is ready to be fully reviewed for merging.

### Contributor License Agreement

Before you can submit any code we need all contributors to sign a
contributor license agreement. By signing a contributor license
agreement (CLA) you're basically just attesting to the fact
that you are the author of the contribution and that you're freely
contributing it under the terms of the Apache-2.0 license.

When you contribute to the Qiskit Terra project with a new pull request,
a bot will evaluate whether you have signed the CLA. If required, the
bot will comment on the pull request, including a link to accept the
agreement. The [individual CLA](https://qiskit.org/license/qiskit-cla.pdf)
document is available for review as a PDF.

**Note**:
> If your contribution is part of your employment or your contribution
> is the property of your employer, then you will likely need to sign a
> [corporate CLA](https://qiskit.org/license/qiskit-corporate-cla.pdf) too and
> email it to us at <qiskit@us.ibm.com>.


### Pull request checklist

When submitting a pull request and you feel it is ready for review,
please ensure that:

1. The code follows the code style of the project and successfully
   passes the tests. After syncing the environment with `uv sync
   --group dev --extra test`, you can run the repository checks through
   `mise`, for example `mise run test:unit`, `mise run test:integration`,
   `mise run test:acceptance`, `mise run check:linting`, and
   `mise run check:format`.
2. The documentation has been updated accordingly. In particular, if a
   function or class has been modified during the PR, please update the
   *docstring* accordingly.
3. If it makes sense for your change ensure that you have added new tests that
   cover your code changes.

### Commit messages

As important as the content of the change, is the content of the commit message
describing it. The commit message provides the context for not only code review
but also the change history in the git log. Having a detailed commit message
will make it easier for your code to be reviewed and also provide context to the
change when it's being looked at years in the future. When writing a commit
message there are some important things to remember:

* Do not assume the reviewer understands what the original problem was.

When reading an issue, after a number of back & forth comments, it is often
clear what the root cause problem is. The commit message should have a clear
statement as to what the original problem is. The bug is merely interesting
historical background on *how* the problem was identified. It should be
possible to review a proposed patch for correctness from the commit message,
 without needing to read the bug ticket.

* Do not assume the code is self-evident/self-documenting.

What is self-evident to one person, might not be clear to another person. Always
document what the original problem was and how it is being fixed, for any change
except the most obvious typos, or whitespace only commits.

* Describe why a change is being made.

A common mistake is to just document how the code has been written, without
describing *why* the developer chose to do it that way. By all means describe
the overall code structure, particularly for large changes, but more importantly
describe the intent/motivation behind the changes.

* Read the commit message to see if it hints at improved code structure.

Often when describing a large commit message, it becomes obvious that a commit
should have in fact been split into 2 or more parts. Don't be afraid to go back
and rebase the change to split it up into separate pull requests.

* Ensure sufficient information to decide whether to review.

When Github sends out email alerts for new pull request submissions, there is
minimal information included, usually just the commit message and the list of
files changes. Because of the high volume of patches, commit message must
contain sufficient information for potential reviewers to find the patch that
they need to look at.

* The first commit line is the most important.

In Git commits, the first line of the commit message has special significance.
It is used as the default pull request title, email notification subject line,
git annotate messages, gitk viewer annotations, merge commit messages, and many
more places where space is at a premium. As well as summarizing the change
itself, it should take care to detail what part of the code is affected.

* Describe any limitations of the current code.

If the code being changed still has future scope for improvements, or any known
limitations, then mention these in the commit message. This demonstrates to the
reviewer that the broader picture has been considered and what tradeoffs have
been done in terms of short term goals vs. long term wishes.

* Include references to issues

If the commit fixes or is related to an issue make sure you annotate that in
the commit message. Using the syntax:

Fixes #1234

if it fixes the issue (github will close the issue when the PR merges).

The main rule to follow is:

The commit message must contain all the information required to fully
understand & review the patch for correctness. Less is not more.


### Installing Qiskit AQT Provider from source

To install the AQT provider from a local git checkout you should
run:

```bash
uv sync --group dev --extra test
```

which will create or update the local virtual environment, install the
project in editable mode, and pull in the development and test dependencies.
After that, run project tasks with `mise run ...` from the repository root.


### Test

Once you've made a code change, it is important to verify that your change
does not break any existing tests and that any new tests that you've added
also run successfully. Before you open a new pull request for your change,
you'll want to run the test suite locally.

The repository uses [**uv**](https://docs.astral.sh/uv/) to manage the
environment and [**mise**](https://mise.jdx.dev/) to provide the common
project tasks defined in `mise.toml`. After running `uv sync --group dev
--extra test`, you can execute:

- `mise run test:unit`
- `mise run test:integration`
- `mise run test:acceptance`
- `mise run check:linting`
- `mise run check:format`
- `mise run check:types`
- `mise run check:spelling`

If you need to run pytest directly, use `uv run pytest ...` from the
repository root so the commands use the same environment as the project
tasks.


### Style guide

To enforce a consistent code style in the project we use
[ruff](https://docs.astral.sh/ruff/) to verify that code contributions conform
to the project style guide. To verify that your changes conform to the style
guide you can run: `mise run check:linting` and `mise run check:format`.

## Documentation

The documentation for the Python SDK is auto-generated from Python
docstrings using [Sphinx](http://www.sphinx-doc.org). Please follow [Google's Python Style
Guide](https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments)
for docstrings. A good example of the style can also be found with
[Sphinx's napoleon converter
documentation](http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

## Development Cycle

The development cycle for qiskit-aqt-provider is all handled in the open using
the project boards in Github for project management. As we're preparing a new release we'll
document what has changed since the previous version in the release notes and Changelog.

### Branches

* `master`:

The master branch is used for development of the next version of qiskit-aqt-provider.
It will be updated frequently and should not be considered stable. The API
can and will change on master as we introduce and refine new features.


### Release Cycle

From time to time, we will release brand new versions of Qiskit Terra. These
are well-tested versions of the software.

When the time for a new release has come, we will:

1. Bump the package version in the `pyproject.toml` on `master`
2. Create a new tag with the version number on master
