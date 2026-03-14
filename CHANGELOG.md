# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Initial release
- Container management: list, start, stop, restart, remove, inspect, view logs
- Container editor: edit ports, environment variables, networks, and restart policy
- Stack management: list, edit compose files (YAML editor with syntax highlighting), remove
- Volume management: list, inspect, remove
- Network management: list, inspect, remove
- Image management: list, inspect, remove
- Endpoint/environment picker for switching between Docker hosts
- Multiple Portainer instance support via `~/.config/portainer-tui/config.yaml`
- API token and username/password authentication
- `.env` file support (via python-dotenv)
- TLS skip-verify option for self-signed certificates
- Help overlay (`?`)
- Confirmation dialogs for destructive actions
- Full-screen log viewer with scroll-to-end
- JSON detail viewer for inspect commands
- Pull latest image and recreate container (`p` in Containers view)
- Pull latest images and redeploy stack (`p` in Stacks view)
