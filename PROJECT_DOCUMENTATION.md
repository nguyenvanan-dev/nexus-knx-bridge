## Milestone v0.7: Device Management
- Implemented bulk import of devices with robust transaction handling and conflict resolution.
- Enforced Domain-driven design with DeviceService acting as a facade for DeviceRegistry and StateManager.
- Enhanced automation engine V2 to resolve `notify_fn` and EventBus injection issues.
- Updated EventBus typing and usage for `DEVICE_REGISTRY_UPDATED`.
- Implemented duplicate group address check with automatic rollback during import.
- Documented and structured codebase for stable architecture freeze.
