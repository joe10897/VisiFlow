# Declarative YAML Test Runner Example

This example demonstrates how anyone on your team (QA engineers, Product Managers, or SDETs) can author and execute visual E2E tests using clean, human-readable YAML without writing any Python or JavaScript code.

## How to Run

Execute the YAML test directly from the command line:

```bash
# Run with visible browser
visiflow run test_flow.yaml --headed

# Run in headless mode (ideal for CI/CD)
visiflow run test_flow.yaml --headless

# Specify a custom report output path
visiflow run test_flow.yaml --report my_custom_report.html
```

## Available Step Actions

| Action | Example |
| :--- | :--- |
| `goto` | `- goto: "https://example.com"` |
| `fill` | `- fill: "Username"`<br>&nbsp;&nbsp;`value: "admin"` |
| `click` | `- click: "Submit"` |
| `click` (spatial) | `- click: "Delete"`<br>&nbsp;&nbsp;`right_of: "Alice Smith"` |
| `press` | `- press: "Enter"` |
| `assert_visible` | `- assert_visible: "Welcome back!"` |
| `assert_not_visible` | `- assert_not_visible: "Loading..."` |
| `wait_for` | `- wait_for: "Dashboard"` |
| `sleep` | `- sleep: 2.0` |
| `screenshot` | `- screenshot: "evidence.png"` |
