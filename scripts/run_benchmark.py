from app.benchmark_runner import (
    run_detailed_benchmark,
)
from app.benchmark import (
    generate_benchmark,
)
from app.performance import (
    measure_throughput,
)


NUM_CASES = 100
SEED = 42


report = run_detailed_benchmark(
    num_cases=NUM_CASES,
    seed=SEED,
)

benchmark = generate_benchmark(
    num_cases=NUM_CASES,
    seed=SEED,
)

throughput = measure_throughput(
    benchmark.observed_records,
    cases=NUM_CASES,
)


metrics = report.metrics


print()
print("=" * 70)
print("FINPROOF — PHASE 1 BASELINE")
print("=" * 70)

print()
print("OVERALL")
print("-" * 70)

print(
    f"Cases processed:      "
    f"{metrics.total_cases}"
)

print(
    f"Financial records:    "
    f"{throughput.records}"
)

print(
    f"Corrupted cases:      "
    f"{metrics.corrupted_cases}"
)

print(
    f"Detected cases:       "
    f"{metrics.detected_cases}"
)

print(
    f"Missed cases:         "
    f"{metrics.missed_cases}"
)

print(
    f"False positives:      "
    f"{metrics.false_positive_cases}"
)

print(
    f"Detection rate:       "
    f"{metrics.detection_rate:.2%}"
)

print(
    f"Precision:            "
    f"{metrics.precision:.2%}"
)

print()
print("CORRUPTION BREAKDOWN")
print("-" * 70)

for metric in report.corruption_metrics:

    print(
        f"{metric.corruption_type:<22}"
        f"Injected: {metric.injected:<4}"
        f"Detected: {metric.detected:<4}"
        f"Missed: {metric.missed:<4}"
        f"Rate: {metric.detection_rate:.2%}"
    )

print()
print("MISSED / UNRESOLVED CASES")
print("-" * 70)

for case_id in sorted(report.missed_cases):
    print(case_id)

print()
print("FALSE POSITIVES")
print("-" * 70)

for case_id in sorted(report.false_positive_cases):
    print(case_id)

print()
print("THROUGHPUT")
print("-" * 70)

print(
    f"Elapsed time:         "
    f"{throughput.elapsed_seconds:.6f} sec"
)

print(
    f"Cases / second:       "
    f"{throughput.cases_per_second:.2f}"
)

print(
    f"Records / second:     "
    f"{throughput.records_per_second:.2f}"
)

print()
print("=" * 70)
