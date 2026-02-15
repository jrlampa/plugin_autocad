# sisRUA Living Documentation (BDD)

This directory contains the executable specifications for the sisRUA project, using Gherkin syntax.

## Structure

- `features/*.feature`: User stories and scenarios.
- `steps/`: C# binding classes (to be implemented in the Plugin test project).

## How to Run

1. Install **SpecFlow for Visual Studio 2022**.
2. Open `src/plugin/sisRUA.sln`.
3. The Test Explorer will discover these scenarios as tests.

## Goal

Replace static `manual-test-cases.csv` with these live feature files. If a scenario passes in the CI/CD or local test run, the requirement is met.
