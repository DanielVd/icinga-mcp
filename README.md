# icinga-mcp

[![Latest Release](https://img.shields.io/github/v/release/DanielVd/icinga-mcp)](https://github.com/DanielVd/icinga-mcp/releases/latest)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

MCP servers for Icinga2 and Icinga Director automation.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Integration](#integration)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

## Features

- Icinga2 monitoring queries
- Director configuration automation
- Streamable HTTP MCP transport

## Requirements

- Python 3.10+
- Icinga2 API enabled
- Icinga Director installed

## Installation

```bash
git clone https://github.com/DanielVd/icinga-mcp.git
cd icinga-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Quick Start

```bash
python -m src.icinga2_mcp.server
python -m src.director_mcp.server
```

## Configuration

Set required credentials in `.env` (`ICINGA_*`, `DIRECTOR_*`).

## Integration

Use MCP client with streamable-http endpoints on ports `8092` and `8093`.

## Troubleshooting

- auth errors: check API user/password
- timeout errors: tune request timeout settings

## Security Notes

- never commit `.env`
- use least-privilege Icinga accounts
