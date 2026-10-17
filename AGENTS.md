# Repository Guidelines

## Project Structure & Module Organization

This workspace currently contains no application source, tests, assets, or dependency manifests. The visible `.git/`, `.agents/`, `.codex/`, and `.aws/` directories are environment metadata; do not use them for application code.

When adding the initial implementation, establish clear source, test, and documentation locations and describe them in a root `README.md`. Keep related modules together and avoid introducing empty directories solely to suggest an architecture.

## Build, Test, and Development Commands

No build, installation, or application commands are currently defined. Inspect the workspace with:

- `ls -la`: list root entries, including hidden directories.
- `rg --files --hidden -g '!.git/**' -g '!.aws/**'`: list files while excluding Git metadata and potential credentials.

When introducing a toolchain, document exact setup, run, build, and test commands in `README.md`. Ensure those commands work from the repository root.

## Coding Style & Naming Conventions

No language, formatter, or linter is configured. Follow the standard conventions of the language introduced, use consistent indentation, and choose descriptive module and function names. Configure formatting and linting alongside the first implementation rather than assuming tools are available.

## Testing Guidelines

No test framework or coverage threshold is established. Add tests for new behavior and bug fixes once application code exists. Use descriptive test names that identify the behavior under test, document the test location and invocation, and keep fixtures free of credentials.

## Commit & Pull Request Guidelines

Git history is unavailable in this workspace, so existing commit conventions cannot be verified. Use concise, imperative commit subjects, such as `Add import validation`. Keep changes focused.

Pull requests should explain the change, its purpose, and validation performed. Link relevant issues when available and include screenshots for visible interface changes. Explicitly identify checks that could not be run.

## Security & Configuration

Never commit secrets, credentials, or local environment configuration. Provide sanitized configuration examples and exclude generated outputs from version control when applicable.
