# Release and Versioning Strategy

<!-- TODO: SME to define a formal release strategy and versioning scheme if/when this project requires distinct, tagged releases (e.g., for use as a library, or for checkpointing stable versions of the analysis).
Currently, the project is a research pipeline with continuous updates to the `main` branch.
-->

N/A – Not applicable to this batch-analysis project in its current form.

The `ethereum_project` is primarily a research and analysis pipeline. As such, it does not currently follow a formal release schedule or versioning scheme (e.g., Semantic Versioning with tagged releases on GitHub). Development typically occurs on feature branches, which are then merged into the `main` branch. The `main` branch represents the latest stable version of the analysis pipeline.

## Future Considerations

If the project evolves to a stage where distinct releases are beneficial (e.g., if parts of the codebase are to be used as a library, or if specific versions of the analysis need to be archived and easily reproducible), the following aspects would need to be defined:

*   **Versioning Scheme:**
    *   Adoption of Semantic Versioning (SemVer - `MAJOR.MINOR.PATCH`).
    *   How version numbers are incremented based on changes (breaking changes, new features, bug fixes).
*   **Branching Strategy for Releases:**
    *   Use of release branches (e.g., `release/v1.0.0`).
    *   Tagging commits on the `main` branch or release branches to mark official releases (e.g., `git tag v1.0.0`).
*   **Release Process:**
    *   Steps to create a release (e.g., final testing, documentation updates, tagging).
    *   Use of GitHub Releases to publish release notes and any associated artifacts.
*   **Changelog Management:**
    *   A system for maintaining a `CHANGELOG.md` file, possibly automated using tools that parse commit messages (e.g., Conventional Commits).
*   **Automation:**
    *   Automating parts of the release process using GitHub Actions (e.g., creating tags, drafting releases based on tags).

For now, users should rely on the latest commit on the `main` branch for the most up-to-date version of the pipeline. Reproducibility for past analyses would rely on checking out specific commit hashes from the Git history and using the pinned dependencies in `repo://requirements-lock.txt` associated with that commit. 