# Contributing to AirTuxOne

Thank you for your interest in AirTuxOne.

## Reporting issues

Open a [GitHub issue](https://github.com/Denis-lab-911/airtuxone/issues) with:

- Linux distribution and kernel version
- Output of `./setup.sh --check`
- Relevant log lines from the daemon
- Your `config.toml` mapping section (no secrets)

## Pull requests

1. Fork the repository and create a focused branch.
2. Keep changes minimal and consistent with existing style.
3. **Never hardcode axis or button mappings in Python** — all mapping belongs in `config.toml`.
4. Update documentation when behavior or configuration changes (`README.md`, `docs/en/`, `docs/fr/`).
5. Test with `evtest` on a real VelocityOne in **PC mode** when possible.

## Mapping changes

- Edit `config.toml` only — see [`docs/en/mapping_velocityone_xbox.md`](docs/en/mapping_velocityone_xbox.md).
- Use `python -m airtux_one.discover` or `python -m airtux_one.learn` to explore inputs.
- Document anti-conflict rules when adding button combos.

## License

By contributing, you agree that your contributions will be licensed under the [GNU GPL v3](LICENSE).
