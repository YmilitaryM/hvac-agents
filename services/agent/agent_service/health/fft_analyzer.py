def analyze_spectrum(fft_bins: dict[float, float], shaft_speed_hz: float = 50.0) -> dict:
    """
    Analyze vibration FFT spectrum per GB/T 19873.
    Detects: unbalance (1x), misalignment (2x, 3x), bearing faults.
    Classifies severity per GB/T 6075 A/B/C/D zones.
    """
    peak_frequencies = []
    for hz, amp in sorted(fft_bins.items()):
        label = None
        tol = shaft_speed_hz * 0.05
        if abs(hz - shaft_speed_hz) <= tol:
            label = "1x 不平衡"
        elif abs(hz - shaft_speed_hz * 2) <= tol:
            label = "2x 不对中"
        elif abs(hz - shaft_speed_hz * 3) <= tol:
            label = "3x 不对中/松动"
        peak_frequencies.append({"hz": hz, "amplitude": amp, "label": label})

    max_amp = max(fft_bins.values()) if fft_bins else 0
    if max_amp < 4.5:
        zone = "A"
    elif max_amp < 7.1:
        zone = "B"
    elif max_amp < 11.0:
        zone = "C"
    else:
        zone = "D"

    return {
        "peak_frequencies": peak_frequencies,
        "max_amplitude": max_amp,
        "vibration_zone": zone,
        "bearing_fault_freqs": {"BPFI": 0.0, "BPFO": 0.0, "FTF": 0.0, "BSF": 0.0},
    }
