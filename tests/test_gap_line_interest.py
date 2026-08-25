from coverage.gap_line_interest import classify_gap_line_interest


def test_classify_gap_line_interest_includes_executable_line() -> None:
    decision = classify_gap_line_interest("  MI.buildMemOperand(0, 0);")
    assert decision.include
    assert decision.reason == ""


def test_classify_gap_line_interest_skips_debug() -> None:
    decision = classify_gap_line_interest("LLVM_DEBUG(dbgs() << x);")
    assert not decision.include
    assert decision.reason == "debug"


def test_classify_gap_line_interest_skips_control_flow() -> None:
    decision = classify_gap_line_interest("if (Cond) {")
    assert not decision.include
    assert decision.reason == "control_flow"


def test_classify_gap_line_interest_skips_class_def() -> None:
    decision = classify_gap_line_interest("class Foo {")
    assert not decision.include
    assert decision.reason == "class_def"


def test_classify_gap_line_interest_skips_function_def() -> None:
    decision = classify_gap_line_interest("static bool lowerFoo(MachineInstr &MI) {")
    assert not decision.include
    assert decision.reason == "function_def"
