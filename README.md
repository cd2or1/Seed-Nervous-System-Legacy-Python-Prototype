# Seed Kernel v15 (Stable)

High-performance, binary-encapsulated AI kernel for local orchestration and low-latency response.

## Package components
- `core/`: Pre-compiled native engine (`.pyd` / `.so`).
- `check_env.py`: System and environment diagnostic tool.
- `repair_license.py`: License management tool.
- `core_settings.json.example`: Multi-tier performance profiles.

## Getting started
1. **Environment check**: Run `python check_env.py` to verify configuration and port availability.
2. **Configuration**:
   - Choose a profile: `low`, `normal`, or `turbo`.
   - Rename your chosen `.json` file to `core_settings.json` (or merge keys as needed).
   - Set `CORE_HOME` and other keys from the example.
3. **Integration**: Import the `core` package and use `StreamBroker` to load the native extension.

## Performance profiles
- **Low**: CPU-optimized, for constrained environments.
- **Normal**: Balanced throughput for daily development.
- **Turbo**: High-concurrency mode for high-end hardware.

## Performance benchmark (stream / kernel path)
- **Legacy Python prototype:** ~1.5 ms latency (indicative).
- **Compiled core (v15):** **23 ns** stable on Ryzen 9 9800X3D (vendor claim).
- **Binary size:** 33 KB (fully stripped, zero dependencies) — illustrative.

## License & support
This kernel is protected by binary encryption. If you change your hardware or encounter authentication issues, run:
`python repair_license.py`
and enter your Gumroad license key.

---
Official Support: labsseed@gmail.com
Product Documentation & Updates: https://seedlab8.gumroad.com/l/okcrxz
